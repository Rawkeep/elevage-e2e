"""Der Taktgeber: eine Herde, ein Stichtag, das ganze Bild.

`rechne()` ruft nur die anderen Module auf und entscheidet selbst nichts
Fachliches — deshalb ist die Oberfläche darüber austauschbar (CLI heute,
Web-App morgen). Der Stichtag kommt herein, nie aus der Uhr.
"""

from __future__ import annotations

from datetime import date

from elevage.anpassung import wirksames_rezept
from elevage.bestand import rechne_bestand
from elevage.mischung import baue_mischauftrag
from elevage.models import (
    Ampel,
    Ausgleichsart,
    Befund,
    Bestandsbewegung,
    Ereignis,
    Herde,
    Kategorie,
    Mischauftrag,
    Praeparat,
    Pruefvermerk,
    Quittung,
    Rezeptanpassung,
    Tagesbild,
    Termin,
    Tierarzt,
    Verzehrkurve,
    befund,
)
from elevage.plan import (
    VORSCHAU_TAGE,
    alter_in_tagen,
    alter_in_wochen,
    baue_termine,
    offene_issues,
    schritte_fuer,
)
from elevage.programme import programm
from elevage.rezepte import KEIN_MASTFUTTER, PHASEN_UEBERLAPPUNG, rezept_fuer
from elevage.verzehr import prognose, richtwert
from elevage.wartezeit import berechne_sperren


def rechne(
    herde: Herde,
    stichtag: date,
    quittungen: list[Quittung] | None = None,
    ereignisse: list[Ereignis] | None = None,
    *,
    kurve: Verzehrkurve | None = None,
    vorrat_kg: float | None = None,
    kurven_issues: list[Befund] | None = None,
    einstellungen: dict[str, str] | None = None,
    anpassungen: list[Rezeptanpassung] | None = None,
    vermerke: list[Pruefvermerk] | None = None,
    praeparate: list[Praeparat] | None = None,
    bewegungen: list[Bestandsbewegung] | None = None,
    tierarzt: Tierarzt | None = None,
) -> Tagesbild:
    alter = alter_in_tagen(herde, stichtag)
    wochen = alter_in_wochen(alter)
    blatt = programm(herde.tierart, herde.programm_id)
    stand = rechne_bestand(herde, stichtag, list(bewegungen or []))
    termine = baue_termine(herde, stichtag, quittungen, ereignisse, einstellungen)

    # Eine Pause ist eine Anweisung, keine Aufgabe: „einfaches Wasser“ steht
    # im Stand und wird nicht abgehakt. Sie aus den Terminen zu lassen wäre
    # falsch — dann sähe niemand, dass die Lücke gewollt ist.
    ruhe = [
        t
        for t in termine
        if t.kategorie is Kategorie.PAUSE and t.faellig_von <= stichtag <= t.faellig_bis
    ]
    arbeit = [t for t in termine if t.kategorie is not Kategorie.PAUSE]

    ueberfaellig = [t for t in arbeit if t.ampel is Ampel.ROT]
    heute = [t for t in arbeit if t.ampel is Ampel.GELB]
    demnaechst = [t for t in arbeit if t.ampel is Ampel.GRUEN and 0 < t.tage_bis <= VORSCHAU_TAGE]
    erledigt = [t for t in arbeit if t.ampel is Ampel.ERLEDIGT]

    vorlauf = {
        s.key: s.vorlauf_tage for s in schritte_fuer(herde, stichtag, ereignisse, einstellungen)
    }
    bestellen = [
        t
        for t in arbeit
        if t.ampel is Ampel.GRUEN
        and vorlauf.get(t.schritt_key, 3) > 0
        and 0 < t.tage_bis <= vorlauf.get(t.schritt_key, 3)
    ]

    issues = offene_issues(herde, stichtag, ereignisse, einstellungen)
    phase = rezept_fuer(herde.tierart, wochen)
    if phase is not None and anpassungen:
        phase = wirksames_rezept(phase, anpassungen)
    if phase is None:
        issues.append(
            KEIN_MASTFUTTER
            if herde.tierart.name == "MASTHUHN"
            else befund(
                "Für diese Lebenswoche liegt kein Futterblatt vor.",
                "Aucune fiche d'alimentation pour cette semaine d'âge.",
            )
        )
    else:
        issues.append(PHASEN_UEBERLAPPUNG)

    # Die Kurve entscheidet nichts — sie liefert eine Zahl mit Herkunft.
    futter = prognose(
        herde,
        stichtag,
        wochen,
        kurve or richtwert(herde.tierart),
        tierzahl=stand.tierzahl,
        vorrat_kg=vorrat_kg,
        zusatz_issues=kurven_issues,
    )
    issues.extend(futter.issues)
    issues.extend(stand.issues)

    sperren, sperr_issues = berechne_sperren(
        herde,
        stichtag,
        list(quittungen or []),
        schritte_fuer(herde, stichtag, ereignisse, einstellungen),
        list(praeparate or []),
    )
    issues.extend(sperr_issues)

    meine_vorfaelle = [
        e
        for e in (ereignisse or [])
        if e.herde_id == herde.herde_id and e.tenant_id == herde.tenant_id
    ]

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
        programm_id=blatt.programm_id,
        programm_titel=blatt.titel,
        programm_titel_fr=blatt.titel_fr,
        phase=phase,
        ueberfaellig=ueberfaellig,
        heute=heute,
        demnaechst=demnaechst,
        bestellen=bestellen,
        erledigt=erledigt,
        ruhe=ruhe,
        vermerke=list(vermerke or []),
        sperren=sperren,
        bestand=stand,
        futter=futter,
        vorfaelle=meine_vorfaelle,
        tierarzt=tierarzt,
        ampel=ampel,
        issues=issues,
    )


def mischauftrag_fuer(
    bild: Tagesbild,
    ziel_kg: float,
    *,
    art: Ausgleichsart = Ausgleichsart.AUSGLEICH,
) -> Mischauftrag | None:
    """Die Mischung zur aktuellen Phase — None, wenn es keine gibt."""
    if bild.phase is None:
        return None
    return baue_mischauftrag(bild.phase, ziel_kg, art=art)


def naechster_schritt(bild: Tagesbild) -> Termin | None:
    """Das eine, was als Nächstes zu tun ist — überfällig schlägt fällig."""
    for liste in (bild.ueberfaellig, bild.heute, bild.demnaechst):
        if liste:
            return liste[0]
    return None
