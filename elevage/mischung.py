"""Mischauftrag: Rezept × Chargengröße — mit Summenprobe und Ausgleich.

Die Blätter summieren sich nicht auf ihre Überschrift. Drei Wege stehen zur
Wahl, und die Ausgabe sagt immer, welcher gegangen wurde:

* **AUSGLEICH** (Vorgabe) — der Überhang wird aus **einem benannten Posten**
  genommen, dem Energieträger. Kalk, Aminosäuren und Konzentrat stehen für
  eine Funktion; ihre Menge ist die Aussage des Rezepts, nicht sein Puffer.
* **VERBATIM** — gerechnet wie auf dem Blatt. Dann gehen 1067 kg in den
  Mischer, wo 1000 draufsteht, und genau das wird gemeldet.
* **ANTEILIG** — alles gleichmäßig skaliert. Trifft die Zielmenge, ändert
  aber jeden Anteil.

Ausgeglichen wird nie stumm: jeder Auftrag trägt den Vorher-Nachher-Wert
und einen Text für den Prüfvermerk, den der Betrieb später abarbeitet.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from elevage.models import Ausgleichsart, Mischauftrag, Mischzeile, Posten, Rezept
from elevage.rezepte import AUSGLEICH_GRENZE_KG, SUMMEN_TOLERANZ_KG, ausgleichsposten

WAAGE_STELLEN = 2
"""Auf 10 g genau — feiner kann die Betriebswaage nicht."""


def _runde(wert: float, stellen: int = WAAGE_STELLEN) -> float:
    """Kaufmännisch runden, nicht zur geraden Zahl — sonst weicht die
    Einwaage vom handgerechneten Blatt ab."""
    q = Decimal(1).scaleb(-stellen)
    return float(Decimal(str(wert)).quantize(q, rounding=ROUND_HALF_UP))


def abweichung(rezept: Rezept) -> float:
    """Wie weit die 100-kg-Spalte von 100 kg entfernt ist."""
    return _runde(rezept.summe_je_100 - 100.0, 4)


def vermerk_text(rezept: Rezept, artikel_id: str, alt: float, neu: float) -> str:
    """Der Satz, der als Prüfvermerk liegen bleibt, bis ein Mensch ihn abhakt."""
    name = next(p.name for p in rezept.posten if p.artikel_id == artikel_id)
    return (
        f"Rezept „{rezept.name}“ geht nicht auf 100 kg auf "
        f"({rezept.summe_je_100:.2f} kg je 100 kg). Der Überhang von "
        f"{abweichung(rezept):+.2f} kg wird über {name} ausgeglichen "
        f"({alt:.2f} → {neu:.2f} kg je 100 kg). Quelle: {rezept.quelle}. "
        "Bitte am Original prüfen, welche Zeile falsch abgeschrieben wurde."
    )


def _ausgeglichene_posten(
    rezept: Rezept, delta: float
) -> tuple[list[Posten], str, float, float, list[str]]:
    """Den Überhang aus einem Posten nehmen. Meldet, wenn das nicht geht."""
    ziel = ausgleichsposten(rezept)
    alt = next(p.kg_je_100 for p in rezept.posten if p.artikel_id == ziel)
    neu = _runde(alt - delta, 4)
    issues: list[str] = []
    if neu <= 0:
        issues.append(
            f"GESPERRT: Der Überhang von {delta:+.2f} kg ist größer als der "
            f"Ausgleichsposten ({alt:.2f} kg). Hier stimmt mehr als eine Zeile nicht."
        )
        return list(rezept.posten), ziel, alt, alt, issues
    posten = [
        p.model_copy(update={"kg_je_100": neu}) if p.artikel_id == ziel else p
        for p in rezept.posten
    ]
    return posten, ziel, alt, neu, issues


def baue_mischauftrag(
    rezept: Rezept,
    ziel_kg: float,
    *,
    art: Ausgleichsart = Ausgleichsart.AUSGLEICH,
) -> Mischauftrag:
    """Waage-Liste für eine Charge.

    `ziel_kg` ist die Menge, die das Blatt meint (100/500/1000 …).
    `ist_einwaage_kg` ist, was tatsächlich im Mischer landet.
    """
    if ziel_kg <= 0:
        raise ValueError("ziel_kg muss größer als 0 sein")

    summe = rezept.summe_je_100
    delta = abweichung(rezept)
    issues: list[str] = []
    posten = list(rezept.posten)
    ziel_posten: str | None = None
    faktor = ziel_kg / 100.0
    freigegeben = True

    if abs(delta) <= SUMMEN_TOLERANZ_KG:
        art = Ausgleichsart.VERBATIM  # nichts auszugleichen
    else:
        issues.append(
            f"Rezept „{rezept.name}“ summiert auf {summe:.2f} kg je 100 kg "
            f"({delta:+.2f} kg). Quelle: {rezept.quelle}."
        )
        if art is Ausgleichsart.AUSGLEICH and abs(delta) > AUSGLEICH_GRENZE_KG:
            issues.append(
                f"GESPERRT: {delta:+.2f} kg je 100 kg ist kein Abschreibfehler mehr, "
                f"sondern eine andere Rezeptur (Grenze {AUSGLEICH_GRENZE_KG:.0f} kg). "
                "Ein Mensch muss entscheiden, welche Zeile falsch ist."
            )
            freigegeben = False
        elif art is Ausgleichsart.AUSGLEICH:
            posten, ziel_posten, alt, neu, probleme = _ausgeglichene_posten(rezept, delta)
            issues.extend(probleme)
            if probleme:
                freigegeben = False
            else:
                issues.append(
                    f"Ausgeglichen über {ziel_posten}: {alt:.2f} → {neu:.2f} kg je 100 kg. "
                    "Als Prüfvermerk hinterlegt."
                )
        elif art is Ausgleichsart.ANTEILIG:
            faktor = faktor * 100.0 / summe
            issues.append(
                f"Anteilig skaliert (×{100.0 / summe:.4f}) — jeder Anteil ändert sich, "
                "auch Wirkstoffe und Kalk."
            )
        else:
            issues.append(
                f"Verbatim gerechnet: es gehen {_runde(summe * faktor):.2f} kg in den "
                f"Mischer, nicht {ziel_kg:.2f} kg."
            )

    zeilen = [
        Mischzeile(artikel_id=p.artikel_id, name=p.name, kg=_runde(p.kg_je_100 * faktor))
        for p in posten
        if p.kg_je_100 > 0
    ]
    ist = _runde(sum(z.kg for z in zeilen))

    return Mischauftrag(
        rezept_key=rezept.key,
        rezept_name=rezept.name,
        ziel_kg=_runde(ziel_kg),
        ausgleich=art,
        ausgleich_posten=ziel_posten,
        normiert=art is Ausgleichsart.ANTEILIG,
        zeilen=zeilen,
        ist_einwaage_kg=ist,
        summe_je_100=summe,
        abweichung_je_100=delta,
        freigegeben=freigegeben,
        issues=issues,
    )
