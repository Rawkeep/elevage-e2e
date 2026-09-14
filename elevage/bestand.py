"""Wie viele Tiere wirklich im Stall stehen.

Die Tierzahl beim Einstallen ist ein Anfangswert, kein Dauerzustand. Wer
mit ihr weiterrechnet, bekommt einen Fehler, der mit der Zeit wächst und
nie auffällt: die Verzehrkurve wird zu niedrig (dieselbe Futtermenge auf
zu viele Tiere), und Mischmengen und Bestellzeitpunkte erben das.

Verluste sind außerdem selbst die Kennzahl, an der ein Ausbruch zuerst
sichtbar wird — eher als an jedem Symptom, das jemand beschreibt.

Wie überall hier: der Stichtag kommt herein, Bewegungen sind Ereignisse
mit eigener Nummer, und eine Lücke wird gemeldet statt geglättet.
"""

from __future__ import annotations

from datetime import date, timedelta

from elevage.models import Befund, Bestand, Bestandsbewegung, Herde, befund

VERLUST_WARNSCHWELLE_PROZENT = 5.0
"""Ab hier wird der Verlust im Tagesbild als Befund genannt.

Eine Zahl, die dem Betrieb gehört, nicht dem Programm: 5 % über die
Aufzucht sind üblich, 5 % in einer Woche sind es nicht. Der Taktgeber
meldet den Stand, er urteilt nicht über die Ursache."""

HAEUFUNG_TAGE = 7
HAEUFUNG_PROZENT = 2.0
"""Verluste in kurzer Zeit sind etwas anderes als dieselbe Zahl über Monate."""


def _meine(herde: Herde, bewegungen: list[Bestandsbewegung]) -> list[Bestandsbewegung]:
    return [
        b for b in bewegungen if b.herde_id == herde.herde_id and b.tenant_id == herde.tenant_id
    ]


def rechne_bestand(herde: Herde, stichtag: date, bewegungen: list[Bestandsbewegung]) -> Bestand:
    """Der Stand an diesem Tag — Bewegungen nach dem Stichtag zählen nicht mit."""
    bis_stichtag = [b for b in _meine(herde, bewegungen) if b.am <= stichtag]
    abgang = sum(b.abgang for b in bis_stichtag)
    zugang = sum(b.zugang for b in bis_stichtag)
    tierzahl = herde.tierzahl - abgang + zugang

    issues: list[Befund] = []
    if tierzahl < 0:
        issues.append(
            befund(
                f"Mehr Abgänge ({abgang}) als je eingestallt ({herde.tierzahl}) — "
                "hier stimmt eine Buchung nicht.",
                f"Plus de sorties ({abgang}) que d'animaux jamais mis en place "
                f"({herde.tierzahl}) — une écriture ne va pas.",
            )
        )
        tierzahl = 0

    verluste = sum(b.abgang for b in bis_stichtag if b.grund.value in ("VERENDET", "GEKEULT"))
    anteil = round(verluste / herde.tierzahl * 100, 2) if herde.tierzahl else 0.0
    if anteil >= VERLUST_WARNSCHWELLE_PROZENT:
        issues.append(
            befund(
                f"Verluste seit dem Einstallen: {verluste} Tiere ({anteil:.1f} %).",
                f"Pertes depuis la mise en place : {verluste} animaux ({anteil:.1f} %).",
            )
        )

    seit = stichtag - timedelta(days=HAEUFUNG_TAGE)
    jung = sum(
        b.abgang for b in bis_stichtag if b.am > seit and b.grund.value in ("VERENDET", "GEKEULT")
    )
    jung_anteil = round(jung / herde.tierzahl * 100, 2) if herde.tierzahl else 0.0
    if jung_anteil >= HAEUFUNG_PROZENT:
        issues.append(
            befund(
                f"Häufung: {jung} Tiere ({jung_anteil:.1f} %) in den letzten "
                f"{HAEUFUNG_TAGE} Tagen. Das ist etwas anderes als dieselbe Zahl "
                "über Monate.",
                f"Concentration : {jung} animaux ({jung_anteil:.1f} %) sur les "
                f"{HAEUFUNG_TAGE} derniers jours. Ce n'est pas la même chose que "
                "le même chiffre étalé sur des mois.",
            )
        )

    if not bis_stichtag:
        issues.append(
            befund(
                "Keine Bestandsbewegung erfasst — gerechnet wird mit der Einstallzahl. "
                "Ohne Abgänge ist die Verzehrkurve zu niedrig.",
                "Aucun mouvement d'effectif saisi — le calcul part du nombre mis en "
                "place. Sans les sorties, la courbe de consommation est trop basse.",
            )
        )

    return Bestand(
        herde_id=herde.herde_id,
        stichtag=stichtag,
        eingestallt=herde.tierzahl,
        abgang_gesamt=abgang,
        zugang_gesamt=zugang,
        tierzahl=tierzahl,
        verluste_prozent=anteil,
        issues=issues,
    )


def tierzahl_am(herde: Herde, stichtag: date, bewegungen: list[Bestandsbewegung]) -> int:
    return rechne_bestand(herde, stichtag, bewegungen).tierzahl


def mittlere_tierzahl(
    herde: Herde, von: date, bis: date, bewegungen: list[Bestandsbewegung]
) -> float:
    """Für einen Zeitraum — die Verzehrkurve rechnet nicht auf einen Tag.

    Gemittelt wird über Anfang und Ende, nicht tagesgenau integriert: bei
    den Stückzahlen eines Stalls ändert das nichts, und die einfachere
    Rechnung ist die nachvollziehbarere.
    """
    return (tierzahl_am(herde, von, bewegungen) + tierzahl_am(herde, bis, bewegungen)) / 2
