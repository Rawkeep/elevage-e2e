"""Kommandozeile — dünne Schale über `takt.rechne()`, keine eigene Logik."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path

from elevage import archiv, betrieb
from elevage.mischung import baue_mischauftrag
from elevage.models import (
    Ampel,
    Ereignis,
    EreignisArt,
    Herde,
    Mischauftrag,
    Quittung,
    Tagesbild,
    Termin,
    Tierart,
)
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
    print(f"\n{h.name} · {h.tierart.value} · {h.tierzahl} Tiere · {h.herde_id}")
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
                if t.ampel is Ampel.ERLEDIGT and t.lot:
                    print(f"        Charge: {t.lot}")

    f = bild.futter
    if f and f.bedarf_je_tag_kg is not None:
        herkunft = "gemessen" if f.quelle and f.quelle.value == "GEMESSEN" else "Richtwert"
        print(
            f"\nFUTTER · {f.gramm_je_tier_tag:.0f} g/Tier/Tag ({herkunft}) "
            f"· {f.bedarf_je_tag_kg:.1f} kg/Tag "
            f"· {f.bedarf_bis_horizont_kg:.0f} kg für {f.horizont_tage} Tage"
        )
        if f.vorrat_kg is not None and f.reicht_bis:
            print(
                f"  Vorrat {f.vorrat_kg:.0f} kg reicht bis {f.reicht_bis:%d.%m.} "
                f"· bestellen ab {f.bestellen_ab:%d.%m.}"
            )

    if bild.vorfaelle:
        print("\nVORFÄLLE")
        for v in bild.vorfaelle:
            zusatz = f" — {v.bemerkung}" if v.bemerkung else ""
            print(f"  {v.festgestellt_am:%d.%m.%Y}  {v.art.value}{zusatz}")

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


def _bauplan(p: argparse.ArgumentParser) -> None:
    p.add_argument("--db", type=Path, help="Pfad zur SQLite-Datei (Vorgabe: ~/.elevage)")
    p.add_argument("--betrieb", default="standard", help="Mandant (tenant_id)")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="elevage", description="Taktgeber für den Betrieb")
    unter = p.add_subparsers(dest="befehl", required=True)

    an = unter.add_parser("einstallen", help="Herde anlegen oder ändern")
    _bauplan(an)
    an.add_argument("--herde", required=True, help="Kurzzeichen, z. B. H1")
    an.add_argument("--name", required=True)
    an.add_argument("--tierart", choices=[t.value for t in Tierart], required=True)
    an.add_argument("--einstall", type=_datum, required=True)
    an.add_argument("--tiere", type=int, required=True)
    an.add_argument("--hoher-virusdruck", action="store_true")
    an.add_argument("--spaete-schlachtung", action="store_true")

    aus = unter.add_parser("ausstallen", help="Herde stilllegen (Historie bleibt)")
    _bauplan(aus)
    aus.add_argument("--herde", required=True)

    li = unter.add_parser("herden", help="Herden des Betriebs")
    _bauplan(li)
    li.add_argument("--alle", action="store_true", help="auch ausgestallte")

    tb = unter.add_parser("tagesbild", help="Was ist heute zu tun?")
    _bauplan(tb)
    tb.add_argument("--herde", required=True)
    tb.add_argument("--stichtag", type=_datum, required=True)
    tb.add_argument("--mischen", type=float, help="Mischauftrag über N kg mitdrucken")
    tb.add_argument("--vorrat", type=float, help="Futtervorrat in kg — ergibt die Reichweite")
    tb.add_argument("--normieren", action="store_true")

    qu = unter.add_parser("quittieren", help="Einen Schritt abhaken")
    _bauplan(qu)
    qu.add_argument("--herde", required=True)
    qu.add_argument("--schritt", required=True, help="Schlüssel aus dem Tagesbild")
    qu.add_argument("--am", type=_datum, required=True)
    qu.add_argument("--durch", default="")
    qu.add_argument("--lot")
    qu.add_argument("--bemerkung")
    qu.add_argument("--id", help="Ereignis-Nummer (Vorgabe: aus Herde/Schritt/Datum)")

    vo = unter.add_parser("vorfall", help="Einen Vorfall melden (löst das Schema aus)")
    _bauplan(vo)
    vo.add_argument("--herde", required=True)
    vo.add_argument("--art", choices=[a.value for a in EreignisArt], default="GUMBORO")
    vo.add_argument("--am", type=_datum, required=True)
    vo.add_argument("--bemerkung")
    vo.add_argument("--id", help="Vorgangsnummer (Vorgabe: aus Herde/Art/Datum)")

    ge = unter.add_parser("gemischt", help="Eine Mischung protokollieren")
    _bauplan(ge)
    ge.add_argument("--herde", required=True)
    ge.add_argument("--kg", type=float, required=True)
    ge.add_argument("--am", type=_datum, required=True)
    ge.add_argument("--normieren", action="store_true")
    ge.add_argument("--nummer", help="Protokollnummer (Vorgabe: aus Herde/Datum)")

    ku = unter.add_parser("verzehr", help="Die Verzehrkurve dieser Herde")
    _bauplan(ku)
    ku.add_argument("--herde", required=True)

    mi = unter.add_parser("mischung", help="Waage-Liste für ein Rezept")
    mi.add_argument("--rezept", choices=[r.key for r in REZEPTE], required=True)
    mi.add_argument("--kg", type=float, required=True)
    mi.add_argument("--normieren", action="store_true")

    unter.add_parser("demo", help="Drei Szenarien ohne Datenbank")

    a = p.parse_args(argv)

    if a.befehl == "mischung":
        zeige_mischauftrag(
            baue_mischauftrag(rezept_nach_key(a.rezept), a.kg, normieren=a.normieren)
        )
        return 0
    if a.befehl == "demo":
        return _demo()

    with archiv.oeffne(a.db) as conn:
        if a.befehl == "einstallen":
            herde = Herde(
                tenant_id=a.betrieb,
                herde_id=a.herde,
                name=a.name,
                tierart=Tierart(a.tierart),
                einstalldatum=a.einstall,
                tierzahl=a.tiere,
                hoher_virusdruck=a.hoher_virusdruck,
                spaete_schlachtung=a.spaete_schlachtung,
            )
            archiv.speichere_herde(conn, herde)
            print(f"Eingestallt: {herde.name} ({herde.herde_id}) ab {herde.einstalldatum}")
            return 0

        if a.befehl == "ausstallen":
            archiv.stalle_aus(conn, a.betrieb, a.herde)
            print(f"Ausgestallt: {a.herde} — Historie bleibt erhalten.")
            return 0

        if a.befehl == "herden":
            herden = archiv.liste_herden(conn, a.betrieb, nur_aktive=not a.alle)
            if not herden:
                print("Keine Herden. Anlegen mit 'elevage einstallen'.")
                return 0
            for h in herden:
                print(
                    f"  {h.herde_id:6s} {h.name:24s} {h.tierart.value:10s} "
                    f"ab {h.einstalldatum}  {h.tierzahl:6d} Tiere"
                )
            return 0

        if a.befehl == "quittieren":
            bekannt = archiv.lade_herde(conn, a.betrieb, a.herde)
            if bekannt is None:
                print(f"Unbekannte Herde: {a.herde}")
                return 1
            quittung = Quittung(
                tenant_id=a.betrieb,
                herde_id=a.herde,
                schritt_key=a.schritt,
                quittung_id=a.id or f"{a.herde}:{a.schritt}:{a.am.isoformat()}",
                erledigt_am=a.am,
                durch=a.durch,
                lot=a.lot,
                bemerkung=a.bemerkung,
            )
            neu = archiv.quittiere(conn, quittung)
            print("Quittiert." if neu else "Lag bereits vor — nichts geändert.")
            return 0

        if a.befehl == "vorfall":
            ereignis = Ereignis(
                tenant_id=a.betrieb,
                herde_id=a.herde,
                ereignis_id=a.id or f"{a.herde}:{a.art}:{a.am.isoformat()}",
                art=EreignisArt(a.art),
                festgestellt_am=a.am,
                bemerkung=a.bemerkung,
            )
            neu = archiv.melde_ereignis(conn, ereignis)
            print(
                f"Vorfall {ereignis.art.value} vom {ereignis.festgestellt_am} "
                + (
                    "aufgenommen — das Schema steht ab sofort im Tagesbild."
                    if neu
                    else "lag bereits vor — nichts geändert."
                )
            )
            return 0

        if a.befehl == "gemischt":
            bild = betrieb.tagesbild(conn, a.betrieb, a.herde, a.am)
            auftrag = mischauftrag_fuer(bild, a.kg, normieren=a.normieren)
            if auftrag is None:
                print("Kein Rezept für diese Linie — nichts zu protokollieren.")
                return 1
            zeige_mischauftrag(auftrag)
            if not auftrag.freigegeben:
                print("\nNicht protokolliert: der Auftrag ist gesperrt.")
                return 2
            archiv.protokolliere_mischung(
                conn,
                a.betrieb,
                a.nummer or f"{a.herde}:{a.am.isoformat()}",
                a.herde,
                a.am,
                auftrag,
            )
            print("\nProtokolliert — die Verzehrkurve rechnet das ab jetzt mit.")
            return 0

        if a.befehl == "verzehr":
            kurve, issues = betrieb.verzehrkurve(conn, a.betrieb, a.herde)
            print(f"Verzehrkurve {a.herde} ({kurve.tierart.value})")
            for punkt in kurve.punkte:
                marke = "gemessen " if punkt.quelle.value == "GEMESSEN" else "Richtwert"
                print(
                    f"  Woche {punkt.woche:3d}  {punkt.gramm_je_tier_tag:6.1f} g/Tier/Tag"
                    f"  {marke}  {punkt.basis or ''}"
                )
            for i in issues:
                print(f"  · {i}")
            return 0

        gewaehlt = archiv.lade_herde(conn, a.betrieb, a.herde)
        if gewaehlt is None:
            print(f"Unbekannte Herde: {a.herde}")
            return 1
        bild = betrieb.tagesbild(conn, a.betrieb, a.herde, a.stichtag, vorrat_kg=a.vorrat)
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
        vorlauf = rechne(herde, stichtag)
        quittungen = [
            Quittung(
                tenant_id=herde.tenant_id,
                herde_id=herde.herde_id,
                schritt_key=t.schritt_key,
                quittung_id=f"demo-{t.schritt_key}",
                erledigt_am=t.faellig_von,
            )
            for t in vorlauf.ueberfaellig
            if (stichtag - t.faellig_bis).days > ERLEDIGT_AB_TAGEN
        ]
        bild = rechne(herde, stichtag, quittungen)
        zeige_tagesbild(bild)
        if mischen:
            auftrag = mischauftrag_fuer(bild, mischen)
            if auftrag:
                zeige_mischauftrag(auftrag)
    return 0


def _starte() -> int:
    """`elevage ... | head` soll nicht mit einem Stacktrace enden."""
    try:
        return main()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0


if __name__ == "__main__":
    raise SystemExit(_starte())
