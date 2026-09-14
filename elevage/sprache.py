"""Zwei Sprachen für die Oberfläche: Deutsch und Französisch.

Das Briefing nannte FR/EN-Zweisprachigkeit für Westafrika ausdrücklich —
und die Quellblätter sind ohnehin französisch. Wer im Stall abhakt, soll
nicht erst Deutsch lernen müssen.

Vier Entscheidungen:

* **Französisch ist die Vorgabe.** Die Blätter sind französisch, der Stall
  ist es auch — Deutsch wäre die Sprache des Werkzeugbauers, nicht die der
  Arbeit. Deutsch bleibt wählbar und bleibt die Sprache des Quelltextes.
* **Nur die Oberfläche wird übersetzt, nicht die Daten.** Präparatnamen und
  Rezeptposten bleiben, wie sie sind. Die **Befunde** dagegen tragen seit
  `models.Befund` beide Fassungen: sie erklären, warum etwas nicht stimmt,
  und wer sie nicht lesen kann, kann nichts damit anfangen.
* **Fehlt eine Vokabel, steht der deutsche Text da** — nicht ein leeres
  Feld und kein Schlüsselname.
* **Die Wahl lebt im Browser** (`localStorage`), nicht in der Datenbank:
  die Sprache gehört dem Menschen vor dem Gerät, nicht dem Konto.
"""

from __future__ import annotations

import json

SPRACHEN = ("de", "fr")
VORGABE = "fr"
"""Französisch, nicht Deutsch: das Werkzeug steht in einem Betrieb, der
französisch arbeitet. Deutsch bleibt die Sprache im Quelltext — und die,
auf die zurückgefallen wird, wenn eine Vokabel fehlt."""

FRANZOESISCH: dict[str, str] = {
    # Kopf und Bedienung
    "Taktgeber": "Cadenceur",
    "Prophylaxe und Fütterung je Herde": "Prophylaxie et alimentation par bande",
    "Herde": "Bande",
    "Stichtag": "Date de référence",
    "Futtervorrat (kg)": "Stock (kg)",
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
    "Stand": "État",
    "Was zu tun ist": "Ce qu'il y a à faire",
    "Eintragen": "Saisir",
    "Offene Ausgleiche": "Compensations ouvertes",
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
    "Programm": "Programme",
    "Programm wechseln": "Changer de programme",
    "Blätter vergleichen": "Comparer les programmes",
    "Ruhe": "Repos",
    "Merksätze des Blattes": "Consignes du programme",
    "Tierarzt": "Vétérinaire",
    # Die Antwortzeile ganz oben
    "1 Aufgabe ist überfällig": "1 tâche est en retard",
    "Aufgaben sind überfällig": "tâches sont en retard",
    "1 Aufgabe steht heute an": "1 tâche est à faire aujourd'hui",
    "Aufgaben stehen heute an": "tâches sont à faire aujourd'hui",
    "Heute ist nichts fällig.": "Rien à faire aujourd'hui.",
    "Als Nächstes": "Ensuite",
    # Die Bereichsleiste
    "Heute": "Aujourd'hui",
    "Prüfen": "Vérifier",
    "Bereiche": "Rubriques",
    "Hier ist gerade nichts.": "Rien ici pour le moment.",
    "Menü": "Menu",
    # Der erste Bildschirm eines neuen Betriebs
    "Noch keine Herde": "Aucune bande pour l'instant",
    "Der Taktgeber rechnet alles aus dem Einstalldatum: Impftermine, "
    "Futterwechsel, Verzehr und Mischauftrag. Ohne eine eingestallte Herde "
    "gibt es nichts zu takten.": (
        "Le Cadenceur calcule tout à partir de la date de mise en place : "
        "échéances de vaccination, transitions alimentaires, consommation et "
        "ordre de mélange. Sans bande mise en place, il n'y a rien à cadencer."
    ),
    "Auf dem Rechner, auf dem der Taktgeber läuft:": ("Sur la machine où tourne le Cadenceur :"),
    "Danach diese Seite neu laden. Welches Prophylaxe-Blatt gilt, lässt sich jederzeit wechseln.": (
        "Rechargez ensuite cette page. Le programme de prophylaxie qui "
        "s'applique peut être changé à tout moment."
    ),
    # Die Anmeldeseite erklärt, wofür man sich anmeldet.
    "Sagt jeden Tag, welche Impfung, Entwurmung oder Futterumstellung "
    "ansteht — gerechnet aus dem Einstalldatum.": (
        "Indique chaque jour quelle vaccination, quel déparasitage ou quelle "
        "transition alimentaire arrive — calculé à partir de la date de mise "
        "en place."
    ),
    "Rechnet den Mischauftrag und sperrt ihn, wenn das Rezept nicht aufgeht.": (
        "Calcule l'ordre de mélange et le bloque si la formule ne tombe pas juste."
    ),
    "Merkt sich, was abgehakt wurde, und meldet, was überfällig ist.": (
        "Retient ce qui a été coché et signale ce qui est en retard."
    ),
    "Der Plan entscheidet, nicht das Gefühl. Jeder Termin kommt aus einer "
    "Subtraktion, keiner aus einer Schätzung.": (
        "C'est le programme qui décide, pas l'impression. Chaque échéance vient "
        "d'une soustraction, aucune d'une estimation."
    ),
    "In den nächsten sieben Tagen steht nichts an.": (
        "Rien de prévu dans les sept prochains jours."
    ),
    # Das Band der öffentlichen Demo — sonst bliebe es als Einziges deutsch.
    "Demo mit erfundenen Betriebsdaten": "Démonstration avec des données inventées",
    "Eingaben bleiben im Browser, es wird nichts gespeichert.": (
        "Les saisies restent dans le navigateur, rien n'est enregistré."
    ),
    "Quelltext": "Code source",
    "Dosis": "Dosage",
    "Gegenüberstellung": "Comparaison",
    "Gegenüberstellen": "Comparer",
    "Übernehmen": "Appliquer",
    "Thema": "Sujet",
    "Links": "Gauche",
    "Rechts": "Droite",
    "bis": "jusqu'au",
    "Abgehakte Schritte bleiben abgehakt. Welches Blatt gilt, entscheidet der Betrieb.": (
        "Les étapes cochées le restent. C'est l'exploitation qui décide quel programme s'applique."
    ),
    "Gleich in beiden": "Identique dans les deux",
    "Welches Blatt gilt, entscheidet der Betrieb.": (
        "C'est l'exploitation qui décide quel programme s'applique."
    ),
    "Das Programm dieser Herde wurde gewechselt.": ("Le programme de cette bande a été changé."),
    "Nur die Leitung darf das Programm wechseln.": (
        "Seule la direction peut changer de programme."
    ),
    # Zustände
    "überfällig": "en retard",
    "jetzt dran": "à faire",
    "geplant": "prévu",
    "erledigt": "fait",
    # Formularfelder
    "Menge (kg)": "Quantité (kg)",
    "Bei Überhang": "En cas d'excédent",
    # Kurz, weil die Auswahl im Feld lesbar bleiben muss — welcher Posten
    # ausgeglichen wird, steht im Ergebnis („Ausgeglichen über MAIS …“).
    "ausgleichen": "compenser",
    "wie im Blatt": "comme sur la fiche",
    "anteilig skalieren": "mettre à l'échelle",
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
    # Rückmeldungen und zusammengesetzte Zeilen
    "Als geprüft abgehakt.": "Marqué comme vérifié.",
    "Anlegen mit:": "Créer avec :",
    "Charge": "Lot",
    "Das hat nicht geklappt:": "Échec :",
    "Eingaben noch nicht beim Server": "saisie(s) pas encore sur le serveur",
    "Eingaben warten": "saisie(s) en attente",
    "Gebucht — der Futterbedarf rechnet ab jetzt damit.": (
        "Enregistré — le besoin en aliment en tient compte."
    ),
    "Ist-Einwaage": "Pesée réelle",
    "Kein Netz": "Pas de réseau",
    "Kein Rezept für diese Linie.": "Aucune formule pour cette lignée.",
    "Mischung protokolliert.": "Mélange enregistré.",
    "Nicht abgehakt:": "Non validé :",
    "Nicht aufgenommen:": "Non enregistré :",
    "Nicht gebucht.": "Non enregistré.",
    "Nicht gebucht:": "Non enregistré :",
    "Noch keine Herde für diesen Betrieb.": ("Aucune bande pour cette exploitation."),
    "Rohstoff": "Matière première",
    "Unbekannter Fehler": "Erreur inconnue",
    "Version": "Version",
    "Vorfall aufgenommen — das Schema steht im Plan.": (
        "Incident enregistré — le protocole est au planning."
    ),
    "Wie viele Tiere?": "Combien d'animaux ?",
    "abgehakt — wird nachgereicht.": "validé — sera envoyé plus tard.",
    "abgehakt.": "validé.",
    "erledigt am": "fait le",
    "frei ab": "libre à partir du",
    "letzte Gabe": "dernière administration",
    "Anmeldung fehlgeschlagen.": "Échec de la connexion.",
    # Einrichtungsseite
    "Noch kein Benutzer angelegt": "Aucun utilisateur créé",
    "Ohne Benutzer gibt es keine Anmeldung und damit keinen Zugang. Den ersten "
    "legst du auf dem Rechner an, auf dem der Taktgeber läuft:": (
        "Sans utilisateur, pas de connexion et donc pas d'accès. Créez le premier "
        "sur la machine où tourne le Cadenceur :"
    ),
    "Das Passwort wird dabei abgefragt und steht nicht in der Kommandozeile. "
    "Danach diese Seite neu laden.": (
        "Le mot de passe est demandé et n'apparaît pas dans la ligne de commande. "
        "Rechargez ensuite cette page."
    ),
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
