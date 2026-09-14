"""Was der NB-Kasten der Blätter verlangt: Notfallschema und Futterwechsel.

Zwei Dinge, die im Tagesgeschäft untergehen, weil sie nicht im Tagesraster
stehen, sondern an einem Ereignis hängen:

* **Gumboro-Notfallschema** — wird ein Ausbruch festgestellt, laufen vier
  Tage Desinfektion plus Antikokzidium und danach der Leberschutz, der die
  Futteraufnahme wieder anschiebt.
* **Leberschutz beim Futterwechsel** — das Junghennen-Blatt verlangt ihn bei
  *jedem* Futterwechsel. Die Wechseltage stehen nicht im Programm, sie
  ergeben sich aus den Rezepten.

**Die beiden Blätter widersprechen sich in der Dosis** (0,5 g/l für
Masthühner, 1 g/l für Junghennen). Beide Zahlen bleiben stehen, der
Unterschied wird gemeldet.
"""

from __future__ import annotations

from datetime import date

from elevage.einstellung import VORGABE_DOSIS
from elevage.models import (
    Ereignis,
    EreignisArt,
    Herde,
    Kategorie,
    Schritt,
    Tierart,
    Verabreichung,
)
from elevage.rezepte import REZEPTE

SCHEMA_TAGE = 4
"""Desinfektion + Antikokzidium laufen vier Tage — beide Blätter sagen das."""

ERHOLUNG_TAGE = 4
"""Danach der Leberschutz, um die Futteraufnahme wieder anzuschieben."""

DOSIS_JE_LITER = VORGABE_DOSIS
"""Verbatim aus den beiden NB-Kästen — die Blätter nennen zwei Dosen."""

DOSIS_WIDERSPRUCH = (
    "Die Blätter nennen zwei Dosen für dasselbe Mittel: 0,5 g/l (Masthuhn) "
    "und 1 g/l (Junghenne). Beide stehen so im NB-Kasten; hier gilt die des "
    "eigenen Blattes, solange der Betrieb nichts anderes eingestellt hat."
)

DOSIS_VOM_BETRIEB = (
    "Die Desinfektionsdosis ist eine Einstellung dieses Betriebs, nicht der Wert des Blattes."
)

DESINFEKTION = ["VIRKON", "VIRUNET"]
ANTIKOKZIDIUM = ["VETACOX", "AMPROLIUM", "TRISULMYCINE FORTE", "ANTICOX"]
LEBERSCHUTZ = ["VIGOSINE", "HEPARENOL", "HEPATURYL", "NEPHRYL", "HEPASOL"]

WECHSEL_FENSTER = (-1, 2)
"""Leberschutz von j-1 bis j+2 um den Futterwechsel."""


def lebenstag(herde: Herde, tag: date) -> int:
    """Ein Datum in den Lebenstag der Herde übersetzen (J1 = Einstalltag)."""
    return (tag - herde.einstalldatum).days + 1


def schritte_fuer_vorfall(
    ereignis: Ereignis,
    herde: Herde,
    dosis: str | None = None,
    *,
    vom_betrieb: bool = False,
) -> list[Schritt]:
    """Das Notfallschema als ganz normale Schritte — gleiche Ampel, gleiche Quittung.

    `dosis` überschreibt den Blattwert (Einstellung des Betriebs). Woher die
    Zahl kommt, steht danach im Befund — eine stillschweigend geänderte Dosis
    wäre die schlechtere Überraschung.
    """
    if ereignis.art is not EreignisArt.GUMBORO:
        return []

    tag = lebenstag(herde, ereignis.festgestellt_am)
    gewaehlt = dosis or DOSIS_JE_LITER[herde.tierart]
    kennung = ereignis.ereignis_id

    return [
        Schritt(
            key=f"NOTFALL_{kennung}_DESINFEKTION",
            tierart=herde.tierart,
            von_tag=tag,
            bis_tag=tag + SCHEMA_TAGE - 1,
            titel=f"Gumboro-Schema: Desinfektion {gewaehlt} + Antikokzidium 1 g/l (4 Tage)",
            titel_fr=(
                f"En cas de maladie de GUMBORO : désinfection {gewaehlt} "
                "+ anticoccidien 1 g/l sur 4 jours"
            ),
            kategorie=Kategorie.MEDIKATION,
            verabreichung=Verabreichung.TRINKWASSER,
            praeparate=[f"{' oder '.join(DESINFEKTION)} ({gewaehlt})"]
            + [f"+ {' oder '.join(ANTIKOKZIDIUM)} (1 g/l)"],
            hinweis=f"Ausgelöst durch Vorfall vom {ereignis.festgestellt_am:%d.%m.%Y}",
            hinweis_fr=f"Déclenché par l'incident du {ereignis.festgestellt_am:%d.%m.%Y}",
            quelle="NB-Kasten des Blattes",
            issues=[DOSIS_VOM_BETRIEB if vom_betrieb else DOSIS_WIDERSPRUCH],
        ),
        Schritt(
            key=f"NOTFALL_{kennung}_ERHOLUNG",
            tierart=herde.tierart,
            von_tag=tag + SCHEMA_TAGE,
            bis_tag=tag + SCHEMA_TAGE + ERHOLUNG_TAGE - 1,
            titel="Nach Gumboro: Futteraufnahme mit Leberschutz wieder anschieben",
            titel_fr=(
                "Relancer la consommation d'aliment après le passage de la "
                "GUMBORO en distribuant un protecteur hépatorénal"
            ),
            kategorie=Kategorie.VITAMINE,
            verabreichung=Verabreichung.TRINKWASSER,
            praeparate=list(LEBERSCHUTZ),
            folgt_auf=f"NOTFALL_{kennung}_DESINFEKTION",
            hinweis="Das Blatt nennt es Diuretikum bzw. hepatorenalen Schutz",
            hinweis_fr="Le programme parle de diurétique ou de protecteur hépatorénal",
            quelle="NB-Kasten des Blattes",
        ),
    ]


def wechseltage(tierart: Tierart) -> list[tuple[int, str, str]]:
    """Aus den Rezepten abgeleitet, nicht als Zahl hingeschrieben.

    Je Wechsel: Lebenstag, Name der Phase, Name im Blatt (französisch)."""
    if tierart is not Tierart.LEGEHENNE:
        return []
    return [
        (7 * (r.von_woche - 1) + 1, r.name, r.name_fr or r.name) for r in REZEPTE if r.von_woche > 1
    ]


def futterwechsel_schritte(herde: Herde) -> list[Schritt]:
    """Leberschutz bei jedem Futterwechsel — Forderung des Junghennen-Blattes."""
    vorn, hinten = WECHSEL_FENSTER
    return [
        Schritt(
            key=f"FUTTERWECHSEL_W{tag}",
            tierart=herde.tierart,
            von_tag=tag + vorn,
            bis_tag=tag + hinten,
            titel=f"Futterwechsel auf {name} — Leberschutz mitgeben",
            titel_fr=(
                f"Transition alimentaire vers {name_fr} — mettre en place un protecteur hépatorénal"
            ),
            kategorie=Kategorie.FUTTERWECHSEL,
            verabreichung=Verabreichung.TRINKWASSER,
            praeparate=list(LEBERSCHUTZ),
            hinweis="Das Blatt verlangt den Schutz bei JEDEM Futterwechsel",
            hinweis_fr="Le programme l'exige à CHAQUE transition alimentaire",
            quelle="NB-Kasten des Blattes",
        )
        for tag, name, name_fr in wechseltage(herde.tierart)
    ]
