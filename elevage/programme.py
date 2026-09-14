"""Die beiden Prophylaxe-Programme als Daten — verbatim von den Betriebsblättern.

Quelle: IVOGRAIN, "Programme de prophylaxie - Poulets de chair" und
"Programme de prophylaxie des poulettes futures pondeuses".

Grundsatz wie in den Schwester-Repos: **verbatim übernehmen, Widersprüche
melden statt still glattziehen**. Wo das Blatt sich selbst widerspricht
(Woche vs. Tagesangabe, doppelte Zählung), steht das im `issues`-Feld des
Schritts und wandert bis ins Tagesbild durch.

Tag-Rechnung: J1 = Einstalltag. Tag 0 ist der Tag davor (Vorbereitung).
Woche w umfasst die Tage 7*(w-1)+1 bis 7*w.
"""

from __future__ import annotations

from elevage.models import (
    OFFENES_ENDE,
    Dauerregel,
    Kategorie,
    Programm,
    Schritt,
    Tierart,
    Verabreichung,
)

# --- Tuning, keine Magic Numbers im Code --------------------------------
VORLAUF_IMPFSTOFF_TAGE = 3
"""Impfstoff muss so viele Tage vor dem Termin bestellt/geholt sein."""

VORLAUF_MEDIKAMENT_TAGE = 2

IVOGRAIN = "IVOGRAIN"
VETO = "VETO-NEGOCES"
"""Die beiden Herausgeber. Steht an jedem Schritt, damit im Tagesbild
sichtbar bleibt, wessen Blatt gerade gilt."""


def woche(w: int) -> tuple[int, int]:
    """Woche w als Lebenstag-Spanne. Woche 1 = Tag 1..7."""
    return (7 * (w - 1) + 1, 7 * w)


_W5 = woche(5)
_W6 = woche(6)
_W7 = woche(7)
_W9 = woche(9)
_W10 = woche(10)
_W11 = woche(11)
_W13 = woche(13)
_W16 = woche(16)

LEGEPHASE_AB_WOCHE = 21
"""Ab hier läuft das Dauerprogramm der Legeperiode (NB-Kasten des Blattes)."""


PROGRAMM_MASTHUHN: list[Schritt] = [
    Schritt(
        key="CHAIR_J0_DESINFEKTION",
        tierart=Tierart.MASTHUHN,
        von_tag=0,
        bis_tag=2,
        titel="Einstreu und Raum desinfizieren",
        kategorie=Kategorie.HYGIENE,
        verabreichung=Verabreichung.SPRUEHUNG,
        praeparate=["Kupfersulfat", "VIRUNET", "AQUAVIC 3%", "IODAVIC"],
        hinweis="0,5 g/l — vor dem Einstallen beginnen, 2 Tage in Anwesenheit der Küken",
    ),
    Schritt(
        key="CHAIR_J1_ND_IB",
        tierart=Tierart.MASTHUHN,
        von_tag=1,
        bis_tag=1,
        titel="Newcastle + Bronchite H120 + IB-Variante",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.AUGENTROPFEN,
        praeparate=[
            "AVINEW oder HB1 (Newcastle)",
            "Bronchite infectieuse H120",
            "CEVAC IBIRD oder GALLIVAC IB 88 oder AVI IB VAR (IB-Variante)",
        ],
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        hinweis="Augentropfen oder Vernebelung, im Brüter",
    ),
    Schritt(
        key="CHAIR_J1_START",
        tierart=Tierart.MASTHUHN,
        von_tag=1,
        bis_tag=1,
        titel="Starttrunk: Zuckerwasser bzw. Vitamin C",
        kategorie=Kategorie.VITAMINE,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["Zuckerwasser 50 g/l", "Vitamin C 0,5 g/l", "VIGOSINE", "HEPASOL"],
    ),
    Schritt(
        key="CHAIR_J2_ANTIBIOTIKUM",
        tierart=Tierart.MASTHUHN,
        von_tag=2,
        bis_tag=6,
        titel="Antibiotikum + Vitamine",
        kategorie=Kategorie.MEDIKATION,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=[
            "COVIT",
            "TETRACOLIVIT",
            "COLITERRAVET",
            "VIGAL 2X",
            "PANTERYL",
            "SUPER LAYER",
        ],
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
    ),
    Schritt(
        key="CHAIR_J8_GUMBORO_1",
        tierart=Tierart.MASTHUHN,
        von_tag=8,
        bis_tag=8,
        titel="1. Gumboro-Impfung (intermediärer Stamm)",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["CEVAC GUMBO L", "AVI IBD INTER", "HIPRAGUMBORO CH80", "BUR706"],
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
    ),
    Schritt(
        key="CHAIR_J10_ND_RAPPEL",
        tierart=Tierart.MASTHUHN,
        von_tag=10,
        bis_tag=10,
        titel="Newcastle-Auffrischung + Bronchite H120",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["AVINEW", "HB1", "CLONE", "+ Bronchite H120"],
        folgt_auf="CHAIR_J1_ND_IB",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
    ),
    Schritt(
        key="CHAIR_J13_GUMBORO_2",
        tierart=Tierart.MASTHUHN,
        von_tag=13,
        bis_tag=13,
        titel="2. Gumboro-Impfung (intermediate plus)",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["CEVAC IBDL", "AVI IBD PLUS", "HIPRAGUMBORO GM97", "NOBILIS 228E"],
        folgt_auf="CHAIR_J8_GUMBORO_1",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
    ),
    Schritt(
        key="CHAIR_J18_GUMBORO_3",
        tierart=Tierart.MASTHUHN,
        von_tag=18,
        bis_tag=18,
        titel="3. Gumboro-Impfung (intermediate plus)",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["CEVAC IBDL", "AVI IBD PLUS", "HIPRAGUMBORO GM97", "NOBILIS 228E"],
        bedingt="hoher_virusdruck",
        folgt_auf="CHAIR_J13_GUMBORO_2",
        hinweis="Nur für Zonen mit starkem Virusdruck",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
    ),
    Schritt(
        key="CHAIR_J19_ANTIKOKZIDIUM",
        tierart=Tierart.MASTHUHN,
        von_tag=19,
        bis_tag=21,
        titel="Antikokzidium",
        kategorie=Kategorie.ANTIKOKZIDIUM,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["VETACOX", "AMPROLIUM", "TRISULMYCINE FORTE", "VOLACOX", "ANTICOX"],
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
    ),
    Schritt(
        key="CHAIR_J21_ND_RAPPEL_2",
        tierart=Tierart.MASTHUHN,
        von_tag=21,
        bis_tag=21,
        titel="Newcastle-Auffrischung + Bronchite H120",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["CLONE", "LASOTA", "+ Bronchite H120"],
        folgt_auf="CHAIR_J10_ND_RAPPEL",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        issues=[
            "Antikokzidium (J19-J21) und Impfung am selben Tag J21 — "
            "das Blatt sagt nicht, was zuerst geht"
        ],
    ),
    Schritt(
        key="CHAIR_J22_VITAMINE",
        tierart=Tierart.MASTHUHN,
        von_tag=22,
        bis_tag=23,
        titel="Vitamine",
        kategorie=Kategorie.VITAMINE,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["VITAFLASH", "AMIN'TOTAL", "Vitamin AD3E+C", "BIOMULTI"],
    ),
    Schritt(
        key="CHAIR_J24_ATEMWEGE",
        tierart=Tierart.MASTHUHN,
        von_tag=24,
        bis_tag=27,
        titel="Prävention Atemwegserkrankungen",
        kategorie=Kategorie.MEDIKATION,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["ENROSOL", "HIPRALONA ENRO", "TYLODOX EXTRA", "NORFLOXAN 20%"],
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
    ),
    Schritt(
        key="CHAIR_J30_ND_SPAET",
        tierart=Tierart.MASTHUHN,
        von_tag=30,
        bis_tag=30,
        titel="Newcastle-Auffrischung bei später Schlachtung",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["CLONE", "LASOTA"],
        bedingt="spaete_schlachtung",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
    ),
    Schritt(
        key="CHAIR_J40_ANTIKOKZIDIUM_SPAET",
        tierart=Tierart.MASTHUHN,
        von_tag=40,
        bis_tag=42,
        titel="Antikokzidium bei später Schlachtung",
        kategorie=Kategorie.ANTIKOKZIDIUM,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["VETACOX", "AMPROLIUM", "TRISULMYCINE FORTE", "DICLACOX", "ANTICOX"],
        bedingt="spaete_schlachtung",
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
    ),
]


PROGRAMM_LEGEHENNE: list[Schritt] = [
    Schritt(
        key="PONDEUSE_J0_EINSTREU",
        tierart=Tierart.LEGEHENNE,
        von_tag=0,
        bis_tag=2,
        titel="Einstreu mit Kupfersulfat behandeln",
        kategorie=Kategorie.HYGIENE,
        verabreichung=Verabreichung.SPRUEHUNG,
        praeparate=["Kupfersulfat 0,5 g/l"],
        hinweis="Vor dem Einstallen und zwei Tage in Anwesenheit der Küken",
    ),
    Schritt(
        key="PONDEUSE_J1_ND_INAKTIVIERT",
        tierart=Tierart.LEGEHENNE,
        von_tag=1,
        bis_tag=3,
        titel="Newcastle inaktiviert, subkutan",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.INJEKTION,
        praeparate=[
            "CEVAC BROILER NDK 0,1 ml (nur im Brüter)",
            "IMOPEST 0,3 ml",
            "CEVAC NEW K 0,3 ml",
            "ITA-NEW ND 0,3 ml",
        ],
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        hinweis="Im Brüter — oder an J3 im Betrieb",
    ),
    Schritt(
        key="PONDEUSE_J1_ND_IB_LEBEND",
        tierart=Tierart.LEGEHENNE,
        von_tag=1,
        bis_tag=1,
        titel="Newcastle + Bronchite lebend (H120 + Variante)",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.AUGENTROPFEN,
        praeparate=[
            "CEVAC VITABRON + CEVAC IBIRD",
            "AVINEW + H120 + CEVAC IBIRD",
            "AVI ND HB1/IB + CEVAC IBIRD",
            "HB1/H120 + CEVAC IBIRD",
        ],
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
    ),
    Schritt(
        key="PONDEUSE_J1_START",
        tierart=Tierart.LEGEHENNE,
        von_tag=1,
        bis_tag=1,
        titel="Starttrunk: Zuckerwasser bzw. Vitamin C",
        kategorie=Kategorie.VITAMINE,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["Zuckerwasser 50 g/l", "Vitamin C 0,5 g/l", "HEPASOL", "VIGOSINE"],
    ),
    Schritt(
        key="PONDEUSE_J2_ANTIBIOTIKUM",
        tierart=Tierart.LEGEHENNE,
        von_tag=2,
        bis_tag=6,
        titel="Antibiotika + Vitamine",
        kategorie=Kategorie.MEDIKATION,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=[
            "COVIT",
            "TETRACOLIVIT",
            "COLITERRAVET",
            "COLIVET",
            "PANTERYL",
            "VIGAL 2X",
            "SUPER LAYER",
        ],
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
    ),
    Schritt(
        key="PONDEUSE_J7_GUMBORO_1",
        tierart=Tierart.LEGEHENNE,
        von_tag=7,
        bis_tag=7,
        titel="1. Gumboro-Impfung (intermediärer Stamm)",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["CEVAC GUMBO L", "AVI IBD INTER", "HIPRAGUMBORO CH80", "BUR706"],
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        hinweis="Augentropfen oder Trinkwasser",
    ),
    Schritt(
        key="PONDEUSE_J10_ND_IB_RAPPEL",
        tierart=Tierart.LEGEHENNE,
        von_tag=10,
        bis_tag=10,
        titel="Newcastle + Bronchite lebend auffrischen",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=[
            "CEVAC VITABRON + CEVAC IBIRD",
            "AVINEW + H120 + CEVAC IBIRD",
            "HB1/H120 + CEVAC IBIRD",
            "AVI ND HB1/IB + CEVAC IBIRD",
        ],
        folgt_auf="PONDEUSE_J1_ND_IB_LEBEND",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
    ),
    Schritt(
        key="PONDEUSE_J12_GUMBORO_2",
        tierart=Tierart.LEGEHENNE,
        von_tag=12,
        bis_tag=12,
        titel="2. Gumboro-Impfung (intermediate plus)",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["CEVAC IBDL", "AVI IBD PLUS", "NOBILIS 228E", "HIPRAGUMBORO GM97"],
        folgt_auf="PONDEUSE_J7_GUMBORO_1",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
    ),
    Schritt(
        key="PONDEUSE_J17_GUMBORO_3",
        tierart=Tierart.LEGEHENNE,
        von_tag=17,
        bis_tag=17,
        titel="3. Gumboro-Impfung (intermediate plus)",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["CEVAC IBDL", "AVI IBD PLUS", "NOBILIS 228 E", "HIPRAGUMBORO GM97"],
        folgt_auf="PONDEUSE_J12_GUMBORO_2",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        issues=[
            "Das Blatt nennt J12 UND J17 beide '2ème Vaccin GUMBORO' — "
            "hier als 2. und 3. Gabe geführt, Zählung des Originals prüfen"
        ],
    ),
    Schritt(
        key="PONDEUSE_J18_ANTIKOKZIDIUM",
        tierart=Tierart.LEGEHENNE,
        von_tag=18,
        bis_tag=20,
        titel="Antikokzidium",
        kategorie=Kategorie.ANTIKOKZIDIUM,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["VETACOX", "DICLACOX", "ANTICOX", "AMPROLIUM", "AMPROL", "AMPROSTAT"],
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
    ),
    Schritt(
        key="PONDEUSE_J21_ND_IB",
        tierart=Tierart.LEGEHENNE,
        von_tag=21,
        bis_tag=21,
        titel="Newcastle-Auffrischung + Bronchite H120",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["AVINEW", "HB1", "CLONE", "+ Bronchite H120"],
        folgt_auf="PONDEUSE_J10_ND_IB_RAPPEL",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
    ),
    Schritt(
        key="PONDEUSE_J23_ANTIBIOTIKUM",
        tierart=Tierart.LEGEHENNE,
        von_tag=23,
        bis_tag=26,
        titel="Antibiotika + Vitamine",
        kategorie=Kategorie.MEDIKATION,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=[
            "COVIT",
            "TETRACOLIVIT",
            "COLITERRAVET",
            "COLIVET",
            "PANTERYL",
            "VIGAL 2X",
            "SUPER LAYER",
        ],
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
    ),
    Schritt(
        key="PONDEUSE_J28_VITAMINE",
        tierart=Tierart.LEGEHENNE,
        von_tag=28,
        bis_tag=32,
        titel="Vitamine",
        kategorie=Kategorie.VITAMINE,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["VITAFLASH", "VITAPEROS", "AD3E+C", "AMIN'TOTAL"],
    ),
    Schritt(
        key="PONDEUSE_W5_VARIOLE",
        tierart=Tierart.LEGEHENNE,
        von_tag=_W5[0],
        bis_tag=_W5[1],
        titel="Pocken-Impfung (Variole) in die Flügelfalte",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.FLUEGELFALTE,
        praeparate=["HIPRAPOX", "DIFTOSEC", "AVI POX", "VECTORMUNE FP-MG"],
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        hinweis="VECTORMUNE FP-MG schützt zusätzlich gegen Mykoplasmen",
    ),
    Schritt(
        key="PONDEUSE_W6_ANTIKOKZIDIUM",
        tierart=Tierart.LEGEHENNE,
        von_tag=_W6[0],
        bis_tag=_W6[1],
        titel="Antikokzidium über 3 Tage",
        kategorie=Kategorie.ANTIKOKZIDIUM,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["VETACOX", "DICLACOX", "AMPROLIUM", "AMPROL", "AMPROSTAT"],
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
    ),
    Schritt(
        key="PONDEUSE_D35_ND_RAPPEL",
        tierart=Tierart.LEGEHENNE,
        von_tag=35,
        bis_tag=40,
        titel="Newcastle-Auffrischung im Trinkwasser",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["LA SOTA", "CLONE", "AVINEW"],
        folgt_auf="PONDEUSE_J21_ND_IB",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        issues=[
            "Zeile steht auf dem Blatt in Woche 6 (Tag 36-42), ist dort aber auf "
            "Tag 35-40 datiert — die explizite Tagesangabe gilt"
        ],
    ),
    Schritt(
        key="PONDEUSE_W7_DEBECQUAGE",
        tierart=Tierart.LEGEHENNE,
        von_tag=_W7[0],
        bis_tag=_W7[1],
        titel="Schnabelkürzen (Débecquage)",
        kategorie=Kategorie.EINGRIFF,
        verabreichung=Verabreichung.HANDGRIFF,
        hinweis="Vitamin K und Stützmittel von j-1 bis j+2 — siehe Folgeschritt",
    ),
    Schritt(
        key="PONDEUSE_W7_ND_INAKTIVIERT",
        tierart=Tierart.LEGEHENNE,
        von_tag=_W7[0],
        bis_tag=_W7[1],
        titel="Newcastle inaktiviert, Injektion (am Tag des Débecquage)",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.INJEKTION,
        praeparate=["IMOPEST", "CEVAC NEW K", "ITA-NEW ND", "NEWCAVAC"],
        folgt_auf="PONDEUSE_W7_DEBECQUAGE",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
    ),
    Schritt(
        key="PONDEUSE_W7_VITAMIN_K",
        tierart=Tierart.LEGEHENNE,
        von_tag=_W7[0] - 1,
        bis_tag=_W7[1] + 2,
        titel="Vitamin K + Stützmittel um das Débecquage (j-1 bis j+2)",
        kategorie=Kategorie.VITAMINE,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["VIGAL 2X", "PANTERYL", "TETRACOLIVIT", "SUPER LAYER", "+ Vitamin K"],
        folgt_auf="PONDEUSE_W7_DEBECQUAGE",
        hinweis="Fenster relativ zum tatsächlichen Débecquage-Tag, nicht zur Woche",
    ),
    Schritt(
        key="PONDEUSE_D57_ND_WASSER",
        tierart=Tierart.LEGEHENNE,
        von_tag=57,
        bis_tag=60,
        titel="Newcastle-Auffrischung im Trinkwasser",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["LA SOTA", "CLONE", "AVINEW"],
        folgt_auf="PONDEUSE_D35_ND_RAPPEL",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        issues=[
            "Das Blatt führt diese Auffrischung zweimal: in der Woche-7-Zeile mit "
            "Tag 57-60 und noch einmal als Zeile 'Woche 9' — hier EIN Termin"
        ],
    ),
    Schritt(
        key="PONDEUSE_W9_ENTWURMUNG",
        tierart=Tierart.LEGEHENNE,
        von_tag=_W9[0],
        bis_tag=_W9[1],
        titel="Entwurmung",
        kategorie=Kategorie.ENTWURMUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["POLYSTRONGLE", "LEVASOL 20%", "LEVALAP"],
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
    ),
    Schritt(
        key="PONDEUSE_W10_ANTIKOKZIDIUM",
        tierart=Tierart.LEGEHENNE,
        von_tag=_W10[0],
        bis_tag=_W10[1],
        titel="Antikokzidium über 3 Tage",
        kategorie=Kategorie.ANTIKOKZIDIUM,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["VETACOX", "DICLACOX", "AMPROLIUM", "AMPROL", "AMPROSTAT"],
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
    ),
    Schritt(
        key="PONDEUSE_W10_IB",
        tierart=Tierart.LEGEHENNE,
        von_tag=_W10[0],
        bis_tag=_W10[1],
        titel="Bronchite H120 + IB-Variante auffrischen",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["H120 + CEVAC IBIRD", "H120 + GALLIVAC IB 88", "H120 + AVI IB VAR"],
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
    ),
    Schritt(
        key="PONDEUSE_W10_VARIOLE_RAPPEL",
        tierart=Tierart.LEGEHENNE,
        von_tag=_W10[0],
        bis_tag=_W10[1],
        titel="Pocken-Auffrischung in die Flügelfalte",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.FLUEGELFALTE,
        praeparate=["HIPRAPOX", "DIFTOSEC", "AVI POX"],
        folgt_auf="PONDEUSE_W5_VARIOLE",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
    ),
    Schritt(
        key="PONDEUSE_W11_CORYZA",
        tierart=Tierart.LEGEHENNE,
        von_tag=_W11[0],
        bis_tag=_W11[1],
        titel="Coryza infectiosa, Injektion",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.INJEKTION,
        praeparate=["CORYMUNE 4K", "HAEMOVAX", "CORIPRAVAC", "ITA CORYZA ABC Gel"],
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        hinweis="CORYMUNE 4K schützt zusätzlich gegen Salmonellen",
    ),
    Schritt(
        key="PONDEUSE_W13_ENTWURMUNG",
        tierart=Tierart.LEGEHENNE,
        von_tag=_W13[0],
        bis_tag=_W13[1],
        titel="Entwurmung",
        kategorie=Kategorie.ENTWURMUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["Piperazin-Citrat"],
        folgt_auf="PONDEUSE_W9_ENTWURMUNG",
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
    ),
    Schritt(
        key="PONDEUSE_W16_CORYZA_KOMBI",
        tierart=Tierart.LEGEHENNE,
        von_tag=_W16[0],
        bis_tag=_W16[1],
        titel="Coryza auffrischen + inaktiviert ND/IB/EDS (Legedepression)",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.INJEKTION,
        praeparate=[
            "CORYMUNE 7K",
            "ITA ND+IB+EDS+COR ABC",
            "CORIPRAVAC + ITA CORYZA ABC + HAEMOVAX",
            "ITA ND IB EDSK",
        ],
        folgt_auf="PONDEUSE_W11_CORYZA",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        hinweis="CORYMUNE 7K schützt zusätzlich gegen Salmonellen",
    ),
]


WIEDERKEHREND_LEGEPHASE: list[Dauerregel] = [
    Dauerregel(
        key="PONTE_ENTWURMUNG",
        titel="Innere Entwurmung (Präparate abwechseln)",
        kategorie=Kategorie.ENTWURMUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["LEVASOL", "LEVALAP", "POLYSTRONGLE", "PIPERAZIN"],
        intervall_tage=30,
        hinweis="Jeden Monat, Wirkstoff wechseln",
    ),
    Dauerregel(
        key="PONTE_VITAMINE",
        titel="Vitamine",
        kategorie=Kategorie.VITAMINE,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["VITAFLASH", "VITAPEROS", "AD3E+C", "AMIN'TOTAL"],
        intervall_tage=60,
        hinweis="Alle zwei Monate",
    ),
    Dauerregel(
        key="PONTE_ND",
        titel="Newcastle auffrischen",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["CLONE", "LASOTA"],
        intervall_tage=30,
        hinweis="LASOTA vor dem Legepeak vermeiden",
    ),
    Dauerregel(
        key="PONTE_IB_H120",
        titel="Bronchite H120",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["H120"],
        intervall_tage=30,
        hinweis="Im Wechsel mit CEVAC IBIRD",
    ),
    Dauerregel(
        key="PONTE_IB_IBIRD",
        titel="Bronchite CEVAC IBIRD",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["CEVAC IBIRD"],
        intervall_tage=90,
        hinweis="Alle drei Monate",
    ),
]


# =======================================================================
# Zweites Blatt für dieselbe Tierart: VETO-NEGOCES / TCHA AGGRO CENTER.
#
# Es ist kein Nachtrag zum IVOGRAIN-Blatt, sondern ein eigener Plan, der
# an fast jedem Datum etwas anderes sagt (Gumboro J14/J21 statt J12/J17,
# ND-Auffrischung alle sechs Monate statt alle dreißig Tage). Zusammen-
# legen wäre eine Entscheidung — die trifft der Betrieb, nicht der Code.
# Deshalb steht es vollständig daneben und wird je Herde gewählt.
#
# Abkürzungen des Blattes: EB = Eau de Boisson (Trinkwasser),
# IM = Intra Musculaire, NEW L = Lasota, BRON = H120,
# IBird = Variante der infektiösen Bronchitis, UNI L = HB1.
# =======================================================================

VITAFLASH = ["VITAFLASH", "POWERVIT"]
"""Die Anti-Stress-/Vitamin-Alternative, die das Blatt durchgehend nennt."""

LEBERSCHUTZ_MITTEL = ["HEPAROL PLUS", "SEQUTONIC PLUS"]
ANTIKOKZIDIUM_MITTEL = ["COX B3", "AMPROLIUM"]
ENTWURMUNG_MITTEL = ["LEVASOL", "PIPER DEWORMER"]


def _stress(von: int, bis: int, nummer: int, praeparate: list[str] | None = None) -> Schritt:
    """Anti-Stress-Gabe im Trinkwasser — das Blatt setzt sie um jeden
    Eingriff herum, deshalb ein Bauer statt zwanzig Wiederholungen."""
    return Schritt(
        key=f"VETO_J{von}_ANTISTRESS_{nummer}",
        tierart=Tierart.LEGEHENNE,
        von_tag=von,
        bis_tag=bis,
        titel="Anti-Stress ins Trinkwasser",
        kategorie=Kategorie.ANTI_STRESS,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=list(praeparate or VITAFLASH),
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
        quelle=VETO,
    )


def _pause(von: int, bis: int, nummer: int) -> Schritt:
    """„EAU SIMPLE“ — einfaches Wasser, ausdrücklich nichts dazu."""
    return Schritt(
        key=f"VETO_J{von}_EAU_SIMPLE_{nummer}",
        tierart=Tierart.LEGEHENNE,
        von_tag=von,
        bis_tag=bis,
        titel="Einfaches Wasser — nichts zugeben",
        kategorie=Kategorie.PAUSE,
        verabreichung=Verabreichung.TRINKWASSER,
        hinweis="Das Blatt schreibt hier ausdrücklich „EAU SIMPLE“ — die Lücke ist gewollt.",
        quelle=VETO,
    )


PROGRAMM_LEGEHENNE_VETO: list[Schritt] = [
    Schritt(
        key="VETO_J1_ANTISTRESS",
        tierart=Tierart.LEGEHENNE,
        von_tag=1,
        bis_tag=4,
        titel="Anti-Stress zum Einstallen",
        kategorie=Kategorie.ANTI_STRESS,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["VITAFLASH", "HEPAROL PLUS"],
        dosis_je_liter="VITAFLASH 1 g/l + Zuckerwasser 50 g/l — oder HEPAROL PLUS 2 ml/l",
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
        quelle=VETO,
    ),
    Schritt(
        key="VETO_J5_ND_IB",
        tierart=Tierart.LEGEHENNE,
        von_tag=5,
        bis_tag=5,
        titel="Newcastle + Bronchite infectieuse impfen",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["CEVAC BIL", "CEVAC BRON (H120) + UNI L (HB1)"],
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        quelle=VETO,
    ),
    Schritt(
        key="VETO_J6_VITAMINE",
        tierart=Tierart.LEGEHENNE,
        von_tag=6,
        bis_tag=6,
        titel="Vitamine nach der Impfung",
        kategorie=Kategorie.VITAMINE,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=list(VITAFLASH),
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
        quelle=VETO,
    ),
    Schritt(
        key="VETO_J7_GUMBORO_1",
        tierart=Tierart.LEGEHENNE,
        von_tag=7,
        bis_tag=7,
        titel="1. Gumboro-Impfung",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["GUMBO L", "IBD inter"],
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        quelle=VETO,
    ),
    _pause(8, 12, 1),
    Schritt(
        key="VETO_J13_VITAMINE",
        tierart=Tierart.LEGEHENNE,
        von_tag=13,
        bis_tag=13,
        titel="Vitamine vor der 2. Gumboro-Impfung",
        kategorie=Kategorie.VITAMINE,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=list(VITAFLASH),
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
        quelle=VETO,
    ),
    Schritt(
        key="VETO_J14_GUMBORO_2",
        tierart=Tierart.LEGEHENNE,
        von_tag=14,
        bis_tag=14,
        titel="2. Gumboro-Impfung",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["CEVAC IBDL", "IBD PLUS"],
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        quelle=VETO,
    ),
    _stress(15, 16, 1),
    Schritt(
        key="VETO_J17_ANTIKOKZIDIUM",
        tierart=Tierart.LEGEHENNE,
        von_tag=17,
        bis_tag=19,
        titel="Antikokzidium über 3 Tage",
        kategorie=Kategorie.ANTIKOKZIDIUM,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=list(ANTIKOKZIDIUM_MITTEL),
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
        quelle=VETO,
        issues=[
            "Die Zeile ist auf dem Blatt mit "
            "„ANTI-STRESS (EB)“ überschrieben, nennt aber COX B3 bzw. AMPROLIUM — "
            "beides Antikokzidia. Hier nach dem Präparat eingeordnet, "
            "Überschrift des Originals prüfen."
        ],
    ),
    _stress(20, 20, 2),
    Schritt(
        key="VETO_J21_GUMBORO_3",
        tierart=Tierart.LEGEHENNE,
        von_tag=21,
        bis_tag=21,
        titel="3. Gumboro-Impfung",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["CEVAC IBDL", "IBD PLUS"],
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        quelle=VETO,
    ),
    Schritt(
        key="VETO_J22_LEBERSCHUTZ",
        tierart=Tierart.LEGEHENNE,
        von_tag=22,
        bis_tag=24,
        titel="Leberschutz über 3 Tage",
        kategorie=Kategorie.LEBERSCHUTZ,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=list(LEBERSCHUTZ_MITTEL),
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
        quelle=VETO,
    ),
    Schritt(
        key="VETO_J25_ND_IB",
        tierart=Tierart.LEGEHENNE,
        von_tag=25,
        bis_tag=25,
        titel="Newcastle + Bronchite auffrischen",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=[
            "CEVAC NEW L (Lasota) + CEVAC BRON",
            "CEVAC NEW L + CEVAC IBird",
        ],
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        quelle=VETO,
    ),
    _stress(26, 29, 3),
    _pause(30, 34, 2),
    Schritt(
        key="VETO_J35_ND",
        tierart=Tierart.LEGEHENNE,
        von_tag=35,
        bis_tag=35,
        titel="Newcastle auffrischen",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["CEVAC NEW L"],
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        quelle=VETO,
    ),
    _stress(36, 38, 4),
    _pause(39, 40, 3),
    _stress(41, 41, 5),
    Schritt(
        key="VETO_J42_POCKEN",
        tierart=Tierart.LEGEHENNE,
        von_tag=42,
        bis_tag=42,
        titel="Pocken-Impfung in die Flügelfalte (transfixion alaire)",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.FLUEGELFALTE,
        praeparate=["CEVAC FPL", "DIFTOSEC", "AVIPOX"],
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        quelle=VETO,
    ),
    _stress(43, 45, 6),
    Schritt(
        key="VETO_J46_ANTIKOKZIDIUM",
        tierart=Tierart.LEGEHENNE,
        von_tag=46,
        bis_tag=48,
        titel="Antikokzidium über 3 Tage",
        kategorie=Kategorie.ANTIKOKZIDIUM,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["AMPROLIUM", "COX B3"],
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
        quelle=VETO,
    ),
    _stress(49, 49, 7),
    Schritt(
        key="VETO_J50_ENTWURMUNG",
        tierart=Tierart.LEGEHENNE,
        von_tag=50,
        bis_tag=50,
        titel="Innere Entwurmung",
        kategorie=Kategorie.ENTWURMUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["LEVASOLE", "PIPER DEWORMER"],
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
        quelle=VETO,
    ),
    Schritt(
        key="VETO_J51_LEBERSCHUTZ",
        tierart=Tierart.LEGEHENNE,
        von_tag=51,
        bis_tag=55,
        titel="Leberschutz über 5 Tage",
        kategorie=Kategorie.LEBERSCHUTZ,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=list(LEBERSCHUTZ_MITTEL),
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
        quelle=VETO,
    ),
    _stress(56, 58, 8),
    _pause(59, 80, 4),
    _stress(81, 83, 9),
    Schritt(
        key="VETO_J84_CORYZA",
        tierart=Tierart.LEGEHENNE,
        von_tag=84,
        bis_tag=84,
        titel="Coryza (A, B, C) + Salmonellose, Injektion",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.INJEKTION,
        praeparate=["CORYMUNE 4 K"],
        hinweis="Intramuskulär (IM)",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        quelle=VETO,
    ),
    _stress(85, 87, 10),
    Schritt(
        key="VETO_J88_ENTWURMUNG",
        tierart=Tierart.LEGEHENNE,
        von_tag=88,
        bis_tag=88,
        titel="Innere Entwurmung",
        kategorie=Kategorie.ENTWURMUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=list(ENTWURMUNG_MITTEL),
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
        quelle=VETO,
    ),
    _stress(89, 91, 11),
    Schritt(
        key="VETO_J92_ANTIKOKZIDIUM",
        tierart=Tierart.LEGEHENNE,
        von_tag=92,
        bis_tag=96,
        titel="Antikokzidium über 5 Tage",
        kategorie=Kategorie.ANTIKOKZIDIUM,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=list(ANTIKOKZIDIUM_MITTEL),
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
        quelle=VETO,
    ),
    Schritt(
        key="VETO_J97_LEBERSCHUTZ",
        tierart=Tierart.LEGEHENNE,
        von_tag=97,
        bis_tag=103,
        titel="Leberschutz über 7 Tage",
        kategorie=Kategorie.LEBERSCHUTZ,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=list(LEBERSCHUTZ_MITTEL),
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
        quelle=VETO,
    ),
    _pause(104, 116, 5),
    _stress(117, 119, 12),
    Schritt(
        key="VETO_J120_KOMBI",
        tierart=Tierart.LEGEHENNE,
        von_tag=120,
        bis_tag=120,
        titel=(
            "Coryza + Salmonellose + Enteritis + Newcastle + Bronchite + Legedepression, Injektion"
        ),
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.INJEKTION,
        praeparate=["CORYMUNE 7 K", "CORYMUNE 4 K + NDIBEDSK (new bron trica)"],
        hinweis="Intramuskulär (IM) — die letzte große Gabe vor der Legephase",
        vorlauf_tage=VORLAUF_IMPFSTOFF_TAGE,
        quelle=VETO,
        issues=[
            "Das Blatt schreibt hier „CORYMINE“, an J84 aber "
            "„CORYMUNE“ — vermutlich dasselbe Mittel, Schreibweise am Original prüfen."
        ],
    ),
    _stress(121, 123, 13),
    Schritt(
        key="VETO_J124_ENTWURMUNG",
        tierart=Tierart.LEGEHENNE,
        von_tag=124,
        bis_tag=124,
        titel="Entwurmung innen und außen",
        kategorie=Kategorie.ENTWURMUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["KEPROMEC ORAL", "LEVASOL + äußeres Entwurmungsmittel"],
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
        quelle=VETO,
    ),
    Schritt(
        key="VETO_J125_ANTISTRESS",
        tierart=Tierart.LEGEHENNE,
        von_tag=125,
        bis_tag=127,
        titel="Anti-Stress ins Trinkwasser",
        kategorie=Kategorie.ANTI_STRESS,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=list(VITAFLASH),
        vorlauf_tage=VORLAUF_MEDIKAMENT_TAGE,
        quelle=VETO,
        issues=[
            "Die Zeile nennt VITAFLASH/POWERVIT UND „EAU SIMPLE“ "
            "nebeneinander — beides zugleich geht nicht. Hier als Anti-Stress geführt."
        ],
    ),
    Schritt(
        key="VETO_J128_FUEHRUNG",
        tierart=Tierart.LEGEHENNE,
        von_tag=128,
        bis_tag=OFFENES_ENDE,
        titel="Gute Stallführung bis zur Ausstallung (Réforme)",
        kategorie=Kategorie.HYGIENE,
        verabreichung=Verabreichung.HANDGRIFF,
        hinweis="Ab hier trägt die Stallführung; die Entwurmung läuft alle zwei Monate weiter.",
        quelle=VETO,
        issues=[
            "Das Blatt endet mit „à la Réforme“ und nennt kein "
            "Datum — der Schritt läuft offen bis zur Ausstallung."
        ],
    ),
]


WIEDERKEHREND_VETO: list[Dauerregel] = [
    Dauerregel(
        key="VETO_DAUER_ENTWURMUNG",
        titel="Entwurmung (Präparate abwechseln)",
        kategorie=Kategorie.ENTWURMUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["PIPER DEWORMER", "KEPROMEC ORAL"],
        intervall_tage=60,
        hinweis="„Penser au déparasitage à chaque deux mois“ — ab Tag 128",
        ab_tag=128,
    ),
    Dauerregel(
        key="VETO_DAUER_ND_IB",
        titel="Newcastle + Bronchite infectieuse auffrischen",
        kategorie=Kategorie.IMPFUNG,
        verabreichung=Verabreichung.TRINKWASSER,
        praeparate=["CEVAC NEW L", "CEVAC BRON (H120)"],
        intervall_tage=180,
        hinweis="„Tous les 6 mois“ — deutlich seltener als im IVOGRAIN-Blatt (dort alle 30 Tage)",
        ab_tag=128,
    ),
]


HINWEISE_VETO = [
    "Der Zugang zum Stall ist streng auf Sie und Ihren Tierarzt beschränkt.",
    "Geimpft wird nur auf gesunde Tiere.",
    "Alle sechs Monate sind Auffrischungen gegen Newcastle und infektiöse Bronchitis nötig.",
    "Der Stall muss gut belüftet sein; Staub vermeiden.",
    "Gleichwertige Präparate vom Markt sind erlaubt — fragen Sie Ihren Tierarzt.",
    "Bei jeder Verhaltensänderung der Tiere den Tierarzt anrufen.",
]


# --- Die Blätter als Ganzes, wählbar je Herde ---------------------------

HINWEISE_IVOGRAIN = [
    "Impfstoffe gekühlt halten und innerhalb von zwei Stunden verbrauchen.",
    "Vor jeder Trinkwasserimpfung zwei Stunden dursten lassen.",
    "Nur gesunde Tiere impfen.",
]

PROGRAMME: list[Programm] = [
    Programm(
        programm_id="IVOGRAIN_CHAIR",
        titel="Masthuhn — IVOGRAIN",
        tierart=Tierart.MASTHUHN,
        quelle=IVOGRAIN,
        herausgeber="IVOGRAIN",
        schritte=PROGRAMM_MASTHUHN,
        hinweise=HINWEISE_IVOGRAIN,
        vorgabe=True,
    ),
    Programm(
        programm_id="IVOGRAIN_PONDEUSE",
        titel="Legehenne — IVOGRAIN",
        tierart=Tierart.LEGEHENNE,
        quelle=IVOGRAIN,
        herausgeber="IVOGRAIN",
        schritte=PROGRAMM_LEGEHENNE,
        dauerregeln=WIEDERKEHREND_LEGEPHASE,
        hinweise=HINWEISE_IVOGRAIN,
        vorgabe=True,
    ),
    Programm(
        programm_id="VETO_PONDEUSE",
        titel="Legehenne — VETO-NEGOCES",
        tierart=Tierart.LEGEHENNE,
        quelle=VETO,
        herausgeber="VETO-NEGOCES / TCHA AGGRO CENTER, Dr. BANGUE",
        schritte=PROGRAMM_LEGEHENNE_VETO,
        dauerregeln=WIEDERKEHREND_VETO,
        hinweise=HINWEISE_VETO,
    ),
]


def alle_programme(tierart: Tierart | None = None) -> list[Programm]:
    """Alle Blätter, optional auf eine Tierart gefiltert."""
    return [p for p in PROGRAMME if tierart is None or p.tierart is tierart]


def vorgabe_programm(tierart: Tierart) -> Programm:
    """Das Blatt, das gilt, solange niemand gewählt hat."""
    for p in PROGRAMME:
        if p.tierart is tierart and p.vorgabe:
            return p
    raise KeyError(f"Kein Vorgabe-Programm für {tierart.value}")


def programm(tierart: Tierart, programm_id: str | None = None) -> Programm:
    """Das Blatt einer Herde.

    Eine unbekannte oder zur Tierart unpassende Wahl fällt auf die Vorgabe
    zurück — still zu scheitern hieße, eine Herde ohne Plan zu führen. Dass
    es passiert ist, meldet `programm_konflikt`.
    """
    if programm_id:
        for p in PROGRAMME:
            if p.programm_id == programm_id and p.tierart is tierart:
                return p
    return vorgabe_programm(tierart)


def programm_konflikt(tierart: Tierart, programm_id: str | None) -> str | None:
    """Befund, wenn die Wahl nicht zur Tierart passt — sonst None."""
    if not programm_id:
        return None
    treffer = [p for p in PROGRAMME if p.programm_id == programm_id]
    if not treffer:
        return (
            f"Programm „{programm_id}“ ist unbekannt — es gilt „{vorgabe_programm(tierart).titel}“."
        )
    if treffer[0].tierart is not tierart:
        return (
            f"Programm „{treffer[0].titel}“ gilt für {treffer[0].tierart.value}, "
            f"die Herde ist {tierart.value} — es gilt "
            f"„{vorgabe_programm(tierart).titel}“."
        )
    return None
