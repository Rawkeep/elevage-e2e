"""Mischauftrag: Rezept × Chargengröße — mit Summenprobe.

Die Blätter summieren sich nicht auf ihre Überschrift. Dieses Modul rechnet
**verbatim** und meldet die Abweichung; normiert wird nur auf ausdrückliche
Anweisung (`normieren=True`). Eine Software, die stillschweigend auf 100
zieht, trifft eine fachliche Entscheidung, die ihr niemand übertragen hat.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from elevage.models import Mischauftrag, Mischzeile, Rezept
from elevage.rezepte import SPERR_SCHWELLE_KG, SUMMEN_TOLERANZ_KG

WAAGE_STELLEN = 2
"""Auf 10 g genau — feiner kann die Betriebswaage nicht."""


def _runde(wert: float, stellen: int = WAAGE_STELLEN) -> float:
    """Kaufmännisch runden, nicht zur geraden Zahl — sonst weicht die
    Einwaage vom handgerechneten Blatt ab."""
    q = Decimal(1).scaleb(-stellen)
    return float(Decimal(str(wert)).quantize(q, rounding=ROUND_HALF_UP))


def baue_mischauftrag(rezept: Rezept, ziel_kg: float, *, normieren: bool = False) -> Mischauftrag:
    """Waage-Liste für eine Charge.

    `ziel_kg` ist die Menge, die das Blatt meint (100/500/1000 …).
    `ist_einwaage_kg` ist, was tatsächlich im Mischer landet — bei einem
    Rezept über 100 kg je 100 kg ist das mehr.
    """
    if ziel_kg <= 0:
        raise ValueError("ziel_kg muss größer als 0 sein")

    summe = rezept.summe_je_100
    abweichung = _runde(summe - 100.0, 4)
    issues: list[str] = []

    faktor = ziel_kg / 100.0
    if normieren:
        faktor = faktor * 100.0 / summe

    zeilen = [
        Mischzeile(
            artikel_id=p.artikel_id,
            name=p.name,
            kg=_runde(p.kg_je_100 * faktor),
        )
        for p in rezept.posten
    ]
    ist = _runde(sum(z.kg for z in zeilen))

    if abs(abweichung) > SUMMEN_TOLERANZ_KG:
        issues.append(
            f"Rezept '{rezept.name}' summiert auf {summe:.2f} kg je 100 kg "
            f"({abweichung:+.2f} kg). Quelle: {rezept.quelle}."
        )
        if normieren:
            issues.append(
                f"Auf {ziel_kg:.0f} kg normiert — jede Komponente wurde mit "
                f"{100.0 / summe:.4f} skaliert. Das weicht vom Blatt ab."
            )
        else:
            issues.append(
                f"Verbatim gerechnet: es gehen {ist:.2f} kg in den Mischer, nicht {ziel_kg:.2f} kg."
            )

    freigegeben = normieren or abs(abweichung) <= SPERR_SCHWELLE_KG
    if not freigegeben:
        issues.append(
            f"GESPERRT: Abweichung über {SPERR_SCHWELLE_KG:.2f} kg je 100 kg. "
            "Ein Mensch muss entscheiden, welche Zeile falsch ist — oder "
            "'normieren' ausdrücklich wählen."
        )

    return Mischauftrag(
        rezept_key=rezept.key,
        rezept_name=rezept.name,
        ziel_kg=_runde(ziel_kg),
        normiert=normieren,
        zeilen=zeilen,
        ist_einwaage_kg=ist,
        summe_je_100=summe,
        abweichung_je_100=abweichung,
        freigegeben=freigegeben,
        issues=issues,
    )
