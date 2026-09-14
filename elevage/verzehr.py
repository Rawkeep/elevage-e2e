"""Verzehrkurve: was ein Tier je Lebenswoche am Tag frisst.

Ohne diese Zahl kann der Taktgeber mischen, aber nicht vorhersagen, wann
der Sack leer ist. Sie kommt aus zwei Quellen, in dieser Reihenfolge:

1. **Gemessen** aus dem eigenen Mischprotokoll: was zwischen zwei Mischungen
   verbraucht wurde, geteilt durch Tierzahl und Tage. Das ist die Zahl des
   Betriebs — Rasse, Klima und Fütterung stecken schon drin.
2. **Richtwert** als Lückenfüller, bis genug gemischt wurde.

Die Richtwerte unten sind **grobe Orientierung, keine Betriebsdaten**. Sie
existieren, damit die Prognose überhaupt anläuft, und werden von jedem
gemessenen Punkt geschlagen. Eine Prognose, die auf ihnen steht, sagt das
in `issues` — eine Bestellmenge auf geratener Grundlage wäre sonst nicht
von einer gerechneten zu unterscheiden.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

from elevage.models import (
    Befund,
    Futterprognose,
    Herde,
    KurvePunkt,
    Quelle,
    Tierart,
    Verzehrkurve,
    befund,
)

PROGNOSE_HORIZONT_TAGE = 14
"""Wie weit die Bedarfsrechnung vorausschaut."""

FUTTER_VORLAUF_TAGE = 5
"""Wie früh vor dem leeren Lager bestellt werden muss."""

MIN_TAGE_JE_MESSUNG = 2
"""Kürzere Abstände zwischen zwei Mischungen sind keine Verbrauchsmessung."""

MAX_GRAMM_JE_TIER_TAG = 400.0
"""Obergrenze der Plausibilität — darüber war es eine Vorratsmischung."""


def _punkte(werte: dict[int, float]) -> list[KurvePunkt]:
    return [
        KurvePunkt(woche=w, gramm_je_tier_tag=g, quelle=Quelle.RICHTWERT, basis="Richtwert")
        for w, g in sorted(werte.items())
    ]


RICHTWERT_LEGEHENNE = Verzehrkurve(
    tierart=Tierart.LEGEHENNE,
    punkte=_punkte(
        {
            1: 13.0,
            2: 20.0,
            3: 27.0,
            4: 34.0,
            5: 40.0,
            6: 45.0,
            8: 50.0,
            10: 60.0,
            12: 70.0,
            14: 75.0,
            16: 80.0,
            18: 85.0,
            20: 95.0,
            22: 105.0,
            26: 110.0,
        }
    ),
)

RICHTWERT_MASTHUHN = Verzehrkurve(
    tierart=Tierart.MASTHUHN,
    punkte=_punkte({1: 20.0, 2: 40.0, 3: 65.0, 4: 95.0, 5: 120.0, 6: 140.0}),
)

RICHTWERT_HINWEIS = befund(
    "Diese Prognose steht auf Richtwerten, nicht auf Zahlen dieses Betriebs. "
    "Sie schärft sich mit jeder protokollierten Mischung von selbst.",
    "Cette prévision repose sur des valeurs indicatives, pas sur les chiffres de "
    "cette exploitation. Elle s'affine d'elle-même à chaque mélange enregistré.",
)


def richtwert(tierart: Tierart) -> Verzehrkurve:
    return RICHTWERT_LEGEHENNE if tierart is Tierart.LEGEHENNE else RICHTWERT_MASTHUHN


def aus_mischungen(
    tierart: Tierart,
    tierzahl: int,
    einstalldatum: date,
    mischungen: list[tuple[date, float]],
    tierzahl_im_zeitraum: Callable[[date, date], float] | None = None,
) -> tuple[Verzehrkurve, list[Befund]]:
    """Verbrauch zwischen zwei Mischungen ⇒ gemessene Kurve.

    `mischungen` sind (Datum, Ist-Einwaage in kg). Die Annahme dahinter ist
    ausdrücklich: was gemischt wurde, ist bis zur nächsten Mischung
    gefressen. Die **letzte** Mischung hat kein Ende und wird deshalb
    übersprungen — gezählt, nicht als Null verbucht.
    """
    issues: list[Befund] = []
    if tierzahl <= 0:
        return Verzehrkurve(tierart=tierart), [
            befund(
                "Tierzahl 0 — keine Messung möglich.",
                "Effectif nul — aucune mesure possible.",
            )
        ]

    sortiert = sorted(mischungen)
    je_woche: dict[int, list[tuple[float, str]]] = {}
    uebersprungen = 0

    for i in range(len(sortiert) - 1):
        von, kg = sortiert[i]
        bis, _ = sortiert[i + 1]
        tage = (bis - von).days
        if tage < MIN_TAGE_JE_MESSUNG:
            uebersprungen += 1
            continue
        im_zeitraum = tierzahl_im_zeitraum(von, bis) if tierzahl_im_zeitraum else float(tierzahl)
        if im_zeitraum <= 0:
            uebersprungen += 1
            continue
        gramm = kg * 1000.0 / im_zeitraum / tage
        if gramm <= 0 or gramm > MAX_GRAMM_JE_TIER_TAG:
            uebersprungen += 1
            continue
        mitte = von + timedelta(days=tage // 2)
        woche = max(1, ((mitte - einstalldatum).days) // 7 + 1)
        je_woche.setdefault(woche, []).append(
            (gramm, f"{kg:.0f} kg über {tage} Tage ab {von.isoformat()}")
        )

    if sortiert:
        uebersprungen += 1  # die letzte Mischung ist noch im Trog

    punkte = []
    for woche, werte in sorted(je_woche.items()):
        schnitt = sum(g for g, _ in werte) / len(werte)
        punkte.append(
            KurvePunkt(
                woche=woche,
                gramm_je_tier_tag=round(schnitt, 1),
                quelle=Quelle.GEMESSEN,
                basis="; ".join(b for _, b in werte),
            )
        )

    if uebersprungen:
        issues.append(
            befund(
                f"{uebersprungen} Mischung(en) nicht in die Kurve eingerechnet "
                "(letzte Mischung noch im Trog, zu kurzer Abstand oder unplausibel).",
                f"{uebersprungen} mélange(s) non intégré(s) à la courbe (dernier "
                "mélange encore à l'auge, intervalle trop court ou invraisemblable).",
            )
        )
    return Verzehrkurve(tierart=tierart, punkte=punkte), issues


def kombiniere(gemessen: Verzehrkurve, ersatz: Verzehrkurve) -> Verzehrkurve:
    """Gemessene Punkte schlagen Richtwerte, Wochenweise. Lücken bleiben Richtwert."""
    nach_woche: dict[int, KurvePunkt] = {p.woche: p for p in ersatz.punkte}
    nach_woche.update({p.woche: p for p in gemessen.punkte})
    return Verzehrkurve(
        tierart=gemessen.tierart,
        punkte=[nach_woche[w] for w in sorted(nach_woche)],
    )


def prognose(
    herde: Herde,
    stichtag: date,
    woche: int,
    kurve: Verzehrkurve,
    *,
    tierzahl: int | None = None,
    vorrat_kg: float | None = None,
    horizont_tage: int = PROGNOSE_HORIZONT_TAGE,
    zusatz_issues: list[Befund] | None = None,
) -> Futterprognose:
    """Tagesbedarf, Reichweite und Bestelltag — mit Herkunft an jeder Zahl."""
    issues = list(zusatz_issues or [])
    punkt = kurve.fuer_woche(woche)

    if punkt is None:
        issues.append(
            befund(
                f"Keine Verzehrzahl für Woche {woche} — weder gemessen noch als "
                "Richtwert. Ohne sie gibt es keine Reichweite und keinen Bestelltag.",
                f"Aucune valeur de consommation pour la semaine {woche} — ni mesurée "
                "ni indicative. Sans elle, pas d'autonomie ni de jour de commande.",
            )
        )
        return Futterprognose(
            herde_id=herde.herde_id,
            stichtag=stichtag,
            woche=woche,
            horizont_tage=horizont_tage,
            vorrat_kg=vorrat_kg,
            issues=issues,
        )

    if punkt.quelle is Quelle.RICHTWERT:
        issues.append(RICHTWERT_HINWEIS)

    im_stall = herde.tierzahl if tierzahl is None else tierzahl
    je_tag = round(punkt.gramm_je_tier_tag * im_stall / 1000.0, 2)
    bis_horizont = round(je_tag * horizont_tage, 2)

    reicht_bis: date | None = None
    bestellen_ab: date | None = None
    if vorrat_kg is not None:
        if je_tag <= 0:
            issues.append(
                befund(
                    "Tagesbedarf 0 — Reichweite nicht berechenbar.",
                    "Besoin journalier nul — autonomie incalculable.",
                )
            )
        else:
            tage = int(vorrat_kg / je_tag)
            reicht_bis = stichtag + timedelta(days=tage)
            bestellen_ab = reicht_bis - timedelta(days=FUTTER_VORLAUF_TAGE)
            if bestellen_ab <= stichtag:
                issues.append(
                    befund(
                        f"Vorrat reicht nur bis {reicht_bis:%d.%m.} — "
                        f"Bestellvorlauf von {FUTTER_VORLAUF_TAGE} Tagen ist bereits "
                        "angebrochen.",
                        f"Le stock ne tient que jusqu'au {reicht_bis:%d.%m.} — le délai "
                        f"de commande de {FUTTER_VORLAUF_TAGE} jours est déjà entamé.",
                    )
                )

    return Futterprognose(
        herde_id=herde.herde_id,
        stichtag=stichtag,
        woche=woche,
        gramm_je_tier_tag=punkt.gramm_je_tier_tag,
        quelle=punkt.quelle,
        bedarf_je_tag_kg=je_tag,
        bedarf_bis_horizont_kg=bis_horizont,
        horizont_tage=horizont_tage,
        vorrat_kg=vorrat_kg,
        reicht_bis=reicht_bis,
        bestellen_ab=bestellen_ab,
        issues=issues,
    )
