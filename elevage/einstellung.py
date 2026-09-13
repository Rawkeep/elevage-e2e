"""Einstellungen je Betrieb: was vom Blatt abweichen darf, weicht hier ab.

Ein flacher Schlüssel-Wert-Speicher statt einer Spalte je Wunsch. Jede
Einstellung hat hier ihren Vorgabewert aus den Blättern — solange nichts
gesetzt ist, rechnet das Programm exakt wie die Vorlage.
"""

from __future__ import annotations

from elevage.models import Ausgleichsart, Tierart

AUSGLEICHSART = "mischung.ausgleich"
NOTFALL_DOSIS = "notfall.dosis"

VORGABE_DOSIS: dict[Tierart, str] = {
    Tierart.MASTHUHN: "0,5 g/l",
    Tierart.LEGEHENNE: "1 g/l",
}
"""Verbatim aus den beiden NB-Kästen. Die Blätter widersprechen sich hier."""


def dosis_schluessel(tierart: Tierart) -> str:
    return f"{NOTFALL_DOSIS}.{tierart.value}"


def notfall_dosis(werte: dict[str, str], tierart: Tierart) -> tuple[str, bool]:
    """Die Dosis und ob sie vom Betrieb stammt (True) oder vom Blatt (False)."""
    gesetzt = werte.get(dosis_schluessel(tierart))
    if gesetzt:
        return gesetzt, True
    return VORGABE_DOSIS[tierart], False


def ausgleichsart(werte: dict[str, str]) -> Ausgleichsart:
    """Wie mit einem Rezept umgegangen wird, das nicht aufgeht."""
    roh = werte.get(AUSGLEICHSART)
    if roh is None:
        return Ausgleichsart.AUSGLEICH
    try:
        return Ausgleichsart(roh)
    except ValueError:
        return Ausgleichsart.AUSGLEICH


BEKANNT: dict[str, str] = {
    AUSGLEICHSART: "VERBATIM | AUSGLEICH (Vorgabe) | ANTEILIG",
    f"{NOTFALL_DOSIS}.MASTHUHN": "Desinfektionsdosis im Gumboro-Schema, Vorgabe 0,5 g/l",
    f"{NOTFALL_DOSIS}.LEGEHENNE": "Desinfektionsdosis im Gumboro-Schema, Vorgabe 1 g/l",
}
"""Was gesetzt werden kann. Unbekannte Schlüssel werden abgewiesen, nicht
stillschweigend abgelegt — sonst sammelt sich dort Müll, den niemand liest."""
