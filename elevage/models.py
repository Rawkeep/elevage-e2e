"""Der Vertrag. Änderungen hier zuerst — alles andere zieht nach.

Python-Felder snake_case, JSON-Vertrag camelCase über den Alias-Generator
(Hausregel aus den Schwester-Repos: die I/O bleibt camelCase).
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _Basis(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Tierart(str, Enum):
    """Die beiden Linien laufen parallel im selben Betrieb."""

    MASTHUHN = "MASTHUHN"
    LEGEHENNE = "LEGEHENNE"


class Kategorie(str, Enum):
    HYGIENE = "HYGIENE"
    IMPFUNG = "IMPFUNG"
    MEDIKATION = "MEDIKATION"
    VITAMINE = "VITAMINE"
    ANTIKOKZIDIUM = "ANTIKOKZIDIUM"
    ENTWURMUNG = "ENTWURMUNG"
    EINGRIFF = "EINGRIFF"
    FUTTERWECHSEL = "FUTTERWECHSEL"


class Verabreichung(str, Enum):
    TRINKWASSER = "TRINKWASSER"
    AUGENTROPFEN = "AUGENTROPFEN"
    VERNEBELUNG = "VERNEBELUNG"
    INJEKTION = "INJEKTION"
    FLUEGELFALTE = "FLUEGELFALTE"
    SPRUEHUNG = "SPRUEHUNG"
    FUTTER = "FUTTER"
    HANDGRIFF = "HANDGRIFF"


class EreignisArt(str, Enum):
    """Was im Stall passiert ist — löst ein Schema aus, kein Urteil."""

    GUMBORO = "GUMBORO"


class Quelle(str, Enum):
    """Woher eine Zahl kommt. Steht an jeder abgeleiteten Zahl dran."""

    GEMESSEN = "GEMESSEN"
    RICHTWERT = "RICHTWERT"


class Ampel(str, Enum):
    """Vier Zustände wie in fristen.py: erledigt schlägt alles."""

    ERLEDIGT = "ERLEDIGT"
    ROT = "ROT"
    GELB = "GELB"
    GRUEN = "GRUEN"


class Schritt(_Basis):
    """Vorlage aus dem Programm — gilt für alle Herden einer Tierart.

    Vorlage und Termin sind getrennt: ein geändertes Programm darf die
    Historie einer laufenden Herde nicht rückwirkend verfälschen.
    """

    key: str
    tierart: Tierart
    von_tag: int = Field(description="Lebenstag, ab dem der Schritt fällig ist (J1 = Einstalltag)")
    bis_tag: int
    titel: str
    kategorie: Kategorie
    verabreichung: Verabreichung
    praeparate: list[str] = Field(default_factory=list, description="Alternativen, 'oder'-Liste")
    bedingt: str | None = None
    vorlauf_tage: int = 0
    folgt_auf: str | None = None
    hinweis: str | None = None
    quelle: str = "IVOGRAIN"
    issues: list[str] = Field(default_factory=list)


class Herde(_Basis):
    """Eine eingestallte Charge. Alles rechnet sich aus dem Einstalldatum."""

    tenant_id: str
    herde_id: str
    name: str
    tierart: Tierart
    einstalldatum: date
    tierzahl: int
    hoher_virusdruck: bool = False
    spaete_schlachtung: bool = False


class Quittung(_Basis):
    """Abhaken ist ein Ereignis, kein überschriebenes Feld.

    Damit gibt es beim Offline-Sync keinen Konflikt, nur zwei Einträge und
    eine sichtbare Frage. `quittung_id` macht das Nachreichen idempotent.
    """

    tenant_id: str
    herde_id: str
    schritt_key: str
    quittung_id: str
    erledigt_am: date
    durch: str = ""
    lot: str | None = None
    bemerkung: str | None = None


class Termin(_Basis):
    """Vorlage + Herde = Termin mit echtem Datum."""

    herde_id: str
    schritt_key: str
    titel: str
    kategorie: Kategorie
    verabreichung: Verabreichung
    praeparate: list[str] = Field(default_factory=list)
    faellig_von: date
    faellig_bis: date
    tage_bis: int = Field(description="Tage bis faellig_von; negativ = überfällig")
    ampel: Ampel
    bedingt: str | None = None
    hinweis: str | None = None
    erledigt_am: date | None = None
    lot: str | None = None


class Dauerregel(_Basis):
    """Wiederkehrende Aufgabe der Legeperiode (NB-Kasten des Blattes)."""

    key: str
    titel: str
    kategorie: Kategorie
    verabreichung: Verabreichung
    praeparate: list[str] = Field(default_factory=list)
    intervall_tage: int
    hinweis: str | None = None


class Ereignis(_Basis):
    """Ein festgestellter Vorfall. Wie die Quittung ein Ereignis, kein Feld."""

    tenant_id: str
    herde_id: str
    ereignis_id: str
    art: EreignisArt
    festgestellt_am: date
    bemerkung: str | None = None


class KurvePunkt(_Basis):
    woche: int
    gramm_je_tier_tag: float
    quelle: Quelle
    basis: str | None = Field(
        default=None, description="Woraus die Zahl stammt (z. B. 'Mischung M-3, 500 kg')"
    )


class Verzehrkurve(_Basis):
    """Was ein Tier je Lebenswoche am Tag frisst.

    Ohne diese Kurve gibt es keine Reichweite und keinen Bestellzeitpunkt.
    Jeder Punkt trägt seine Quelle — gemessen aus dem eigenen Mischprotokoll
    oder Richtwert. Eine Prognose, die auf Richtwerten steht, sagt das.
    """

    tierart: Tierart
    punkte: list[KurvePunkt] = Field(default_factory=list)

    def fuer_woche(self, woche: int) -> KurvePunkt | None:
        """Der Punkt dieser Woche — sonst der letzte davor (Kurve hält)."""
        treffer: KurvePunkt | None = None
        for p in sorted(self.punkte, key=lambda x: x.woche):
            if p.woche <= woche:
                treffer = p
        return treffer


class Futterprognose(_Basis):
    """Reichweite und Bestelltag — oder eine ehrliche Lücke."""

    herde_id: str
    stichtag: date
    woche: int
    gramm_je_tier_tag: float | None = None
    quelle: Quelle | None = None
    bedarf_je_tag_kg: float | None = None
    bedarf_bis_horizont_kg: float | None = None
    horizont_tage: int = 0
    vorrat_kg: float | None = None
    reicht_bis: date | None = None
    bestellen_ab: date | None = None
    issues: list[str] = Field(default_factory=list)


class Posten(_Basis):
    artikel_id: str
    name: str
    kg_je_100: float


class Rezept(_Basis):
    key: str
    name: str
    tierart: Tierart
    von_woche: int
    bis_woche: int | None = None
    posten: list[Posten]
    quelle: str = "Betriebsblatt (handschriftlich)"

    @property
    def summe_je_100(self) -> float:
        return round(sum(p.kg_je_100 for p in self.posten), 4)


class Mischzeile(_Basis):
    artikel_id: str
    name: str
    kg: float


class Mischauftrag(_Basis):
    rezept_key: str
    rezept_name: str
    ziel_kg: float
    normiert: bool
    zeilen: list[Mischzeile]
    ist_einwaage_kg: float = Field(description="Was tatsächlich in den Mischer geht")
    summe_je_100: float
    abweichung_je_100: float
    freigegeben: bool
    issues: list[str] = Field(default_factory=list)


class Tagesbild(_Basis):
    """Ein Stichtag, eine Herde, das ganze Bild. Der Stichtag kommt herein."""

    stichtag: date
    herde: Herde
    alter_tage: int
    alter_wochen: int
    phase: Rezept | None = None
    ueberfaellig: list[Termin] = Field(default_factory=list)
    heute: list[Termin] = Field(default_factory=list)
    demnaechst: list[Termin] = Field(default_factory=list)
    bestellen: list[Termin] = Field(default_factory=list)
    erledigt: list[Termin] = Field(default_factory=list)
    futter: Futterprognose | None = None
    vorfaelle: list[Ereignis] = Field(default_factory=list)
    ampel: Ampel = Ampel.GRUEN
    issues: list[str] = Field(default_factory=list)
