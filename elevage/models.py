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
    ANTI_STRESS = "ANTI_STRESS"
    LEBERSCHUTZ = "LEBERSCHUTZ"
    # PAUSE = ausdrücklich nichts geben (VETO-NEGOCES: „EAU SIMPLE").
    # Kein Versäumnis, sondern eine Anweisung — deshalb eine eigene
    # Kategorie und kein fehlender Schritt. Sie erzeugt keinen Posten zum
    # Abhaken, sondern eine Zeile im Stand.
    PAUSE = "PAUSE"


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


class Herkunft(str, Enum):
    """Steht an jedem Rezeptposten: Blattwert oder Betriebswert."""

    BLATT = "BLATT"
    BETRIEB = "BETRIEB"


class Ausgleichsart(str, Enum):
    """Wie mit einem Rezept umgegangen wird, das nicht auf 100 kg aufgeht."""

    VERBATIM = "VERBATIM"
    AUSGLEICH = "AUSGLEICH"
    ANTEILIG = "ANTEILIG"


class Quelle(str, Enum):
    """Woher eine Zahl kommt. Steht an jeder abgeleiteten Zahl dran."""

    GEMESSEN = "GEMESSEN"
    RICHTWERT = "RICHTWERT"


class Erzeugnis(str, Enum):
    """Woran eine Wartezeit hängt. Das Blatt nennt beides nicht — der
    Beipackzettel des Präparats schon."""

    EIER = "EIER"
    FLEISCH = "FLEISCH"


class Ampel(str, Enum):
    """Vier Zustände wie in fristen.py: erledigt schlägt alles."""

    ERLEDIGT = "ERLEDIGT"
    ROT = "ROT"
    GELB = "GELB"
    GRUEN = "GRUEN"


class Satz(_Basis):
    """Ein Satz in beiden Sprachen — Deutsch im Code, Französisch daneben."""

    text: str
    text_fr: str | None = None


def satz(de: str, fr: str) -> Satz:
    """Kurzform für einen Merksatz des Blattes."""
    return Satz(text=de, text_fr=fr)


class Befund(Satz):
    """Ein Satz, der auf einen Widerspruch zeigt.

    Eigener Name, weil er etwas anderes meint als ein Merksatz: hier
    stimmt etwas nicht, und jemand muss nachsehen.

    Früher war das ein blanker String, und die französische Ansicht zeigte
    deutsche Sätze — bei einem Werkzeug, dessen Blätter französisch sind
    und dessen Stall französisch spricht, ist das der falsche Weg herum.

    Ein Wörterbuch hilft hier nicht: die meisten Befunde tragen Zahlen
    („46,50 → 45,40 kg“), und ein Musterabgleich auf zusammengesetzte
    Sätze wäre genau die Sorte Magie, die dieses Haus vermeidet. Also
    schreibt die Stelle, die den Befund erzeugt, beide Fassungen — sie ist
    die einzige, die weiß, was sie sagen will.
    """


def befund(de: str, fr: str) -> Befund:
    """Kurzform, damit die erzeugende Stelle lesbar bleibt."""
    return Befund(text=de, text_fr=fr)


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
    titel_fr: str | None = Field(
        default=None,
        description="Wortlaut des Blattes — die Blätter SIND französisch, "
        "der deutsche Titel ist die Übersetzung",
    )
    hinweis_fr: str | None = None
    dosis_je_liter: str | None = Field(
        default=None,
        description="Dosierung wörtlich vom Blatt, z. B. '1 g/l' oder '2 ml/l'",
    )
    quelle: str = "IVOGRAIN"
    issues: list[Befund] = Field(default_factory=list)


class Rolle(str, Enum):
    """Wer was darf. LESER sieht, STALL hakt ab, LEITUNG ändert Rezepte."""

    LESER = "LESER"
    STALL = "STALL"
    LEITUNG = "LEITUNG"


class Benutzer(_Basis):
    tenant_id: str
    benutzer_id: str = Field(description="Anmeldename, betriebsübergreifend eindeutig")
    name: str
    rolle: Rolle = Rolle.STALL
    aktiv: bool = True
    angelegt_am: date


class Sitzung(_Basis):
    tenant_id: str
    benutzer_id: str
    rolle: Rolle
    name: str
    laeuft_ab_am: date


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
    programm_id: str | None = Field(
        default=None,
        description="Welches Prophylaxe-Programm gilt; None = Vorgabe der Tierart",
    )


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
    praeparat: str | None = Field(
        default=None, description="Welches der Alternativpräparate gegeben wurde"
    )
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
    titel_fr: str | None = None
    hinweis_fr: str | None = None
    dosis_je_liter: str | None = None
    quelle: str = ""
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
    titel_fr: str | None = None
    hinweis_fr: str | None = None
    dosis_je_liter: str | None = None
    ab_tag: int | None = Field(
        default=None,
        description="Lebenstag, ab dem die Regel greift; None = ab Legephase",
    )


OFFENES_ENDE = 10_000
"""`bis_tag` für Schritte ohne Enddatum („J128 à la Réforme").

Eine Zahl, kein None: die ganze Planrechnung vergleicht Lebenstage, und
ein None an dieser Stelle hieße überall eine Sonderbehandlung. 10.000 Tage
sind 27 Jahre — jenseits jeder Legehenne."""


class Programm(_Basis):
    """Ein Prophylaxe-Blatt als Ganzes — Schritte, Dauerregeln, Merksätze.

    Zwei Tierärzte, zwei Blätter, dieselbe Tierart: die Wahl gehört
    deshalb an die Herde, nicht an die Tierart. Zusammenlegen wäre falsch —
    die Blätter widersprechen sich an fast jedem Datum, und welches gilt,
    entscheidet ein Mensch.
    """

    programm_id: str
    titel: str
    titel_fr: str | None = None
    tierart: Tierart
    quelle: str = Field(description="Wer das Blatt herausgibt")
    herausgeber: str | None = Field(default=None, description="Praxis, Person, Kontakt")
    schritte: list[Schritt] = Field(default_factory=list)
    dauerregeln: list[Dauerregel] = Field(default_factory=list)
    hinweise: list[Satz] = Field(
        default_factory=list, description="Merksätze des Blattes — keine Termine"
    )
    vorgabe: bool = Field(default=False, description="Vorgabe für diese Tierart")


class Programmunterschied(_Basis):
    """Eine Zeile der Gegenüberstellung zweier Blätter."""

    thema: str
    links: str | None = None
    rechts: str | None = None
    gleich: bool = False


class Programmvergleich(_Basis):
    """Was zwei Blätter für dieselbe Tierart verschieden sagen.

    Deterministisch gerechnet, nicht formuliert: gruppiert wird über die
    Kategorie, verglichen werden die Tagesfenster. Das Urteil, welches
    Blatt gilt, trifft der Betrieb.
    """

    tierart: Tierart
    links_id: str
    rechts_id: str
    links_titel: str
    rechts_titel: str
    zeilen: list[Programmunterschied] = Field(default_factory=list)
    nur_links: list[str] = Field(default_factory=list)
    nur_rechts: list[str] = Field(default_factory=list)
    issues: list[Befund] = Field(default_factory=list)


class Tierarzt(_Basis):
    """Der Tierarzt des Betriebs — je Mandant einer.

    Steht auf jedem Blatt („Contactez votre vétérinaire dès que vous
    constatez un changement de comportement"), gehört aber nicht ins
    Programm: der Betrieb wechselt den Arzt, nicht das Blatt.
    """

    tenant_id: str
    name: str
    praxis: str | None = None
    telefon: str | None = None
    email: str | None = None
    hinweis: str | None = None


class Abgangsgrund(str, Enum):
    """Warum Tiere den Bestand verlassen. Verendet ist nicht verkauft."""

    VERENDET = "VERENDET"
    GEKEULT = "GEKEULT"
    VERKAUFT = "VERKAUFT"
    SONSTIGES = "SONSTIGES"


class Bestandsbewegung(_Basis):
    """Ein Zu- oder Abgang an einem Tag. Wie die Quittung ein Ereignis."""

    tenant_id: str
    herde_id: str
    bewegung_id: str
    am: date
    abgang: int = Field(default=0, ge=0)
    zugang: int = Field(default=0, ge=0)
    grund: Abgangsgrund = Abgangsgrund.VERENDET
    bemerkung: str | None = None


class Bestand(_Basis):
    """Wie viele Tiere an einem Stichtag im Stall stehen."""

    herde_id: str
    stichtag: date
    eingestallt: int
    abgang_gesamt: int
    zugang_gesamt: int
    tierzahl: int
    verluste_prozent: float
    issues: list[Befund] = Field(default_factory=list)


class Praeparat(_Basis):
    """Ein Mittel und seine Wartezeit — die Zahl steht auf der Packung.

    `None` heißt **unbekannt**, nicht `0`. Der Unterschied ist der ganze
    Zweck dieser Tabelle: eine fehlende Wartezeit muss auffallen, nicht
    stillschweigend zu „darf verkauft werden" werden.
    """

    tenant_id: str
    praeparat_id: str
    name: str
    wartezeit_eier_tage: int | None = Field(default=None, ge=0)
    wartezeit_fleisch_tage: int | None = Field(default=None, ge=0)
    quelle: str | None = Field(default=None, description="Woher die Zahl stammt")
    hinweis: str | None = None


class Sperrfenster(_Basis):
    """Ab wann wieder vermarktet werden darf. Ergebnis, keine Eingabe."""

    erzeugnis: Erzeugnis
    herde_id: str
    praeparat: str
    schritt_key: str
    letzte_gabe: date
    wartezeit_tage: int
    freigabe_ab: date
    laeuft_noch: bool


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
    issues: list[Befund] = Field(default_factory=list)


class Posten(_Basis):
    artikel_id: str
    name: str
    kg_je_100: float
    herkunft: Herkunft = Herkunft.BLATT
    blatt_kg_je_100: float | None = Field(
        default=None, description="Der Wert des Blattes, wenn der Betrieb ihn geändert hat"
    )


class Rezept(_Basis):
    key: str
    name: str
    name_fr: str | None = None
    tierart: Tierart
    von_woche: int
    bis_woche: int | None = None
    posten: list[Posten]
    quelle: str = "Betriebsblatt (handschriftlich)"

    @property
    def summe_je_100(self) -> float:
        return round(sum(p.kg_je_100 for p in self.posten), 4)


class Rezeptanpassung(_Basis):
    """Ein vom Betrieb geänderter Rezeptposten. 0 kg heißt: Posten entfällt."""

    tenant_id: str
    rezept_key: str
    artikel_id: str
    kg_je_100: float = Field(ge=0)
    grund: str | None = None
    geaendert_am: date


class Pruefvermerk(_Basis):
    """Ein Punkt, den ein Mensch später prüfen soll. Verschwindet nicht von selbst."""

    tenant_id: str
    vermerk_id: str
    betrifft: str
    text: str
    text_fr: str | None = None
    angelegt_am: date
    erledigt_am: date | None = None
    erledigt_durch: str | None = None


class Mischzeile(_Basis):
    artikel_id: str
    name: str
    kg: float


class Mischauftrag(_Basis):
    rezept_key: str
    rezept_name: str
    ziel_kg: float
    ausgleich: Ausgleichsart
    ausgleich_posten: str | None = None
    normiert: bool
    zeilen: list[Mischzeile]
    ist_einwaage_kg: float = Field(description="Was tatsächlich in den Mischer geht")
    summe_je_100: float
    abweichung_je_100: float
    freigegeben: bool
    issues: list[Befund] = Field(default_factory=list)


class Tagesbild(_Basis):
    """Ein Stichtag, eine Herde, das ganze Bild. Der Stichtag kommt herein."""

    stichtag: date
    herde: Herde
    alter_tage: int
    alter_wochen: int
    programm_id: str = ""
    programm_titel: str = ""
    programm_titel_fr: str | None = None
    phase: Rezept | None = None
    ueberfaellig: list[Termin] = Field(default_factory=list)
    heute: list[Termin] = Field(default_factory=list)
    demnaechst: list[Termin] = Field(default_factory=list)
    bestellen: list[Termin] = Field(default_factory=list)
    erledigt: list[Termin] = Field(default_factory=list)
    futter: Futterprognose | None = None
    ruhe: list[Termin] = Field(
        default_factory=list,
        description="Laufende Pausen — einfaches Wasser, nichts zum Abhaken",
    )
    vorfaelle: list[Ereignis] = Field(default_factory=list)
    vermerke: list[Pruefvermerk] = Field(default_factory=list)
    sperren: list[Sperrfenster] = Field(default_factory=list)
    tierarzt: Tierarzt | None = None
    bestand: Bestand | None = None
    ampel: Ampel = Ampel.GRUEN
    issues: list[Befund] = Field(default_factory=list)
