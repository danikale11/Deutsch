"""Szabaly-alapu, magyar nyelvu nyelvtani magyarazatok gyartasa a
mondatokhoz es szopárokhoz. Nincs AI-hivas: a meglevo adatbazis mezoi
(fejezet nyelvtani temaja, szofaj, vonzat, ragozas, deklinacio) alapjan
allitunk ossze egy rovid, sajat megfogalmazasu indoklast.
"""
from __future__ import annotations

from typing import Any

# 1. szint: konkret nyelvtani tema (a `topic` mezo) -> magyarazat sablon.
# A kulcsokat a ket adatbazisban elofordulo `topic` ertekekbol allitottuk
# ossze (kis-nagy betu erzeketlen egyezes).
GRAMMAR_TOPICS: dict[str, str] = {
    "akkusativ": (
        "Ez a mondat tárgyesetet (Akkusativ) igényel: a `haben` ige és sok "
        "más ige mellett a mondat tárgya tárgyesetbe kerül, ezért a "
        "hím­nemű névelő `der` -> `den` alakot vesz fel (pl. der Tisch -> "
        "den Tisch), a nő- és semlegesnemű, illetve többes számú névelők "
        "nem változnak."
    ),
    "dativ": (
        "Ez a mondat részes esetet (Dativ) igényel: bizonyos igék (pl. "
        "helfen, danken, gefallen) és elöljárószók (aus, bei, mit, nach, "
        "seit, von, zu) mindig Dativ vonzattal állnak. A névelők ilyenkor "
        "der->dem, die->der, das->dem, die(tbsz)->den(+n a főnév végén) "
        "alakra változnak."
    ),
    "genitiv": (
        "Ez a mondat birtokos esetet (Genitiv) igényel: a Genitiv fejezi ki "
        "a birtoklást vagy egyes elöljárószók (wegen, trotz, während, "
        "innerhalb) vonzatát. A hím- és semlegesnemű főnevek `-s`/`-es` "
        "végződést kapnak, a névelő der/das -> des, die -> der."
    ),
    "wechselpräposition": (
        "Ez egy Wechselpräposition (in, an, auf, über, unter, vor, hinter, "
        "neben, zwischen), amely Akkusativot vagy Dativot is vonzhat: "
        "mozgást, irányt kifejező 'hova?' kérdésre Akkusativ jár (pl. Ich "
        "gehe in die Küche), helyhez kötött 'hol?' kérdésre Dativ (pl. Ich "
        "bin in der Küche)."
    ),
    "reflexive verben": (
        "Ez egy visszaható ige (reflexives Verb): a cselekvés visszahat az "
        "alanyra, ezért a mondatban egy visszaható névmás (mich, dich, "
        "sich, uns, euch, sich) is szerepel, ami a legtöbb esetben "
        "tárgyesetben áll."
    ),
    "modalverben": (
        "Modális ige (können, müssen, dürfen, sollen, wollen, mögen) "
        "szerepel a mondatban: a modális ige ragozódik a mondat második "
        "helyén, az értelmi ige pedig ragozatlan főnévi igenévként a "
        "mondat végére kerül (keretes szerkezet)."
    ),
    "modalverben und wendungen": (
        "Modális ige vagy modális jelentésű állandósult kifejezés áll a "
        "mondatban: a ragozott modális ige a második helyen, a "
        "cselekvést kifejező ige főnévi igenévi alakban a mondat végén "
        "helyezkedik el."
    ),
    "wortstellung": (
        "Ez a mondat a német szórendi szabályokat gyakoroltatja: kijelentő "
        "mondatban a ragozott ige mindig a második helyen áll, míg a "
        "mondat többi része (alany, határozók, tárgy) ehhez igazodik, "
        "akár az élre kerül egy határozó (pl. időhatározó), az igét akkor "
        "is a második hely illeti."
    ),
    "man": (
        "A `man` általános alany névmás: olyankor használjuk, amikor nem "
        "egy konkrét személyről, hanem általánosságban ('az ember', "
        "'valaki') beszélünk. Az ige mindig egyes szám 3. személyben áll "
        "utána."
    ),
    "adverbien und konnektoren": (
        "Ez a mondat egy határozószót vagy kötőszót (Konnektor) gyakoroltat, "
        "amely két gondolat logikai kapcsolatát (ok, következmény, "
        "ellentét, feltétel) fejezi ki, és befolyásolhatja a mellette álló "
        "ige helyét a mondatban."
    ),
    "nebensatz": (
        "Ez egy mellékmondat (Nebensatz): a mellékmondatot bevezető "
        "kötőszó (weil, dass, wenn, obwohl stb.) miatt a ragozott ige a "
        "mellékmondat végére kerül, nem a második helyre, mint a "
        "főmondatban."
    ),
    "relativsatz": (
        "Ez egy vonatkozó mellékmondat (Relativsatz): a vonatkozó névmás "
        "(der/die/das/den/dem stb.) neme és száma a jelzett szótól függ, "
        "esete pedig attól, hogy a mellékmondatban milyen szerepet tölt "
        "be. A ragozott ige itt is a mondat végére kerül."
    ),
    "höflichkeit": (
        "Ez egy udvariassági fordulat: a Konjunktiv II (würde, hätte, "
        "wäre, könnte) formák teszik a kérést vagy javaslatot "
        "udvariasabbá, kevésbé közvetlenné, mint a jelen idejű alak."
    ),
    "redewendung": (
        "Ez egy állandósult szókapcsolat (Redewendung): a jelentése nem "
        "mindig vezethető le szó szerint az egyes szavakból, ezért "
        "érdemes egységként, a kontextussal együtt megtanulni."
    ),
    "perfekt": (
        "Ez a mondat Perfekt múlt időt gyakoroltat: a `haben` vagy `sein` "
        "segédige (mozgást/állapotváltozást kifejező igéknél `sein`, "
        "egyébként jellemzően `haben`) ragozott alakja a második helyen, "
        "az ige Partizip II alakja pedig a mondat végén áll."
    ),
    "präteritum": (
        "Ez a mondat Präteritum (elbeszélő múlt) alakot gyakoroltat: ezt a "
        "formát elsősorban írásban és elbeszélésben használjuk, a "
        "`haben`/`sein` és a módbeli segédigék esetén a beszélt nyelvben is "
        "gyakoribb, mint a Perfekt."
    ),
    "futur i": (
        "Ez a mondat Futur I jövő időt gyakoroltat: a `werden` segédige "
        "ragozott alakja a második helyen áll, a cselekvést kifejező ige "
        "pedig változatlan főnévi igenévi alakban a mondat végén."
    ),
    "kati": (
        "Ez a mondat a KATI kötőszó-csoportba (kausal, adversativ, "
        "temporal, final - ok, ellentét, idő, cél) tartozó kötőszót "
        "gyakoroltat, amely mellékmondatot vezet be, ezért az ige a "
        "mondat végére kerül."
    ),
    "konnektoren und satzbau": (
        "Ez a mondat egy kötőszó (Konnektor) mondattani hatását "
        "gyakoroltatja: a kötőszó típusától függ, hogy a ragozott ige a "
        "mondat második helyén marad-e (mellérendelő, pl. und, aber, "
        "denn), vagy a mondat végére kerül (alárendelő, pl. weil, dass)."
    ),
    "imperativ": (
        "Ez felszólító mód (Imperativ): egyes szám 2. személyben az ige "
        "töve (esetenként `-e` végződéssel), többes szám 2. személyben a "
        "`ihr`-hez tartozó igealak (névmás nélkül), magázó formában pedig "
        "az igealak + `Sie` a szórend."
    ),
    "trennbare verben": (
        "Ez egy elváló igekötős ige (trennbares Verb): kijelentő mondatban "
        "az igekötő leválik a ragozott igéről és a mondat végére kerül "
        "(pl. abfahren -> Der Zug fährt um acht ab), Perfektben pedig a "
        "`ge-` képző az igekötő és a szótő közé kerül."
    ),
    "verben mit präposition": (
        "Ez egy vonzatos ige (Verb mit Präposition): az ige jelentéséhez "
        "egy meghatározott elöljárószó és eset (Akkusativ vagy Dativ) "
        "tartozik rögzített formában, ezt a párost egységként érdemes "
        "megtanulni."
    ),
    "präpositionen": (
        "Ez egy elöljárószó, amelyhez rögzített eset (Akkusativ, Dativ "
        "vagy Genitiv) tartozik: az elöljárószó után álló főnév/névmás "
        "esetét mindig az elöljárószó határozza meg, nem a mondat egyéb "
        "része."
    ),
    "genitivpräposition": (
        "Ez egy Genitiv vonzatú elöljárószó (pl. wegen, trotz, während, "
        "innerhalb): a mögötte álló főnév -s/-es végződést kap, a "
        "névelő pedig des/der alakú lesz."
    ),
    "pronominaladverb": (
        "Ez egy névmási határozószó (Pronominaladverb, pl. darauf, damit, "
        "worüber): akkor használjuk elöljárószó + névmás helyett, ha a "
        "vonzat egy dologra (nem személyre) vonatkozik; kérdő alakja "
        "`wo(r)+elöljárószó`, mutató/visszautaló alakja `da(r)+elöljárószó`."
    ),
    "schwache nomen": (
        "Ez egy úgynevezett gyenge főnév (n-Deklination): a hímnemű főnév "
        "minden esetben (Akkusativ, Dativ, Genitiv), egyes számban is "
        "-(e)n végződést kap (pl. der Mensch -> den/dem/des Menschen), "
        "csak az alanyeset (Nominativ) marad változatlan."
    ),
    "modalpartikeln": (
        "Ez egy módosítószó (Modalpartikel, pl. doch, mal, ja, eben): "
        "önmagában nem fordítható le szó szerint, a mondat hangulatát, "
        "nyomatékát vagy a beszélő attitűdjét (meglepetés, unszolás, "
        "magától értetődőség) fejezi ki."
    ),
    "possessivpronomen": (
        "Ez egy birtokos névmás (mein, dein, sein, ihr, unser, euer, "
        "ihr/Ihr): ragozása ugyanúgy a birtok nemétől/számától és "
        "mondatbeli esetétől függ, mint a határozatlan névelőé (ein-szavak)."
    ),
    "wohin/wo/woher": (
        "Ez a `wohin` (hova?), `wo` (hol?) és `woher` (honnan?) "
        "kérdőszavak közti különbséget gyakoroltatja: `wohin` és `woher` "
        "irányt fejez ki (mozgás célja/kiindulópontja), `wo` helyhez "
        "kötött állapotot - ez egyben az Akkusativ/Dativ választást is "
        "meghatározza a Wechselpräpositionoknál."
    ),
    "einer/keiner": (
        "Ez az `einer/eine/eins` és `keiner/keine/kein(e)s` névmások "
        "használatát gyakoroltatja, amikor egy korábban említett főnevet "
        "névelő nélkül, névmással helyettesítünk ('egy/egyik' illetve "
        "'egyik sem')."
    ),
    "jemand/niemand": (
        "Ez a `jemand` (valaki) és `niemand` (senki) határozatlan "
        "névmások ragozását gyakoroltatja: Akkusativban `jemand(en)` / "
        "`niemand(en)`, Dativban `jemand(em)` / `niemand(em)` alakot "
        "vehetnek fel (a végződés ma már gyakran elmaradhat)."
    ),
    "welcher": (
        "Ez a `welcher/welche/welches` kérdő névmás ('melyik?') "
        "ragozását gyakoroltatja, amely a der-szavak (der, die, das) "
        "mintáját követi nemben, számban és esetben."
    ),
    "haben oder sein": (
        "Ez azt gyakoroltatja, hogy a Perfekt segédigéje `haben` vagy "
        "`sein` legyen: `sein` jár a helyváltoztatást vagy "
        "állapotváltozást kifejező igék mellett (pl. gehen, fahren, "
        "werden), minden más igéhez jellemzően `haben` tartozik."
    ),
    "lassen": (
        "Ez a `lassen` ige használatát gyakoroltatja: jelentheti azt, hogy "
        "'hagyni, engedni' valamit, vagy azt, hogy valakivel "
        "elvégeztetünk valamit (pl. Ich lasse mein Auto reparieren - "
        "megjavíttatom az autómat), a főnévi igenévvel együtt, `zu` "
        "nélkül áll a mondat végén."
    ),
    "offizieller brief": (
        "Ez egy hivatalos levél stílusát gyakoroltatja: magázó forma "
        "(Sie), udvarias, tárgyilagos megfogalmazás, formális "
        "megszólítás és zárás jellemzi."
    ),
    "persönlicher brief": (
        "Ez egy személyes levél stílusát gyakoroltatja: tegező forma "
        "(du/ihr), közvetlenebb, személyesebb hangnem és megszólítás "
        "jellemzi, mint a hivatalos levélben."
    ),
    "bildbeschreibung": (
        "Ez egy képleírásban használatos fordulat: jellemzően jelen idő, "
        "helyhatározós kifejezések (vorne, hinten, links, rechts, in der "
        "Mitte) és a Wechselpräpositionok Dativ alakja (mert helyet, nem "
        "mozgást írunk le) jellemzi."
    ),
    "meinung": (
        "Ez egy véleménynyilvánító fordulat (pl. Ich finde, dass...; "
        "Meiner Meinung nach...): ha a `dass` kötőszóval kapcsolódik "
        "mellékmondat, az ige a mondat végére kerül."
    ),
    "präpositionalfragen": (
        "Ez egy elöljárószós kérdés (pl. Worüber sprichst du? / Mit wem "
        "fährst du?): dologra vonatkozó kérdésnél `wo(r)+elöljárószó`, "
        "személyre vonatkozó kérdésnél `elöljárószó + wen/wem` a helyes "
        "szerkezet."
    ),
}

# Ha a `topic` mezo nem talalhato a fenti szotarban, a fejezet nyelvtani
# cime alapjan probalunk egy altalanosabb, de meg mindig konkret utalast
# adni. Ez csak akkor fut le, ha a topic-alapu egyezes sikertelen.
_CHAPTER_FALLBACK_HINTS: dict[str, str] = {
    "akkusativ": GRAMMAR_TOPICS["akkusativ"],
    "dativ": GRAMMAR_TOPICS["dativ"],
    "genitiv": GRAMMAR_TOPICS["genitiv"],
    "wechselpräpositionen": GRAMMAR_TOPICS["wechselpräposition"],
    "modalverben": GRAMMAR_TOPICS["modalverben"],
    "perfekt": GRAMMAR_TOPICS["perfekt"],
    "präteritum": GRAMMAR_TOPICS["präteritum"],
    "futur i": GRAMMAR_TOPICS["futur i"],
    "trennbare verben": GRAMMAR_TOPICS["trennbare verben"],
    "imperativ": GRAMMAR_TOPICS["imperativ"],
    "reflexive verben": GRAMMAR_TOPICS["reflexive verben"],
    "lassen": GRAMMAR_TOPICS["lassen"],
    "genitivpräpositionen": GRAMMAR_TOPICS["genitivpräposition"],
    "schwache nomen": GRAMMAR_TOPICS["schwache nomen"],
    "modalpartikeln": GRAMMAR_TOPICS["modalpartikeln"],
}


def _lookup_topic(topic: str | None) -> str | None:
    if not topic:
        return None
    return GRAMMAR_TOPICS.get(topic.strip().lower())


def _lookup_chapter_fallback(chapter_title: str | None) -> str | None:
    if not chapter_title:
        return None
    lowered = chapter_title.lower()
    for key, hint in _CHAPTER_FALLBACK_HINTS.items():
        if key in lowered:
            return hint
    return None


def _generic_sentence_fallback(item: dict[str, Any]) -> str:
    chapter_title = item.get("chapter_title") or "a lecke témája"
    return (
        f"Ez a mondat a(z) \"{chapter_title}\" témaköréhez kapcsolódik. "
        "Figyeld meg a szórendet és az esetragozást, és vesd össze a "
        "saját fordításodat a megoldással: a legtöbb eltérés a "
        "névelő/esetválasztásból vagy az igepozícióból adódik."
    )


def sentence_explanation(item: dict[str, Any]) -> str:
    """Egy mondathoz tartozo nyelvtani magyarazat osszeallitasa."""
    topic_hint = _lookup_topic(item.get("topic"))
    if topic_hint:
        return topic_hint

    chapter_hint = _lookup_chapter_fallback(item.get("chapter_title"))
    if chapter_hint:
        return chapter_hint

    return _generic_sentence_fallback(item)


def _vocab_note_for_noun(item: dict[str, Any]) -> str | None:
    if item.get("pos") not in ("Nomen", "Nomen (n-Deklination)"):
        return None
    parts = []
    plural = item.get("plural")
    if plural:
        parts.append(f"Többes száma: {plural}.")
    deklination = item.get("deklination")
    if deklination:
        parts.append(
            f"Gyenge főnév (n-Deklination), ragozott alakjai: {deklination}."
        )
    if not parts:
        return None
    return " ".join(parts)


def _vocab_note_for_verb(item: dict[str, Any]) -> str | None:
    if item.get("pos") not in (
        "Verb",
        "Verb mit Präposition",
        "Reflexives Verb",
        "Trennbares Verb",
    ):
        return None
    parts = []
    praeteritum = item.get("praeteritum")
    perfekt = item.get("perfekt")
    if praeteritum or perfekt:
        forms = " / ".join(f for f in (praeteritum, perfekt) if f)
        parts.append(f"Alapalakok (Präteritum / Perfekt): {forms}.")
    praeposition = item.get("praeposition")
    if praeposition:
        parts.append(f"Rögzített vonzat: {praeposition}.")
    if item.get("pos") == "Trennbares Verb":
        parts.append("Elváló igekötős ige: kijelentő mondatban az igekötő a mondat végére kerül.")
    if item.get("pos") == "Reflexives Verb":
        parts.append("Visszaható ige: használatához visszaható névmás (mich, dich, sich...) szükséges.")
    if not parts:
        return None
    return " ".join(parts)


def vocab_note(item: dict[str, Any]) -> str | None:
    """Rovid, opcionalis kiegeszito megjegyzes egy szoparhoz (nem
    kotelezo elem, de segit a nem/tobbes szam/vonzat megjegyzeseben).
    Visszaadhat None-t, ha nincs semmi erdemleges hozzafuznivalo.
    """
    return _vocab_note_for_noun(item) or _vocab_note_for_verb(item)
