"""Vorlage + Herde = Termine mit echten Daten.

Der Stichtag kommt herein, er wird nie aus der Uhr geholt — sonst ist kein
Lauf reproduzierbar und kein Test aussagekräftig.
"""

from __future__ import annotations

from datetime import date, timedelta

from elevage.einstellung import notfall_dosis
from elevage.models import (
    Ampel,
    Befund,
    Ereignis,
    Herde,
    Quittung,
    Schritt,
    Termin,
    Tierart,
)
from elevage.notfall import futterwechsel_schritte, schritte_fuer_vorfall
from elevage.programme import LEGEPHASE_AB_WOCHE, programm, programm_konflikt

VORSCHAU_TAGE = 7
"""Wie weit 'demnächst' in die Zukunft reicht."""

LEGEPHASE_HORIZONT_TAGE = 120
"""Wie weit die Dauertermine der Legeperiode vorausberechnet werden."""


def datum_von_tag(herde: Herde, lebenstag: int) -> date:
    """J1 ist der Einstalltag. Tag 0 ist der Tag davor (Vorbereitung)."""
    return herde.einstalldatum + timedelta(days=lebenstag - 1)


def alter_in_tagen(herde: Herde, stichtag: date) -> int:
    """Am Einstalltag ist die Herde einen Tag alt (J1)."""
    return (stichtag - herde.einstalldatum).days + 1


def alter_in_wochen(alter_tage: int) -> int:
    """Woche 1 = Tag 1..7. Vor dem Einstallen: Woche 0."""
    if alter_tage < 1:
        return 0
    return (alter_tage - 1) // 7 + 1


def _gilt(schritt: Schritt, herde: Herde) -> bool:
    """Bedingte Schritte hängen an einem Feld der Herde, nicht an einem Urteil."""
    if schritt.bedingt is None:
        return True
    return bool(getattr(herde, schritt.bedingt, False))


def _ampel(von: date, bis: date, stichtag: date, erledigt: bool) -> Ampel:
    """Vier Zustände — erledigt schlägt alles."""
    if erledigt:
        return Ampel.ERLEDIGT
    if stichtag > bis:
        return Ampel.ROT
    if stichtag >= von:
        return Ampel.GELB
    return Ampel.GRUEN


def _wiederkehrende_schritte(herde: Herde, bis_tag: int) -> list[Schritt]:
    """Die Dauerperiode entfalten — die Regeln des gewählten Blattes.

    Wann sie anfängt, sagt die Regel selbst (`ab_tag`); ohne Angabe gilt
    der Beginn der Legephase. Das IVOGRAIN-Blatt rechnet in Wochen, das
    VETO-Blatt nennt einen Tag — beide passen so in dieselbe Rechnung.
    """
    if herde.tierart is not Tierart.LEGEHENNE:
        return []
    legephase = 7 * (LEGEPHASE_AB_WOCHE - 1) + 1
    raus: list[Schritt] = []
    for regel in programm(herde.tierart, herde.programm_id).dauerregeln:
        tag = regel.ab_tag if regel.ab_tag is not None else legephase
        nummer = 1
        while tag <= bis_tag:
            raus.append(
                Schritt(
                    key=f"{regel.key}_{nummer}",
                    tierart=Tierart.LEGEHENNE,
                    von_tag=tag,
                    bis_tag=tag + 6,
                    titel=f"{regel.titel} ({nummer}. Gabe der Dauerperiode)",
                    titel_fr=(
                        f"{regel.titel_fr} ({nummer}e administration)" if regel.titel_fr else None
                    ),
                    kategorie=regel.kategorie,
                    verabreichung=regel.verabreichung,
                    praeparate=list(regel.praeparate),
                    hinweis=regel.hinweis,
                    hinweis_fr=regel.hinweis_fr,
                    dosis_je_liter=regel.dosis_je_liter,
                    vorlauf_tage=3,
                )
            )
            tag += regel.intervall_tage
            nummer += 1
    return raus


def schritte_fuer(
    herde: Herde,
    stichtag: date,
    ereignisse: list[Ereignis] | None = None,
    einstellungen: dict[str, str] | None = None,
) -> list[Schritt]:
    """Programm + Legeperiode + Futterwechsel + ausgelöste Notfallschemata.

    Eine Quelle für Termine UND Befunde — sonst meldet das Tagesbild die
    Widersprüche des Programms, aber nicht die eines Notfallschemas.
    """
    alter = alter_in_tagen(herde, stichtag)
    horizont = max(alter, 0) + LEGEPHASE_HORIZONT_TAGE
    blatt = programm(herde.tierart, herde.programm_id)
    schritte = [s for s in blatt.schritte if _gilt(s, herde)]
    schritte += _wiederkehrende_schritte(herde, horizont)
    schritte += futterwechsel_schritte(herde)
    dosis, vom_betrieb = notfall_dosis(einstellungen or {}, herde.tierart)
    for ereignis in ereignisse or []:
        if ereignis.herde_id != herde.herde_id or ereignis.tenant_id != herde.tenant_id:
            continue
        schritte += schritte_fuer_vorfall(ereignis, herde, dosis, vom_betrieb=vom_betrieb)
    return schritte


def baue_termine(
    herde: Herde,
    stichtag: date,
    quittungen: list[Quittung] | None = None,
    ereignisse: list[Ereignis] | None = None,
    einstellungen: dict[str, str] | None = None,
) -> list[Termin]:
    """Alle Termine dieser Herde, chronologisch."""
    quittungen = quittungen or []
    quittiert: dict[str, Quittung] = {}
    for q in quittungen:
        if q.herde_id != herde.herde_id or q.tenant_id != herde.tenant_id:
            continue
        # Mehrfach nachgereichte Quittungen: die früheste zählt — damit ist
        # der Offline-Sync idempotent und wiederholbares Senden harmlos.
        vorhanden: Quittung | None = quittiert.get(q.schritt_key)
        if vorhanden is None or q.erledigt_am < vorhanden.erledigt_am:
            quittiert[q.schritt_key] = q

    schritte = schritte_fuer(herde, stichtag, ereignisse, einstellungen)

    termine: list[Termin] = []
    for s in schritte:
        von = datum_von_tag(herde, s.von_tag)
        bis = datum_von_tag(herde, s.bis_tag)
        quittung = quittiert.get(s.key)
        termine.append(
            Termin(
                herde_id=herde.herde_id,
                schritt_key=s.key,
                titel=s.titel,
                kategorie=s.kategorie,
                verabreichung=s.verabreichung,
                praeparate=s.praeparate,
                faellig_von=von,
                faellig_bis=bis,
                tage_bis=(von - stichtag).days,
                ampel=_ampel(von, bis, stichtag, quittung is not None),
                bedingt=s.bedingt,
                hinweis=s.hinweis,
                titel_fr=s.titel_fr,
                hinweis_fr=s.hinweis_fr,
                dosis_je_liter=s.dosis_je_liter,
                quelle=s.quelle,
                erledigt_am=quittung.erledigt_am if quittung else None,
                lot=quittung.lot if quittung else None,
            )
        )
    termine.sort(key=lambda t: (t.faellig_von, t.schritt_key))
    return termine


def offene_issues(
    herde: Herde,
    stichtag: date,
    ereignisse: list[Ereignis] | None = None,
    einstellungen: dict[str, str] | None = None,
) -> list[Befund]:
    """Widersprüche, die in den geltenden Schritten stecken — ohne Dopplung.

    Der Schlüssel des Schritts kommt vor beide Fassungen: er ist die
    Nummer, unter der jemand den Widerspruch am Papier nachschlägt, und
    die ist in keiner Sprache eine andere.
    """
    raus: list[Befund] = []
    gesehen: set[str] = set()
    konflikt = programm_konflikt(herde.tierart, herde.programm_id)
    if konflikt:
        raus.append(konflikt)
        gesehen.add(konflikt.text)
    for s in schritte_fuer(herde, stichtag, ereignisse, einstellungen):
        for i in s.issues:
            zeile = f"{s.key}: {i.text}"
            if zeile in gesehen:
                continue
            gesehen.add(zeile)
            raus.append(
                Befund(
                    text=zeile,
                    text_fr=f"{s.key}: {i.text_fr}" if i.text_fr else None,
                )
            )
    return raus
