"""Wartezeiten: ab wann nach einer Behandlung wieder vermarktet werden darf.

**Die Zahl kommt von der Packung, nicht aus diesem Programm.** Es gibt hier
keine Tabelle mit Wartezeiten, weil sie vom Präparat, von der Dosis und vom
Zulassungsland abhängt — eine erfundene Zahl wäre schlimmer als gar keine.
Der Betrieb trägt sie einmal je Mittel ein, dieses Modul rechnet daraus das
Freigabedatum.

Drei Regeln, die nicht verhandelbar sind:

1. **Unbekannt ist nicht null.** Ein Mittel ohne hinterlegte Wartezeit
   erzeugt einen Befund, keine Freigabe.
2. **Ohne festgehaltenes Präparat gibt es keine Rechnung.** Die Programme
   nennen je Schritt mehrere Alternativen; welche gegeben wurde, weiß nur,
   wer sie gegeben hat. Fehlt die Angabe, wird das gemeldet.
3. **Die Frist läuft ab der letzten Gabe.** Bei einem mehrtägigen Schritt
   ist das nicht der Quittungstag, sondern das Ende des Behandlungsfensters,
   sofern es später liegt.

Welche Konvention der Beipackzettel genau meint (Tag der letzten Gabe
mitzählen oder nicht), steht dort und nicht hier — `freigabe_ab` ist der
erste Tag, an dem wieder vermarktet werden darf, wenn die Wartezeit als
volle Tage nach der letzten Gabe gelesen wird.
"""

from __future__ import annotations

from datetime import date, timedelta

from elevage.models import (
    Befund,
    Erzeugnis,
    Herde,
    Kategorie,
    Praeparat,
    Quittung,
    Schritt,
    Sperrfenster,
    Tierart,
    befund,
)

WARTEZEIT_RELEVANT = {
    Kategorie.MEDIKATION,
    Kategorie.ANTIKOKZIDIUM,
    Kategorie.ENTWURMUNG,
    Kategorie.IMPFUNG,
}
"""Kategorien, bei denen eine Wartezeit zu klären ist.

Impfungen stehen bewusst mit drin: die meisten Lebendimpfstoffe haben keine,
manche inaktivierten schon — und „meistens keine" ist kein Grund, gar nicht
erst zu fragen. Vitamine, Hygiene und Handgriffe bleiben draußen."""

ERZEUGNIS_JE_TIERART = {
    Tierart.LEGEHENNE: Erzeugnis.EIER,
    Tierart.MASTHUHN: Erzeugnis.FLEISCH,
}


def praeparat_id(name: str) -> str:
    """Ein Mittel, eine Nummer — Groß-/Kleinschreibung und Beiwerk egal."""
    return "".join(z for z in name.upper() if z.isalnum())


def _wartezeit(praeparat: Praeparat, erzeugnis: Erzeugnis) -> int | None:
    if erzeugnis is Erzeugnis.EIER:
        return praeparat.wartezeit_eier_tage
    return praeparat.wartezeit_fleisch_tage


def berechne_sperren(
    herde: Herde,
    stichtag: date,
    quittungen: list[Quittung],
    schritte: list[Schritt],
    praeparate: list[Praeparat],
) -> tuple[list[Sperrfenster], list[Befund]]:
    """Offene und abgelaufene Sperren plus die Befunde, die dabei auffallen."""
    erzeugnis = ERZEUGNIS_JE_TIERART[herde.tierart]
    nach_key = {s.key: s for s in schritte}
    stamm = {p.praeparat_id: p for p in praeparate}

    sperren: list[Sperrfenster] = []
    issues: list[Befund] = []
    ohne_angabe: list[str] = []
    ohne_zahl: set[str] = set()

    for quittung in quittungen:
        if quittung.herde_id != herde.herde_id or quittung.tenant_id != herde.tenant_id:
            continue
        schritt = nach_key.get(quittung.schritt_key)
        if schritt is None or schritt.kategorie not in WARTEZEIT_RELEVANT:
            continue

        if not quittung.praeparat:
            ohne_angabe.append(schritt.titel)
            continue

        gefunden = stamm.get(praeparat_id(quittung.praeparat))
        tage = _wartezeit(gefunden, erzeugnis) if gefunden else None
        if tage is None:
            ohne_zahl.add(quittung.praeparat)
            continue

        # Die Frist läuft ab der letzten Gabe, nicht ab dem Abhaken.
        letzte_gabe = max(
            quittung.erledigt_am,
            herde.einstalldatum + timedelta(days=schritt.bis_tag - 1),
        )
        freigabe = letzte_gabe + timedelta(days=tage)
        sperren.append(
            Sperrfenster(
                erzeugnis=erzeugnis,
                herde_id=herde.herde_id,
                praeparat=quittung.praeparat,
                schritt_key=schritt.key,
                letzte_gabe=letzte_gabe,
                wartezeit_tage=tage,
                freigabe_ab=freigabe,
                laeuft_noch=stichtag < freigabe,
            )
        )

    if ohne_angabe:
        issues.append(
            befund(
                f"{len(ohne_angabe)} abgehakte Behandlung(en) ohne Angabe, welches Mittel "
                "gegeben wurde — ohne das lässt sich keine Wartezeit rechnen "
                f"(z. B. „{ohne_angabe[0]}“).",
                f"{len(ohne_angabe)} traitement(s) coché(s) sans indication du produit "
                "administré — sans elle, aucun délai d'attente n'est calculable "
                f"(p. ex. « {ohne_angabe[0]} »).",
            )
        )
    for name in sorted(ohne_zahl):
        issues.append(
            befund(
                f"Für „{name}“ ist keine Wartezeit hinterlegt. Unbekannt ist nicht null — "
                "die Zahl steht auf der Packung: 'elevage praeparat' trägt sie ein.",
                f"Aucun délai d'attente enregistré pour « {name} ». Inconnu ne veut pas "
                "dire zéro — le chiffre est sur l'emballage : 'elevage praeparat' "
                "le saisit.",
            )
        )
    sperren.sort(key=lambda s: s.freigabe_ab)
    return sperren, issues


def offene(sperren: list[Sperrfenster]) -> list[Sperrfenster]:
    return [s for s in sperren if s.laeuft_noch]


def freigabe_ab(sperren: list[Sperrfenster]) -> date | None:
    """Der späteste Tag aller laufenden Sperren — vorher geht gar nichts."""
    laufend = offene(sperren)
    return max((s.freigabe_ab for s in laufend), default=None)
