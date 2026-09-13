"""Zwei Sprachen für die Oberfläche: Deutsch und Französisch.

Das Briefing nannte FR/EN-Zweisprachigkeit für Westafrika ausdrücklich —
und die Quellblätter sind ohnehin französisch. Wer im Stall abhakt, soll
nicht erst Deutsch lernen müssen.

Drei Entscheidungen:

* **Nur die Oberfläche wird übersetzt, nicht die Daten.** Präparatnamen,
  Rezeptposten und Befunde bleiben, wie sie sind. Ein Befund, der in der
  Übersetzung eine Nuance verliert, ist schlimmer als einer auf Deutsch.
* **Fehlt eine Vokabel, steht der deutsche Text da** — nicht ein leeres
  Feld und kein Schlüsselname.
* **Die Wahl lebt im Browser** (`localStorage`), nicht in der Datenbank:
  die Sprache gehört dem Menschen vor dem Gerät, nicht dem Konto.
"""

from __future__ import annotations

import json

SPRACHEN = ("de", "fr")
VORGABE = "de"

FRANZOESISCH: dict[str, str] = {
    # Kopf und Bedienung
    "Taktgeber": "Cadenceur",
    "Prophylaxe und Fütterung je Herde": "Prophylaxie et alimentation par bande",
    "Herde": "Bande",
    "Stichtag": "Date de référence",
    "Futtervorrat (kg)": "Stock d'aliment (kg)",
    "Anzeigen": "Afficher",
    "Ansicht wechseln": "Changer l'affichage",
    "Abmelden": "Se déconnecter",
    "Anmelden": "Se connecter",
    "Anmeldename": "Identifiant",
    "Passwort": "Mot de passe",
    "Sprache": "Langue",
    "Lade …": "Chargement …",
    "Rückgängig": "Annuler",
    "Abbrechen": "Annuler",
    "Erledigt": "Fait",
    "Abhaken": "Valider",
    "Geprüft": "Vérifié",
    "Rechnen": "Calculer",
    "Melden": "Signaler",
    "Buchen": "Enregistrer",
    "Jetzt nachreichen": "Envoyer maintenant",
    # Abschnitte
    "Überfällig": "En retard",
    "Jetzt dran": "À faire maintenant",
    "Jetzt besorgen": "À commander",
    "Demnächst": "Prochainement",
    "Zuletzt erledigt": "Derniers faits",
    "Zu prüfen": "À vérifier",
    "Wartezeit": "Délai d'attente",
    "Futter": "Aliment",
    "Mischauftrag": "Ordre de mélange",
    "Vorfall melden": "Signaler un incident",
    "Abgang buchen": "Enregistrer une sortie",
    "Befunde": "Constats",
    # Zustände
    "überfällig": "en retard",
    "jetzt dran": "à faire",
    "geplant": "prévu",
    "erledigt": "fait",
    # Formularfelder
    "Menge (kg)": "Quantité (kg)",
    "Bei Überhang": "En cas d'excédent",
    "über den Energieträger ausgleichen": "compenser sur la céréale",
    "wie auf dem Blatt rechnen": "calculer comme sur la fiche",
    "alles anteilig skalieren": "tout mettre à l'échelle",
    "Als gemischt buchen": "Enregistrer comme mélangé",
    "Art": "Type",
    "Festgestellt am": "Constaté le",
    "Beobachtung": "Observation",
    "optional": "facultatif",
    "Tiere": "Animaux",
    "Grund": "Motif",
    "Am": "Le",
    "verendet": "mort",
    "gekeult": "abattu",
    "verkauft": "vendu",
    "sonstiges": "autre",
    "Welches Mittel wurde gegeben?": "Quel produit a été administré ?",
    # Sätze
    "Das Schema startet am gemeldeten Tag.": "Le protocole démarre le jour signalé.",
    "Bleibt liegen, bis jemand am Original nachsieht.": (
        "Reste ouvert jusqu'à vérification sur l'original."
    ),
    "Vorlauf läuft — muss da sein, bevor der Tag kommt.": (
        "Délai en cours — doit être là avant le jour venu."
    ),
    "Verkauft ist kein Verlust — der Grund entscheidet, ob es in die Verlustquote zählt.": (
        "Vendu n'est pas une perte — le motif décide du taux de mortalité."
    ),
    "Das hat nicht geklappt: ": "Échec : ",
    "Kein Netz — die Seite arbeitet aus dem Zwischenspeicher.": (
        "Pas de réseau — la page travaille depuis le cache."
    ),
    "Anmeldename oder Passwort stimmt nicht.": "Identifiant ou mot de passe incorrect.",
    # Zur Laufzeit zusammengesetzte Zeilen
    "Tag": "Jour",
    "von": "sur",
    "Woche": "Semaine",
    "Futterphase": "Phase d'alimentation",
    "Für diese Linie liegt kein Futterblatt vor.": ("Aucune fiche d'aliment pour cette lignée."),
    "g/Tier/Tag": "g/animal/jour",
    "kg am Tag": "kg par jour",
    "kg für": "kg pour",
    "Tage": "jours",
    "Vorrat reicht bis": "Stock suffisant jusqu'au",
    "bestellen ab": "commander à partir du",
    "Aus dem eigenen Mischprotokoll gerechnet.": (
        "Calculé à partir du registre de mélange de l'exploitation."
    ),
    "Richtwert — keine Zahl dieses Betriebs.": (
        "Valeur indicative — pas un chiffre de cette exploitation."
    ),
    "Eier": "Œufs",
    "Fleisch": "Viande",
    "gesperrt bis": "bloqué jusqu'au",
}
"""Was auf dem Bildschirm steht, nicht was in den Daten steht."""


def woerterbuch() -> str:
    """Als JSON für die Seite — eine Quelle, kein zweites Wörterbuch im JS."""
    return json.dumps({"fr": FRANZOESISCH}, ensure_ascii=False, sort_keys=True)


def uebersetze(text: str, sprache: str = VORGABE) -> str:
    """Fehlt eine Vokabel, steht der deutsche Text da."""
    if sprache == "fr":
        return FRANZOESISCH.get(text, text)
    return text
