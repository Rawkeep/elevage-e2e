"""Die drei Futter-Rezepturen — verbatim von den Betriebsblättern.

Die Blätter führen drei Spalten (100/500/1000 kg); die 500er- und 1000er-
Spalte sind exakt das Fünf- und Zehnfache der 100er. Gespeichert wird
deshalb nur die 100-kg-Basis, hochgerechnet wird in `mischung.py`.

**Wichtig:** Die Spalten summieren sich nicht auf ihre Überschrift
(Ponte: 106,7 statt 100 kg). Das bleibt hier stehen, wie es auf dem Blatt
steht — gemeldet wird es beim Mischauftrag, nicht still korrigiert.

Der Artikelstamm gibt jedem Rohstoff EINE Nummer. Das Blatt schreibt
denselben Binder als ALFABIND und AFABIND; ohne Stamm zählt die
Lagerreichweite zweimal getrennt.
"""

from __future__ import annotations

from elevage.models import Posten, Rezept, Tierart

# --- Tuning -------------------------------------------------------------
SUMMEN_TOLERANZ_KG = 0.05
"""Ab dieser Abweichung von 100 kg je 100 kg gilt ein Rezept als auffällig."""

AUSGLEICH_GRENZE_KG = 15.0
"""Bis hierhin wird ein Überhang ausgeglichen, darüber hält der Auftrag an.

15 kg je 100 kg ist kein Abschreibfehler mehr, sondern eine andere
Rezeptur — so etwas gleicht keine Software still aus. Die Zahl ist Tuning,
kein Naturgesetz; sie gehört dem Betrieb, nicht dem Programm."""


ARTIKELSTAMM: dict[str, str] = {
    "MAIS": "Mais",
    "SOJA_48": "Sojaschrot 48 % RP",
    "SOJA_TOURFIE": "Soja torréfié (getoastete Vollfettsoja)",
    "CONCENTRE_CHAIR": "Concentré chair",
    "CONCENTRE_PONTE": "Concentré ponte",
    "SON_CUBE": "Son cube (Weizenkleie, pelletiert)",
    "COQUILLE": "Coquille (Muschelschalen-Kalk)",
    "POISSON": "Fischmehl",
    "METHIONINE": "Méthionine",
    "LYSINE": "Lysine",
    "ALFABIND": "Alfabind (Binder; das Blatt schreibt auch AFABIND)",
    "PHOSPHATE": "Phosphat",
    "SEL": "Salz",
    "LECENAN": "Lecenan (Zusatz für die Eientwicklung)",
}

ARTIKEL_ALIAS: dict[str, str] = {
    "AFABIND": "ALFABIND",
    "SEJA_48": "SOJA_48",
    "SOJA": "SOJA_TOURFIE",
}
"""Schreibweisen des Blattes auf die Stamm-Nummer. Ein Rohstoff, eine Nummer."""


def _posten(paare: list[tuple[str, float]]) -> list[Posten]:
    zeilen = []
    for artikel_id, kg in paare:
        artikel_id = ARTIKEL_ALIAS.get(artikel_id, artikel_id)
        zeilen.append(Posten(artikel_id=artikel_id, name=ARTIKELSTAMM[artikel_id], kg_je_100=kg))
    return zeilen


REZEPT_DEMARRAGE = Rezept(
    key="DEMARRAGE_0_8",
    name="Démarrage Poussin 0 bis 8 Wochen",
    tierart=Tierart.LEGEHENNE,
    von_woche=1,
    bis_woche=8,
    posten=_posten(
        [
            ("MAIS", 60.5),
            ("SOJA_48", 10.0),
            ("SOJA", 12.0),
            ("CONCENTRE_CHAIR", 10.0),
            ("SON_CUBE", 5.0),
            ("COQUILLE", 2.0),
            ("METHIONINE", 0.5),
            ("LYSINE", 0.5),
            ("AFABIND", 0.2),
            ("PHOSPHATE", 0.2),
            ("SEL", 0.2),
        ]
    ),
    quelle='Betriebsblatt "GOLIATH" (handschriftlich)',
)

REZEPT_POULETTE = Rezept(
    key="POULETTE_8_21",
    name="Poulette 8 bis 21 Wochen",
    tierart=Tierart.LEGEHENNE,
    von_woche=9,
    bis_woche=21,
    posten=_posten(
        [
            ("MAIS", 46.5),
            ("SOJA_48", 4.0),
            ("SOJA_TOURFIE", 7.5),
            ("CONCENTRE_CHAIR", 5.0),
            ("SON_CUBE", 31.0),
            ("COQUILLE", 2.5),
            ("POISSON", 3.0),
            ("METHIONINE", 0.5),
            ("LYSINE", 0.5),
            ("ALFABIND", 0.2),
            ("PHOSPHATE", 0.2),
            ("SEL", 0.2),
        ]
    ),
    quelle='Betriebsblatt "PONDEUSE" (handschriftlich)',
)

REZEPT_PONTE = Rezept(
    key="PONTE_AB_21",
    name="Ponte ab 21 Wochen",
    tierart=Tierart.LEGEHENNE,
    von_woche=22,
    bis_woche=None,
    posten=_posten(
        [
            ("MAIS", 50.0),
            ("SOJA_TOURFIE", 14.0),
            ("CONCENTRE_PONTE", 5.0),
            ("SON_CUBE", 19.0),
            ("POISSON", 6.0),
            ("COQUILLE", 8.0),
            ("METHIONINE", 0.1),
            ("LYSINE", 0.1),
            ("ALFABIND", 0.3),
            ("LECENAN", 4.2),
        ]
    ),
    quelle='Betriebsblatt "PONTE" (handschriftlich)',
)

REZEPTE: list[Rezept] = [REZEPT_DEMARRAGE, REZEPT_POULETTE, REZEPT_PONTE]

PHASEN_UEBERLAPPUNG = (
    "Die Blätter überlappen an den Rändern (0-8 und 8-21, 8-21 und ab 21). "
    "Hier gilt: Démarrage bis Woche 8, Poulette ab Woche 9, Ponte ab Woche 22."
)

KEIN_MASTFUTTER = (
    "Für Masthühner liegt kein Futterblatt vor — nur das Prophylaxe-Programm. "
    "Der Taktgeber plant für diese Linie deshalb keine Mischung."
)


AUSGLEICHSPOSTEN: dict[str, str] = {
    "DEMARRAGE_0_8": "MAIS",
    "POULETTE_8_21": "MAIS",
    "PONTE_AB_21": "MAIS",
}
"""Woraus der Überhang genommen wird — der Energieträger, nicht die Wirkstoffe.

Mais ist der Füller: Kalk, Aminosäuren und Konzentrat stehen für eine
Funktion, ihre Menge ist die Aussage des Rezepts. Wer den Überhang
gleichmäßig über alle Posten zieht, senkt auch Methionin und Muschelkalk —
das ändert die Rezeptur, statt einen Rechenfehler zu glätten. Deshalb ist
der Ausgleich über einen benannten Posten der Vorgabeweg und `ANTEILIG`
nur die Alternative auf Ansage."""


def ausgleichsposten(rezept: Rezept) -> str:
    """Der benannte Posten — sonst der größte, weil er die Rundung am besten trägt."""
    gewaehlt = AUSGLEICHSPOSTEN.get(rezept.key)
    if gewaehlt and any(p.artikel_id == gewaehlt for p in rezept.posten):
        return gewaehlt
    return max(rezept.posten, key=lambda p: p.kg_je_100).artikel_id


def rezept_fuer(tierart: Tierart, alter_wochen: int) -> Rezept | None:
    """Welches Rezept gilt in dieser Lebenswoche? Deterministisch, keine Uhr."""
    if tierart is not Tierart.LEGEHENNE:
        return None
    for r in REZEPTE:
        if alter_wochen < r.von_woche:
            continue
        if r.bis_woche is None or alter_wochen <= r.bis_woche:
            return r
    return None


def rezept_nach_key(key: str) -> Rezept:
    for r in REZEPTE:
        if r.key == key:
            return r
    raise KeyError(f"Unbekanntes Rezept: {key}")
