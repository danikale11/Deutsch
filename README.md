# Deutsch – napi német gyakorló

Önálló, napi szintű német nyelvtanulást segítő webalkalmazás. Minden nap
(hajnalban, automatikusan) egy friss feladatsort állít elő a repóban lévő
két saját szerzésű adatbázisból (`konyv_adatbazis.json`, `konyv_adatbazis_2.json`):

- 5 magyar → német mondatfordítás
- 5 német → magyar mondatfordítás
- 5 magyar → német szópárosítás
- 5 német → magyar szópárosítás

Minden mondathoz megoldás és rövid, magyar nyelvű nyelvtani magyarázat
tartozik. A kitöltés után a rendszer pontoz (automatikus hasonlóság-becslés
+ saját megerősítés), és minden nap eredménye elmentődik egy visszanézhető,
újracsinálható history-listába.

Nincs élő szerver: a frontend statikus (GitHub Pages), a napi generálást és
az előzmény-adatbázis karbantartását GitHub Actions workflow-k végzik.

## Felépítés

```
konyv_adatbazis.json, konyv_adatbazis_2.json   forrás adatbázisok (szópárok, mondatok)
scripts/generate_daily.py                       napi feladatsor generálása
scripts/build_db.py                              history -> SQLite + összesítő
scripts/lib/pool.py                              adatbázis-egyesítés, ismétlés-elkerülés
scripts/lib/explanations.py                      szabály-alapú nyelvtani magyarázatok
web/                                              a statikus frontend (ide mutat a GitHub Pages)
  index.html, app.js, style.css
  data/
    daily/today.json           a mai feladatsor (a cron írja felül minden hajnalban)
    history/YYYY-MM-DD.json    napi eredmények (attempts[] tömbbel, redo-kompatibilis)
    history_index.json         összesítő a history nézethez (streak, átlag, gyenge témák)
    app.db                     levezetett, lekérdezhető/letölthető SQLite adatbázis
    state/usage_state.json     melyik szót/mondatot mikor használtuk (ismétlés-elkerüléshez)
.github/workflows/
  generate_daily.yml           hajnali cron + kézi indítás (workflow_dispatch)
  build_db.yml                 history/** push-ra újraépíti az app.db-t és a history_index.json-t
```

## Beüzemelés (egyszeri lépések)

### 1. GitHub Pages bekapcsolása

A repo **Settings → Pages** menüjében:
- Source: "Deploy from a branch"
- Branch: `main`, mappa: `/web`

Ezután az oldal elérhető lesz a `https://<felhasználónév>.github.io/<repo>/` címen.

> Ha ez az ág (`claude/...`) még nem a `main`, a végleges használat előtt
> mergeld/pushold a tartalmát a `main` ágra – a scheduled workflow-k csak a
> default branch-en lévő workflow-fájlt futtatják.

### 2. GitHub Personal Access Token létrehozása

A napi eredmények mentéséhez (és a legfrissebb előzmények olvasásához) a
böngészőnek írási joga kell a repóhoz. Hozz létre egy **fine-grained
personal access tokent**:

1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token
2. Repository access: csak ez az egy repó (`Deutsch`)
3. Permissions: **Contents: Read and write**
4. Lejárat: javasolt 90 nap (utána újra kell generálni)

A tokent az alkalmazás **Beállítások** fülén add meg – csak a saját
böngésződ localStorage-ában tárolódik, GitHube-on kívül sehova nem kerül.
Ne oszd meg mással, és ne mentsd el közös/nyilvános gépen.

### 3. Első generálás

A hajnali cron (`generate_daily.yml`, `0 3 * * *` UTC) automatikusan lefut
minden nap. Az első feladatsorhoz nem kell várni: a repo Actions fülén
indítsd el kézzel a "Napi feladatsor generálása" workflow-t
(`workflow_dispatch`), vagy a Pages élesítése előtt már legenerált
`web/data/daily/today.json` is használható.

## Napi használat

1. Nyisd meg az oldalt reggel, töltsd ki a napi feladatsort.
2. "Ellenőrzés" → megjelenik minden feladathoz a megoldás, a magyarázat és
   egy automatikus javaslat (Helyes / Részben / Hibás). Ha a fordításod
   helyesen eltér a tárolt megoldástól, kattints a megfelelő gombra a
   javaslat felülbírálásához.
3. "Eredmény mentése" → a mai eredmény bekerül a `web/data/history/` alá, a
   `build_db.yml` workflow pedig automatikusan frissíti az összesítőt és a
   letölthető SQLite adatbázist.
4. Az "Előzmények" fülön visszanézhető minden korábbi nap, illetve az
   "Újra csinálom" gombbal egy régebbi nap feladatai újra elvégezhetők
   (ez új próbálkozásként kerül ugyanahhoz a naphoz).

## Hogyan működik a kiválasztás és a magyarázat

- A két adatbázis szópárjai és mondatai egy közös halmazba kerülnek; az
  elmúlt kb. 14 napban már használt elemek kizárásra kerülnek az ismétlés
  elkerülése végett (`scripts/lib/pool.py`).
- A korábbi eredmények alapján gyengébben teljesített témák enyhén nagyobb
  eséllyel kerülnek be az új feladatsorba.
- A nyelvtani magyarázatok szabály-alapú sablonokból épülnek fel
  (`scripts/lib/explanations.py`), a fejezet nyelvtani témája és a szó
  saját mezői (szófaj, vonzat, ragozás) alapján – nincs AI-hívás, így a
  hajnali automatizált futás API-kulcs és külső függőség nélkül,
  megbízhatóan működik.

## Adatbázis lekérdezése

A `web/data/app.db` egy szabványos SQLite fájl (`attempts`, `answers`
táblákkal), bármilyen SQLite kliensben (pl. DB Browser for SQLite)
megnyitható és lekérdezhető részletesebb statisztikákhoz.
