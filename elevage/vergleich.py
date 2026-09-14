"""Zwei Blätter nebeneinander — deterministisch gerechnet, nicht formuliert.

Sobald zwei Tierärzte dieselbe Tierart verschieden takten, ist die Frage
nicht mehr „was steht da“, sondern „wo gehen sie auseinander“. Das ist eine
Rechnung: gruppiert wird über ein Thema — bei Impfungen über den **Erreger**,
sonst über die Kategorie —, verglichen werden die Tagesfenster.

Das Urteil, welches Blatt gilt, trifft der Betrieb. Dieses Modul stellt nur
nebeneinander: es empfiehlt nichts, legt nichts zusammen und rechnet keine
Mischform aus.
"""

from __future__ import annotations

from elevage.models import (
    OFFENES_ENDE,
    Kategorie,
    Programm,
    Programmunterschied,
    Programmvergleich,
    Schritt,
    Tierart,
)
from elevage.programme import alle_programme, programm

BEGLEITEND = {Kategorie.ANTI_STRESS, Kategorie.VITAMINE, Kategorie.PAUSE}
"""Kategorien, die das Tagesgeschäft begleiten statt es zu takten.

Sie stehen in einem Blatt zwanzigmal und im anderen gar nicht — Zeile für
Zeile verglichen ergäben sie Lärm statt Erkenntnis. Deshalb werden sie
gezählt und in einer Zeile zusammengefasst."""

THEMA_NAME = {
    Kategorie.HYGIENE: "Hygiene / Stallführung",
    Kategorie.IMPFUNG: "Impfung",
    Kategorie.MEDIKATION: "Medikation",
    Kategorie.VITAMINE: "Vitamine",
    Kategorie.ANTIKOKZIDIUM: "Antikokzidium",
    Kategorie.ENTWURMUNG: "Entwurmung",
    Kategorie.EINGRIFF: "Eingriff",
    Kategorie.FUTTERWECHSEL: "Futterwechsel",
    Kategorie.ANTI_STRESS: "Anti-Stress",
    Kategorie.LEBERSCHUTZ: "Leberschutz",
    Kategorie.PAUSE: "Pause (einfaches Wasser)",
}

ERREGER = [
    ("gumboro", "Gumboro"),
    ("newcastle", "Newcastle"),
    ("bronchite", "Bronchite infectieuse"),
    ("pocken", "Pocken (Variole)"),
    ("variole", "Pocken (Variole)"),
    ("coryza", "Coryza"),
    ("salmonellose", "Salmonellose"),
    ("enteritis", "Enteritis"),
    ("legedepression", "Legedepression (EDS)"),
]
"""Wonach Impfungen gruppiert werden: der Erreger, nicht der Titel.

Über den Titel verglichen stünde „2. Gumboro-Impfung“ neben nichts, weil das
andere Blatt dieselbe Gabe anders nennt. Ein Kombi-Impfstoff schützt gegen
mehrere Erreger und steht deshalb in mehreren Zeilen — das ist keine
Dopplung, sondern die Wahrheit über das Präparat."""


def _fenster(schritt: Schritt) -> str:
    """Das Tagesfenster, wie es auf dem Papier stünde."""
    if schritt.bis_tag >= OFFENES_ENDE:
        return f"ab J{schritt.von_tag} (offen)"
    if schritt.von_tag == schritt.bis_tag:
        return f"J{schritt.von_tag}"
    return f"J{schritt.von_tag}–J{schritt.bis_tag}"


def _erreger(schritt: Schritt) -> list[str]:
    """Die Erreger im Titel — leer, wenn keiner erkannt wird."""
    text = schritt.titel.lower()
    raus: list[str] = []
    for schluessel, name in ERREGER:
        if schluessel in text and name not in raus:
            raus.append(name)
    return raus


def _themen(blatt: Programm) -> tuple[dict[str, list[Schritt]], list[str]]:
    """Schritte nach Thema, plus die Impfungen ohne erkannten Erreger.

    Gleichartige Gaben behalten ihre Reihenfolge — aus ihr wird die Zählung
    („1., 2., 3. Gabe“), nicht aus dem Namen.
    """
    raus: dict[str, list[Schritt]] = {}
    unbekannt: list[str] = []
    for schritt in sorted(blatt.schritte, key=lambda s: (s.von_tag, s.key)):
        if schritt.kategorie in BEGLEITEND:
            namen = [THEMA_NAME[schritt.kategorie]]
        elif schritt.kategorie is Kategorie.IMPFUNG:
            erreger = _erreger(schritt)
            if not erreger:
                unbekannt.append(schritt.titel)
                erreger = [schritt.titel]
            namen = [f"Impfung: {e}" for e in erreger]
        else:
            namen = [THEMA_NAME.get(schritt.kategorie, schritt.kategorie.value)]
        for name in namen:
            raus.setdefault(name, []).append(schritt)
    return raus, unbekannt


def _zusammenfassung(schritte: list[Schritt]) -> str:
    """Eine Zeile für ein Thema: die Fenster, bei Begleitendem die Anzahl."""
    if schritte and schritte[0].kategorie in BEGLEITEND:
        tage = sum(s.bis_tag - s.von_tag + 1 for s in schritte if s.bis_tag < OFFENES_ENDE)
        return f"{len(schritte)}× ({tage} Tage)"
    return " · ".join(_fenster(s) for s in schritte)


def _takt_text(takte: list[int]) -> str | None:
    """„alle 30 Tage“ bzw. „alle 30 / 90 Tage“ — None, wenn es keine gibt."""
    if not takte:
        return None
    return "alle " + " / ".join(str(t) for t in takte) + " Tage"


def _nicht_vergleichbar(links: Programm, rechts: Programm) -> Programmvergleich:
    return Programmvergleich(
        tierart=links.tierart,
        links_id=links.programm_id,
        rechts_id=rechts.programm_id,
        links_titel=links.titel,
        rechts_titel=rechts.titel,
        issues=[
            f"„{links.titel}“ gilt für {links.tierart.value}, "
            f"„{rechts.titel}“ für {rechts.tierart.value} — "
            "die Blätter sind nicht vergleichbar."
        ],
    )


def vergleiche(links: Programm, rechts: Programm) -> Programmvergleich:
    """Was die beiden Blätter verschieden sagen.

    Beide müssen für dieselbe Tierart gelten — sonst wäre die Tabelle eine
    Scheinpräzision, und das wird gemeldet statt gerechnet.
    """
    if links.tierart is not rechts.tierart:
        return _nicht_vergleichbar(links, rechts)

    issues: list[str] = []
    l_themen, l_offen = _themen(links)
    r_themen, r_offen = _themen(rechts)
    for blatt, offen in ((links, l_offen), (rechts, r_offen)):
        for titel in offen:
            issues.append(
                f"„{blatt.titel}“: Bei „{titel}“ ist kein Erreger erkannt — "
                "die Zeile steht für sich und ist nicht gegengestellt."
            )

    zeilen: list[Programmunterschied] = []
    for name in sorted(set(l_themen) | set(r_themen)):
        l_text = _zusammenfassung(l_themen[name]) if name in l_themen else None
        r_text = _zusammenfassung(r_themen[name]) if name in r_themen else None
        zeilen.append(
            Programmunterschied(thema=name, links=l_text, rechts=r_text, gleich=l_text == r_text)
        )

    # Die Dauerregeln entscheiden über Jahre, nicht über Wochen — ein Faktor
    # sechs im Auffrischungsintervall fällt in keiner Tageszeile auf. Eine
    # Zeile je Kategorie; das Kreuzprodukt wäre dreimal dieselbe Aussage.
    kategorien = {r.kategorie for r in links.dauerregeln} | {
        r.kategorie for r in rechts.dauerregeln
    }
    for kategorie in sorted(kategorien, key=lambda k: k.value):
        l_takte = sorted({r.intervall_tage for r in links.dauerregeln if r.kategorie is kategorie})
        r_takte = sorted({r.intervall_tage for r in rechts.dauerregeln if r.kategorie is kategorie})
        if l_takte == r_takte:
            continue
        name = THEMA_NAME.get(kategorie, kategorie.value)
        zeilen.append(
            Programmunterschied(
                thema=f"Dauerregel: {name}",
                links=_takt_text(l_takte),
                rechts=_takt_text(r_takte),
            )
        )
        issues.append(
            f"{name} als Dauerregel: „{links.titel}“ {_takt_text(l_takte) or 'gar nicht'}, "
            f"„{rechts.titel}“ {_takt_text(r_takte) or 'gar nicht'} — "
            "das ist keine Rundungsfrage, das entscheidet der Betrieb."
        )

    return Programmvergleich(
        tierart=links.tierart,
        links_id=links.programm_id,
        rechts_id=rechts.programm_id,
        links_titel=links.titel,
        rechts_titel=rechts.titel,
        zeilen=zeilen,
        nur_links=[n for n in sorted(l_themen) if n not in r_themen],
        nur_rechts=[n for n in sorted(r_themen) if n not in l_themen],
        issues=issues,
    )


def vergleiche_ids(tierart: Tierart, links_id: str, rechts_id: str) -> Programmvergleich:
    """Bequemer Zugang über die Kennungen."""
    return vergleiche(programm(tierart, links_id), programm(tierart, rechts_id))


def vergleichbare(tierart: Tierart) -> list[Programm]:
    """Alle Blätter dieser Tierart — die Auswahl für die Gegenüberstellung."""
    return alle_programme(tierart)
