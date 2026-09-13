"""Rezeptmengen sind anpassbar — je Betrieb, ohne das Blatt zu verlieren.

Das Blatt bleibt im Code stehen und wird nie überschrieben. Was der Betrieb
ändert, liegt als Anpassung daneben; das wirksame Rezept entsteht erst beim
Zusammenlegen. Jeder Posten trägt danach seine Herkunft, und wo der Betrieb
eingegriffen hat, steht der Blattwert weiter daneben.
"""

from __future__ import annotations

from elevage.models import Herkunft, Posten, Rezept, Rezeptanpassung
from elevage.rezepte import ARTIKEL_ALIAS, ARTIKELSTAMM


def artikel_name(artikel_id: str) -> str:
    """Unbekannte Nummern werden nicht erfunden, sondern als solche gezeigt."""
    return ARTIKELSTAMM.get(artikel_id, f"Unbekannter Artikel {artikel_id}")


def normiere_artikel(artikel_id: str) -> str:
    """Schreibweisen des Blattes auf die Stamm-Nummer — ein Rohstoff, eine Nummer."""
    return ARTIKEL_ALIAS.get(artikel_id, artikel_id)


def wirksames_rezept(basis: Rezept, anpassungen: list[Rezeptanpassung]) -> Rezept:
    """Blatt + Betriebsanpassungen = das Rezept, nach dem wirklich gemischt wird."""
    passend = {normiere_artikel(a.artikel_id): a for a in anpassungen if a.rezept_key == basis.key}
    posten: list[Posten] = []
    for p in basis.posten:
        anpassung = passend.pop(p.artikel_id, None)
        if anpassung is None:
            posten.append(p)
            continue
        posten.append(
            p.model_copy(
                update={
                    "kg_je_100": anpassung.kg_je_100,
                    "herkunft": Herkunft.BETRIEB,
                    "blatt_kg_je_100": p.kg_je_100,
                }
            )
        )
    # Posten, die das Blatt gar nicht kennt — der Betrieb hat sie ergänzt.
    for artikel_id, anpassung in passend.items():
        posten.append(
            Posten(
                artikel_id=artikel_id,
                name=artikel_name(artikel_id),
                kg_je_100=anpassung.kg_je_100,
                herkunft=Herkunft.BETRIEB,
                blatt_kg_je_100=None,
            )
        )
    return basis.model_copy(update={"posten": posten})


def geaendert(rezept: Rezept) -> list[Posten]:
    """Welche Posten vom Blatt abweichen — für Anzeige und Prüfvermerk."""
    return [p for p in rezept.posten if p.herkunft is Herkunft.BETRIEB]
