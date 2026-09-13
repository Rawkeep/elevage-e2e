"""Kommandozeile — dünne Schale über `takt.rechne()`, keine eigene Logik."""

from __future__ import annotations

import argparse
from datetime import date, datetime

from elevage.mischung import baue_mischauftrag
from elevage.models import Ampel, Herde, Mischauftrag, Quittung, Tagesbild, Termin, Tierart
from elevage.rezepte import REZEPTE, rezept_nach_key
from elevage.takt import mischauftrag_fuer, rechne

ERLEDIGT_AB_TAGEN = 10
"""Nur in der Demo: was länger als so lange zurückliegt, gilt als abgehakt."""

SYMBOL = {
    Ampel.ROT: "[!]",
    Ampel.GELB: "[>]",
    Ampel.GRUEN: "[ ]",
    Ampel.ERLEDIGT: "[x]",
}


def _datum(text: str) -> date:
    return datetime.strptime(text, "%Y-%m-%d").date()


def _zeile(t: Termin) -> str:
    fenster = (
        f"{t.faellig_von:%d.%m.}"
        if t.faellig_von == t.faellig_bis
        else f"{t.faellig_von:%d.%m.}-{t.faellig_bis:%d.%m.}"
    )
    mittel = f" — {' / '.join(t.praeparate)}" if t.praeparate else ""
    return f"  {SYMBOL[t.ampel]} {fenster:>13s}  {t.titel}{mittel}"


def zeige_tagesbild(bild: Tagesbild) -> None:
    h = bild.herde
    print(f"\n{h.name} · {h.tierart.value} · {h.tierzahl} Tiere")
    print(
        f"Stichtag {bild.stichtag:%d.%m.%Y} · Tag {bild.alter_tage} "
        f"· Woche {bild.alter_wochen} · Gesamtlage {bild.ampel.value}"
    )
    print(f"Futterphase: {bild.phase.name if bild.phase else '— kein Blatt vorhanden'}")

    for titel, liste in (
        ("ÜBERFÄLLIG", bild.ueberfaellig),
        ("JETZT DRAN", bild.heute),
        ("DEMNÄCHST", bild.demnaechst),
        ("BESTELLEN (Vorlauf)", bild.bestellen),
        ("ERLEDIGT (letzte 5)", bild.erledigt[-5:]),
    ):
        if liste:
            print(f"\n{titel}")
            for t in liste:
                print(_zeile(t))
                if t.hinweis:
                    print(f"        Hinweis: {t.hinweis}")

    if bild.issues:
        print("\nBEFUNDE (gemeldet, nicht stillschweigend repariert)")
        for i in bild.issues:
            print(f"  · {i}")


def zeige_mischauftrag(auftrag: Mischauftrag) -> None:
    print(f"\nMISCHAUFTRAG · {auftrag.rezept_name} · Ziel {auftrag.ziel_kg:.0f} kg")
    for z in auftrag.zeilen:
        print(f"  {z.kg:9.2f} kg  {z.name}")
    print(f"  {'-' * 9}")
    print(f"  {auftrag.ist_einwaage_kg:9.2f} kg  Ist-Einwaage")
    print(f"  Freigabe: {'JA' if auftrag.freigegeben else 'NEIN'}")
    for i in auftrag.issues:
        print(f"  · {i}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="elevage", description="Taktgeber für den Betrieb")
    unter = p.add_subparsers(dest="befehl", required=True)

    tb = unter.add_parser("tagesbild", help="Was ist heute zu tun?")
    tb.add_argument("--tierart", choices=[t.value for t in Tierart], required=True)
    tb.add_argument("--einstall", type=_datum, required=True)
    tb.add_argument("--stichtag", type=_datum, required=True)
    tb.add_argument("--tiere", type=int, default=1000)
    tb.add_argument("--name", default="Stall 1")
    tb.add_argument("--hoher-virusdruck", action="store_true")
    tb.add_argument("--spaete-schlachtung", action="store_true")
    tb.add_argument("--mischen", type=float, help="Mischauftrag über N kg mitdrucken")
    tb.add_argument("--normieren", action="store_true")

    mi = unter.add_parser("mischung", help="Waage-Liste für ein Rezept")
    mi.add_argument("--rezept", choices=[r.key for r in REZEPTE], required=True)
    mi.add_argument("--kg", type=float, required=True)
    mi.add_argument("--normieren", action="store_true")

    unter.add_parser("demo", help="Drei Szenarien ohne Eingaben")

    a = p.parse_args(argv)

    if a.befehl == "mischung":
        zeige_mischauftrag(
            baue_mischauftrag(rezept_nach_key(a.rezept), a.kg, normieren=a.normieren)
        )
        return 0

    if a.befehl == "demo":
        return _demo()

    herde = Herde(
        tenant_id="demo",
        herde_id="H1",
        name=a.name,
        tierart=Tierart(a.tierart),
        einstalldatum=a.einstall,
        tierzahl=a.tiere,
        hoher_virusdruck=a.hoher_virusdruck,
        spaete_schlachtung=a.spaete_schlachtung,
    )
    bild = rechne(herde, a.stichtag)
    zeige_tagesbild(bild)
    if a.mischen:
        auftrag = mischauftrag_fuer(bild, a.mischen, normieren=a.normieren)
        if auftrag is None:
            print("\nKein Mischauftrag: für diese Linie liegt kein Futterblatt vor.")
        else:
            zeige_mischauftrag(auftrag)
    return 0 if bild.ampel is not Ampel.ROT else 2


def _demo() -> int:
    faelle = [
        ("Junghenne in Woche 2", Tierart.LEGEHENNE, date(2026, 3, 2), date(2026, 3, 13), None),
        ("Masthuhn an Tag 13", Tierart.MASTHUHN, date(2026, 3, 2), date(2026, 3, 14), None),
        ("Legehenne in der Ponte", Tierart.LEGEHENNE, date(2025, 9, 1), date(2026, 3, 20), 1000.0),
    ]
    for titel, art, einstall, stichtag, mischen in faelle:
        print("=" * 72)
        print(titel)
        herde = Herde(
            tenant_id="demo",
            herde_id="H1",
            name=titel,
            tierart=art,
            einstalldatum=einstall,
            tierzahl=1000,
        )
        # Im laufenden Betrieb ist das Alte abgehakt — sonst zeigt die Demo
        # nur eine Wand aus Überfälligem und nicht, was der Taktgeber leistet.
        vorlauf_bild = rechne(herde, stichtag)
        quittungen = [
            Quittung(
                tenant_id=herde.tenant_id,
                herde_id=herde.herde_id,
                schritt_key=t.schritt_key,
                quittung_id=f"demo-{t.schritt_key}",
                erledigt_am=t.faellig_von,
            )
            for t in vorlauf_bild.ueberfaellig
            if (stichtag - t.faellig_bis).days > ERLEDIGT_AB_TAGEN
        ]
        bild = rechne(herde, stichtag, quittungen)
        zeige_tagesbild(bild)
        if mischen:
            auftrag = mischauftrag_fuer(bild, mischen)
            if auftrag:
                zeige_mischauftrag(auftrag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
