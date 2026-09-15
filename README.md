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
az előzmény-adatbázis karbantartását egy **Claude Code Routine** végzi
minden hajnalban (nem GitHub Actions).

## Felépítés

```
konyv_adatbazis.json, konyv_adatbazis_2.json   forrás adatbázisok (szópárok, mondatok)
scripts/generate_daily.py                       napi feladatsor generálása
scripts/build_db.py                              history -> SQLite + összesítő
scripts/lib/pool.py                              adatbázis-egyesítés, ismétlés-elkerülés
scripts/lib/explanations.py                      szabály-alapú nyelvtani magyarázatok
docs/                                             a statikus frontend (ide mutat a GitHub Pages)
  index.html, app.js, style.css
  data/
    daily/today.json           a mai feladatsor (a cron írja felül minden hajnalban)
    history/YYYY-MM-DD.json    napi eredmények (attempts[] tömbbel, redo-kompatibilis)
    history_index.json         összesítő a history nézethez (streak, átlag, gyenge témák)
    app.db                     levezetett, lekérdezhető/letölthető SQLite adatbázis
    state/usage_state.json     melyik szót/mondatot mikor használtuk (ismétlés-elkerüléshez)
```

A hajnali automatizálást egy Claude Code Routine végzi (nincs `.github/workflows`
mappa): minden éjjel lefuttatja a `scripts/build_db.py` és
`scripts/generate_daily.py` scripteket, majd commitolja és pusholja az
eredményt a `main` ágra.

## Beüzemelés (egyszeri lépések)

### 1. GitHub Pages bekapcsolása

A repo **Settings → Pages** menüjében:
- Source: "Deploy from a branch"
- Branch: `main`, mappa: `/docs`

Ezután az oldal elérhető lesz a `https://<felhasználónév>.github.io/<repo>/` címen.

### 2. GitHub Personal Access Token létrehozása

A napi eredmények mentéséhez (és a legfrissebb előzmények olvasásához) a
böngészőnek írási joga kell a repóhoz. Ehhez a **Beállítások** fülön
kattints a "Token létrehozása előre kitöltött űrlappal" linkre – ez egy
olyan GitHub oldalt nyit meg, ahol a név, a leírás, a jogosultság
(Contents: write) és a lejárat (90 nap) már ki van töltve. Már csak ennyi
a dolgod:

1. "Only select repositories" alatt válaszd ki a `Deutsch` repót
2. "Generate token"
3. Másold be a kapott tokent a Beállítások fülön a mezőbe, és mentsd el

(A linket kézzel is elérheted: GitHub → Settings → Developer settings →
Personal access tokens → Fine-grained tokens → Generate new token.)

A token csak a saját böngésződ localStorage-ában tárolódik, GitHube-on
kívül sehova nem kerül. Ne oszd meg mással, és ne mentsd el közös/nyilvános
gépen.

### 3. Hajnali automatizálás (Claude Code Routine)

A napi feladatsor generálását és az előzmény-adatbázis karbantartását egy
Claude Code Routine végzi, ami minden hajnalban (kb. 03:00 UTC, azaz
4-5 óra Európa/Budapest idő szerint) lefut, és a következőket teszi:

1. `git pull` a `main` ágon
2. `python3 scripts/build_db.py` – az előző napi eredményekből frissíti a
   `docs/data/app.db` SQLite adatbázist és a `docs/data/history_index.json`
   összesítőt
3. `python3 scripts/generate_daily.py` – legenerálja a következő napi
   feladatsort (`docs/data/daily/today.json`)
4. commit + push a `main` ágra

Ehhez nincs szükség GitHub Actions-re: a Routine a Claude Code
előfizetésed alatt fut. A Routine beállítását/módosítását (ütemezés,
kikapcsolás) a Claude Code felületén, a Routines listában tudod kezelni.

## Napi használat

1. Nyisd meg a bookmarkolt oldalt reggel, töltsd ki a napi feladatsort.
2. "Ellenőrzés" → megjelenik minden feladathoz a megoldás, a magyarázat és
   egy automatikus javaslat (Helyes / Részben / Hibás). Ha a fordításod
   helyesen eltér a tárolt megoldástól, kattints a megfelelő gombra a
   javaslat felülbírálásához.
3. "Eredmény mentése" → a mai eredmény bekerül a `docs/data/history/` alá.
   Az összesítő (SQLite + history_index.json) a következő hajnali Routine
   futáskor frissül automatikusan.
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

A `docs/data/app.db` egy szabványos SQLite fájl (`attempts`, `answers`
táblákkal), bármilyen SQLite kliensben (pl. DB Browser for SQLite)
megnyitható és lekérdezhető részletesebb statisztikákhoz.
