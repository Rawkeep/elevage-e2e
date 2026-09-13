"""Der Taktgeber: eine Herde, ein Stichtag, das ganze Bild.

`rechne()` ruft nur die anderen Module auf und entscheidet selbst nichts
Fachliches — deshalb ist die Oberfläche darüber austauschbar (CLI heute,
Web-App morgen). Der Stichtag kommt herein, nie aus der Uhr.
"""

from __future__ import annotations

from datetime import date

from elevage.mischung import baue_mischauftrag
from elevage.models import Ampel, Herde, Mischauftrag, Quittung, Tagesbild, Termin
from elevage.plan import (
    VORSCHAU_TAGE,
    alter_in_tagen,
    alter_in_wochen,
    baue_termine,
    offene_issues,
)
from elevage.programme import programm
from elevage.rezepte import KEIN_MASTFUTTER, PHASEN_UEBERLAPPUNG, rezept_fuer

TAGESVERZEHR_UNBEKANNT = (
    "Ohne Verzehrkurve (g/Tier/Tag je Alterswoche) kann der Taktgeber mischen, "
    "aber keine Reichweite und keinen Bestellzeitpunkt vorhersagen."
)


def rechne(
    herde: Herde,
    stichtag: date,
    quittungen: list[Quittung] | None = None,
) -> Tagesbild:
    alter = alter_in_tagen(herde, stichtag)
    wochen = alter_in_wochen(alter)
    termine = baue_termine(herde, stichtag, quittungen)

    ueberfaellig = [t for t in termine if t.ampel is Ampel.ROT]
    heute = [t for t in termine if t.ampel is Ampel.GELB]
    demnaechst = [t for t in termine if t.ampel is Ampel.GRUEN and 0 < t.tage_bis <= VORSCHAU_TAGE]
    erledigt = [t for t in termine if t.ampel is Ampel.ERLEDIGT]

    vorlauf = {s.key: s.vorlauf_tage for s in programm(herde.tierart)}
    bestellen = [
        t
        for t in termine
        if t.ampel is Ampel.GRUEN
        and vorlauf.get(t.schritt_key, 3) > 0
        and 0 < t.tage_bis <= vorlauf.get(t.schritt_key, 3)
    ]

    issues = offene_issues(herde)
    phase = rezept_fuer(herde.tierart, wochen)
    if phase is None:
        issues.append(
            KEIN_MASTFUTTER
            if herde.tierart.name == "MASTHUHN"
            else "Für diese Lebenswoche liegt kein Futterblatt vor."
        )
    else:
        issues.append(PHASEN_UEBERLAPPUNG)
    issues.append(TAGESVERZEHR_UNBEKANNT)

    if ueberfaellig:
        ampel = Ampel.ROT
    elif heute:
        ampel = Ampel.GELB
    else:
        ampel = Ampel.GRUEN

    return Tagesbild(
        stichtag=stichtag,
        herde=herde,
        alter_tage=alter,
        alter_wochen=wochen,
        phase=phase,
        ueberfaellig=ueberfaellig,
        heute=heute,
        demnaechst=demnaechst,
        bestellen=bestellen,
        erledigt=erledigt,
        ampel=ampel,
        issues=issues,
    )


def mischauftrag_fuer(
    bild: Tagesbild, ziel_kg: float, *, normieren: bool = False
) -> Mischauftrag | None:
    """Die Mischung zur aktuellen Phase — None, wenn es keine gibt."""
    if bild.phase is None:
        return None
    return baue_mischauftrag(bild.phase, ziel_kg, normieren=normieren)


def naechster_schritt(bild: Tagesbild) -> Termin | None:
    """Das eine, was als Nächstes zu tun ist — überfällig schlägt fällig."""
    for liste in (bild.ueberfaellig, bild.heute, bild.demnaechst):
        if liste:
            return liste[0]
    return None
