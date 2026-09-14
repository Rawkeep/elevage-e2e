"""Kommandozeile — dünne Schale über `takt.rechne()`, keine eigene Logik."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from getpass import getpass
from pathlib import Path

from elevage import archiv, betrieb
from elevage.anmeldung import PasswortZuKurz, hashe_passwort
from elevage.anpassung import normiere_artikel
from elevage.einstellung import BEKANNT
from elevage.mischung import baue_mischauftrag
from elevage.models import (
    OFFENES_ENDE,
    Abgangsgrund,
    Ampel,
    Ausgleichsart,
    Benutzer,
    Bestandsbewegung,
    Ereignis,
    EreignisArt,
    Herde,
    Herkunft,
    Mischauftrag,
    Praeparat,
    Programm,
    Programmvergleich,
    Quittung,
    Rezept,
    Rezeptanpassung,
    Rolle,
    Tagesbild,
    Termin,
    Tierart,
    Tierarzt,
)
from elevage.programme import alle_programme, programm, programm_konflikt
from elevage.rezepte import REZEPTE, rezept_nach_key
from elevage.server import STANDARD_PORT, laufe
from elevage.takt import mischauftrag_fuer, rechne
from elevage.vergleich import vergleiche
from elevage.wartezeit import praeparat_id

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
    im_stall = bild.bestand.tierzahl if bild.bestand else h.tierzahl
    verluste = (
        f" (von {h.tierzahl}, −{bild.bestand.verluste_prozent:.1f} %)"
        if (bild.bestand and bild.bestand.abgang_gesamt)
        else ""
    )
    print(f"\n{h.name} · {h.tierart.value} · {im_stall} Tiere{verluste} · {h.herde_id}")
    print(
        f"Stichtag {bild.stichtag:%d.%m.%Y} · Tag {bild.alter_tage} "
        f"· Woche {bild.alter_wochen} · Gesamtlage {bild.ampel.value}"
    )
    print(f"Programm: {bild.programm_titel}")
    print(f"Futterphase: {bild.phase.name if bild.phase else '— kein Blatt vorhanden'}")
    for r in bild.ruhe:
        print(f"RUHE: {r.titel} (bis {r.faellig_bis:%d.%m.})")

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

    laufend = [s for s in bild.sperren if s.laeuft_noch]
    if laufend:
        erzeugnis = laufend[0].erzeugnis.value.capitalize()
        spaeteste = max(s.freigabe_ab for s in laufend)
        print(f"\nWARTEZEIT — {erzeugnis} gesperrt bis {spaeteste:%d.%m.%Y}")
        for sp in laufend:
            print(
                f"  {sp.praeparat} · letzte Gabe {sp.letzte_gabe:%d.%m.} "
                f"· {sp.wartezeit_tage} Tage · frei ab {sp.freigabe_ab:%d.%m.}"
            )

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

    if bild.tierarzt:
        kontakt = " · ".join(x for x in (bild.tierarzt.telefon, bild.tierarzt.email) if x)
        print(f"\nTIERARZT: {bild.tierarzt.name}" + (f" · {kontakt}" if kontakt else ""))


def zeige_programm(blatt: Programm) -> None:
    """Ein Blatt, wie es auf dem Papier steht — Schritte, Dauer, Merksätze."""
    print(f"\n{blatt.titel}  [{blatt.programm_id}]")
    if blatt.herausgeber:
        print(f"Herausgeber: {blatt.herausgeber}")
    print(f"{len(blatt.schritte)} Schritte · {len(blatt.dauerregeln)} Dauerregeln")
    for s in sorted(blatt.schritte, key=lambda x: (x.von_tag, x.key)):
        fenster = (
            f"ab J{s.von_tag}"
            if s.bis_tag >= OFFENES_ENDE
            else (f"J{s.von_tag}" if s.von_tag == s.bis_tag else f"J{s.von_tag}-J{s.bis_tag}")
        )
        mittel = f" — {' / '.join(s.praeparate)}" if s.praeparate else ""
        print(f"  {fenster:>12s}  {s.kategorie.value:<14s} {s.titel}{mittel}")
        if s.dosis_je_liter:
            print(f"                Dosis: {s.dosis_je_liter}")
    for r in blatt.dauerregeln:
        ab = f" ab J{r.ab_tag}" if r.ab_tag is not None else " ab der Legephase"
        print(f"  alle {r.intervall_tage:>4d} d  {r.kategorie.value:<14s} {r.titel}{ab}")
    if blatt.hinweise:
        print("\nMERKSÄTZE DES BLATTES")
        for h in blatt.hinweise:
            print(f"  · {h}")


def zeige_vergleich(v: Programmvergleich) -> None:
    """Die Gegenüberstellung — Unterschiede zuerst, Gleiches am Ende."""
    print(f"\n{v.links_titel}   ←→   {v.rechts_titel}")
    print(f"{'THEMA':<34s} {'LINKS':<34s} RECHTS")
    for z in v.zeilen:
        if z.gleich:
            continue
        print(f"{z.thema[:33]:<34s} {(z.links or '—')[:33]:<34s} {z.rechts or '—'}")
    gleich = [z.thema for z in v.zeilen if z.gleich]
    if gleich:
        print(f"\nGLEICH IN BEIDEN: {', '.join(gleich)}")
    if v.issues:
        print("\nBEFUNDE (gemeldet, nicht stillschweigend geglättet)")
        for i in v.issues:
            print(f"  · {i}")
    print("\nWelches Blatt gilt, entscheidet der Betrieb — mit 'elevage programm --herde X")
    print("--waehlen KENNUNG' wird die Wahl je Herde gesetzt.")


def zeige_rezept(rezept: Rezept) -> None:
    print(f"\n{rezept.name} ({rezept.key}) · Quelle: {rezept.quelle}")
    for p in rezept.posten:
        herkunft = "Betrieb " if p.herkunft is Herkunft.BETRIEB else "Blatt   "
        vorher = f"  (Blatt: {p.blatt_kg_je_100:.2f})" if p.blatt_kg_je_100 is not None else ""
        entfaellt = "  ENTFÄLLT" if p.kg_je_100 == 0 else ""
        print(
            f"  {p.artikel_id:16s} {p.kg_je_100:7.2f} kg/100kg  {herkunft}"
            f"{p.name}{vorher}{entfaellt}"
        )
    delta = rezept.summe_je_100 - 100.0
    print(f"  {'SUMME':16s} {rezept.summe_je_100:7.2f} kg/100kg  ({delta:+.2f})")


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
    an.add_argument(
        "--programm",
        choices=[x.programm_id for x in alle_programme()],
        help="Prophylaxe-Blatt (Vorgabe: das der Tierart)",
    )

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
    tb.add_argument("--art", choices=[x.value for x in Ausgleichsart], default=None)

    qu = unter.add_parser("quittieren", help="Einen Schritt abhaken")
    _bauplan(qu)
    qu.add_argument("--herde", required=True)
    qu.add_argument("--schritt", required=True, help="Schlüssel aus dem Tagesbild")
    qu.add_argument("--am", type=_datum, required=True)
    qu.add_argument("--durch", default="")
    qu.add_argument("--praeparat", help="welches Mittel gegeben wurde (für die Wartezeit)")
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
    ge.add_argument("--art", choices=[x.value for x in Ausgleichsart], default=None)
    ge.add_argument("--nummer", help="Protokollnummer (Vorgabe: aus Herde/Datum)")

    rz = unter.add_parser("rezept", help="Rezept anzeigen und Mengen anpassen")
    _bauplan(rz)
    rz.add_argument("--rezept", choices=[r.key for r in REZEPTE], required=True)
    rz.add_argument("--artikel", help="Artikelnummer, z. B. MAIS")
    rz.add_argument("--kg", type=float, help="Menge je 100 kg; 0 = Posten entfällt")
    rz.add_argument("--grund")
    rz.add_argument("--am", type=_datum, help="Änderungsdatum (Vorgabe: --am nötig)")
    rz.add_argument("--zuruecksetzen", action="store_true", help="zurück zum Blattwert")

    es = unter.add_parser("einstellung", help="Einstellungen des Betriebs")
    _bauplan(es)
    es.add_argument("--schluessel", choices=sorted(BEKANNT))
    es.add_argument("--wert", help="ohne --wert: zurück auf den Blattwert")

    ab = unter.add_parser("abgang", help="Verluste und Abgänge buchen")
    _bauplan(ab)
    ab.add_argument("--herde", required=True)
    ab.add_argument("--tiere", type=int, required=True, help="Anzahl Abgang")
    ab.add_argument("--am", type=_datum, required=True)
    ab.add_argument(
        "--grund", choices=[g.value for g in Abgangsgrund], default=Abgangsgrund.VERENDET.value
    )
    ab.add_argument("--bemerkung")
    ab.add_argument("--nummer", help="Belegnummer (Vorgabe: aus Herde/Datum/Grund)")

    pr = unter.add_parser("praeparat", help="Mittel und ihre Wartezeiten")
    _bauplan(pr)
    pr.add_argument("--anlegen", metavar="NAME")
    pr.add_argument("--eier", type=int, help="Wartezeit für Eier in Tagen")
    pr.add_argument("--fleisch", type=int, help="Wartezeit für Fleisch in Tagen")
    pr.add_argument("--quelle", help="woher die Zahl stammt, z. B. Beipackzettel")
    pr.add_argument("--hinweis")

    pv = unter.add_parser("pruefliste", help="Offene Prüfvermerke")
    _bauplan(pv)
    pv.add_argument("--alle", action="store_true")
    pv.add_argument("--abhaken", help="Vermerk-Nummer")
    pv.add_argument("--am", type=_datum)
    pv.add_argument("--durch", default="")

    ku = unter.add_parser("verzehr", help="Die Verzehrkurve dieser Herde")
    _bauplan(ku)
    ku.add_argument("--herde", required=True)

    mi = unter.add_parser("mischung", help="Waage-Liste für ein Rezept")
    mi.add_argument("--rezept", choices=[r.key for r in REZEPTE], required=True)
    mi.add_argument("--kg", type=float, required=True)
    mi.add_argument(
        "--art",
        choices=[x.value for x in Ausgleichsart],
        default=Ausgleichsart.AUSGLEICH.value,
        help="wie mit einem Überhang umgegangen wird",
    )

    bu = unter.add_parser("benutzer", help="Benutzer anlegen, sperren, auflisten")
    _bauplan(bu)
    bu.add_argument("--anlegen", metavar="ANMELDENAME")
    bu.add_argument("--name", help="Klarname der Person")
    bu.add_argument("--rolle", choices=[r.value for r in Rolle], default=Rolle.STALL.value)
    bu.add_argument("--sperren", metavar="ANMELDENAME")
    bu.add_argument("--passwort", metavar="ANMELDENAME", help="Passwort neu setzen")
    bu.add_argument("--am", type=_datum, help="Anlagedatum (Vorgabe: heute)")

    pg = unter.add_parser("programm", help="Prophylaxe-Blätter: zeigen, wählen, vergleichen")
    _bauplan(pg)
    pg.add_argument("--herde", help="Blatt dieser Herde wechseln")
    pg.add_argument(
        "--waehlen",
        choices=[x.programm_id for x in alle_programme()],
        help="Kennung des Blattes; ohne Angabe zurück auf die Vorgabe",
    )
    pg.add_argument("--zeigen", choices=[x.programm_id for x in alle_programme()])
    pg.add_argument(
        "--vergleich",
        nargs=2,
        metavar=("LINKS", "RECHTS"),
        help="zwei Kennungen gegenüberstellen",
    )

    ta = unter.add_parser("tierarzt", help="Den Tierarzt des Betriebs hinterlegen")
    _bauplan(ta)
    ta.add_argument("--name", help="Klarname, z. B. Dr. BANGUE")
    ta.add_argument("--praxis")
    ta.add_argument("--telefon")
    ta.add_argument("--email")
    ta.add_argument("--hinweis")

    ui = unter.add_parser("ui", help="Lokale Oberfläche starten")
    ui.add_argument("--db", type=Path)
    ui.add_argument("--port", type=int, default=STANDARD_PORT)
    ui.add_argument("--host", default=None, help="nur mit ELEVAGE_ALLOW_REMOTE")

    unter.add_parser("demo", help="Drei Szenarien ohne Datenbank")

    a = p.parse_args(argv)

    if a.befehl == "mischung":
        zeige_mischauftrag(
            baue_mischauftrag(rezept_nach_key(a.rezept), a.kg, art=Ausgleichsart(a.art))
        )
        return 0
    if a.befehl == "demo":
        return _demo()
    if a.befehl == "ui":
        laufe(a.port, a.db, a.host)
        return 0

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
                programm_id=a.programm,
            )
            konflikt = programm_konflikt(herde.tierart, herde.programm_id)
            if konflikt:
                print(konflikt)
                return 2
            archiv.speichere_herde(conn, herde)
            blatt = programm(herde.tierart, herde.programm_id)
            print(f"Eingestallt: {herde.name} ({herde.herde_id}) ab {herde.einstalldatum}")
            print(f"Programm: {blatt.titel}")
            return 0

        if a.befehl == "programm":
            if a.vergleich:
                links, rechts = a.vergleich
                paare = {x.programm_id: x for x in alle_programme()}
                if links not in paare or rechts not in paare:
                    print("Unbekannte Kennung. Bekannt sind: " + ", ".join(sorted(paare)))
                    return 2
                zeige_vergleich(vergleiche(paare[links], paare[rechts]))
                return 0
            if a.zeigen:
                zeige_programm(next(x for x in alle_programme() if x.programm_id == a.zeigen))
                return 0
            if a.herde:
                try:
                    gewechselt = betrieb.setze_programm(conn, a.betrieb, a.herde, a.waehlen)
                except (KeyError, ValueError) as fehler:
                    print(str(fehler))
                    return 2
                blatt = programm(gewechselt.tierart, gewechselt.programm_id)
                print(f"{gewechselt.name}: Programm ist jetzt „{blatt.titel}“.")
                print(
                    "Abgehakte Schritte bleiben abgehakt — was das neue Blatt "
                    "nicht kennt, verschwindet aus der Liste."
                )
                return 0
            for x in alle_programme():
                marke = " (Vorgabe)" if x.vorgabe else ""
                print(
                    f"  {x.programm_id:<20s} {x.tierart.value:<10s} {x.titel}{marke}\n"
                    f"  {'':<20s} {len(x.schritte)} Schritte · "
                    f"{len(x.dauerregeln)} Dauerregeln · {x.herausgeber or x.quelle}"
                )
            return 0

        if a.befehl == "tierarzt":
            if a.name:
                archiv.setze_tierarzt(
                    conn,
                    Tierarzt(
                        tenant_id=a.betrieb,
                        name=a.name,
                        praxis=a.praxis,
                        telefon=a.telefon,
                        email=a.email,
                        hinweis=a.hinweis,
                    ),
                )
                print(f"Tierarzt hinterlegt: {a.name}")
                return 0
            arzt = archiv.tierarzt_fuer(conn, a.betrieb)
            if arzt is None:
                print("Kein Tierarzt hinterlegt. Anlegen mit 'elevage tierarzt --name …'.")
                return 0
            print(f"  {arzt.name}" + (f" · {arzt.praxis}" if arzt.praxis else ""))
            for feld, wert in (("Telefon", arzt.telefon), ("E-Mail", arzt.email)):
                if wert:
                    print(f"  {feld}: {wert}")
            if arzt.hinweis:
                print(f"  {arzt.hinweis}")
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
                    f"ab {h.einstalldatum}  {h.tierzahl:6d} Tiere  "
                    f"{programm(h.tierart, h.programm_id).titel}"
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
                praeparat=a.praeparat,
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
            auftrag, _ = betrieb.mischauftrag(
                conn,
                a.betrieb,
                a.herde,
                a.kg,
                a.am,
                art=Ausgleichsart(a.art) if a.art else None,
            )
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

        if a.befehl == "benutzer":
            if a.passwort:
                vorhanden = archiv.benutzer_mit_hash(conn, a.passwort)
                if vorhanden is None or vorhanden[0].tenant_id != a.betrieb:
                    print(f"Unbekannt: {a.passwort}")
                    return 1
                neues_passwort = getpass("Neues Passwort: ")
                if neues_passwort != getpass("Wiederholen: "):
                    print("Die Eingaben stimmen nicht überein.")
                    return 1
                try:
                    archiv.setze_passwort(conn, a.passwort, hashe_passwort(neues_passwort))
                except PasswortZuKurz as fehler:
                    print(str(fehler))
                    return 1
                print("Gesetzt. Alle offenen Sitzungen dieses Kontos gelten nicht mehr.")
                return 0

            if a.anlegen or a.sperren:
                anmeldename = a.anlegen or a.sperren
                vorhanden = archiv.benutzer_mit_hash(conn, anmeldename)
                if a.sperren:
                    if vorhanden is None:
                        print(f"Unbekannt: {anmeldename}")
                        return 1
                    archiv.lege_benutzer_an(
                        conn, vorhanden[0].model_copy(update={"aktiv": False}), vorhanden[1]
                    )
                    archiv.schliesse_alle_sitzungen(conn, anmeldename)
                    print(f"{anmeldename} gesperrt. Offene Sitzungen gelten nicht mehr.")
                else:
                    if not a.name:
                        print("--name fehlt: ein Konto ohne Klarnamen ist nicht prüfbar.")
                        return 1
                    if vorhanden is not None and vorhanden[0].tenant_id != a.betrieb:
                        print(f"{anmeldename} gehört bereits zu {vorhanden[0].tenant_id}.")
                        return 1
                    passwort = getpass("Passwort: ")
                    if passwort != getpass("Wiederholen: "):
                        print("Die Eingaben stimmen nicht überein.")
                        return 1
                    try:
                        hash_wert = hashe_passwort(passwort)
                    except PasswortZuKurz as fehler:
                        print(str(fehler))
                        return 1
                    archiv.lege_benutzer_an(
                        conn,
                        Benutzer(
                            tenant_id=a.betrieb,
                            benutzer_id=anmeldename,
                            name=a.name,
                            rolle=Rolle(a.rolle),
                            angelegt_am=a.am or date.today(),
                        ),
                        hash_wert,
                    )
                    print(f"{anmeldename} angelegt für {a.betrieb} als {a.rolle}.")
            alle = archiv.liste_benutzer(conn, a.betrieb)
            if not alle:
                print("Keine Benutzer für diesen Betrieb.")
                return 0
            for b in alle:
                stand = "aktiv " if b.aktiv else "GESPERRT"
                print(f"  {b.benutzer_id:16s} {stand:9s} {b.rolle.value:8s} {b.name}")
            return 0

        if a.befehl == "rezept":
            basis = rezept_nach_key(a.rezept)
            if a.zuruecksetzen or a.kg is not None:
                if not a.artikel:
                    print("--artikel fehlt.")
                    return 1
                artikel = normiere_artikel(a.artikel)
                if a.zuruecksetzen:
                    weg = archiv.loesche_anpassung(conn, a.betrieb, a.rezept, artikel)
                    print("Zurück auf den Blattwert." if weg else "Es gab keine Anpassung.")
                else:
                    if a.am is None:
                        print("--am fehlt: eine Änderung ohne Datum ist nicht prüfbar.")
                        return 1
                    betrieb.passe_rezept_an(
                        conn,
                        a.betrieb,
                        Rezeptanpassung(
                            tenant_id=a.betrieb,
                            rezept_key=a.rezept,
                            artikel_id=artikel,
                            kg_je_100=a.kg,
                            grund=a.grund,
                            geaendert_am=a.am,
                        ),
                    )
                    print(f"{artikel} steht jetzt auf {a.kg:.2f} kg je 100 kg.")
            wirksam = betrieb.wirksames_rezept_fuer(conn, a.betrieb, basis)
            zeige_rezept(wirksam)
            return 0

        if a.befehl == "einstellung":
            if a.schluessel:
                archiv.setze_einstellung(conn, a.betrieb, a.schluessel, a.wert or None)
                print(f"{a.schluessel} = {a.wert or '(Blattwert)'}")
            gesetzt = archiv.einstellungen_fuer(conn, a.betrieb)
            for schluessel, erklaerung in sorted(BEKANNT.items()):
                wert = gesetzt.get(schluessel)
                marke = wert if wert else "(Blattwert)"
                print(f"  {schluessel:34s} {marke:12s} {erklaerung}")
            return 0

        if a.befehl == "abgang":
            if archiv.lade_herde(conn, a.betrieb, a.herde) is None:
                print(f"Unbekannte Herde: {a.herde}")
                return 1
            neu = archiv.buche_bewegung(
                conn,
                Bestandsbewegung(
                    tenant_id=a.betrieb,
                    herde_id=a.herde,
                    bewegung_id=a.nummer or f"{a.herde}:{a.am.isoformat()}:{a.grund}",
                    am=a.am,
                    abgang=a.tiere,
                    grund=Abgangsgrund(a.grund),
                    bemerkung=a.bemerkung,
                ),
            )
            print("Gebucht." if neu else "Lag bereits vor — nichts geändert.")
            bild = betrieb.tagesbild(conn, a.betrieb, a.herde, a.am)
            if bild.bestand:
                print(
                    f"Bestand am {a.am}: {bild.bestand.tierzahl} Tiere "
                    f"(von {bild.bestand.eingestallt}, "
                    f"Verluste {bild.bestand.verluste_prozent:.1f} %)"
                )
            return 0

        if a.befehl == "praeparat":
            if a.anlegen:
                if a.eier is None and a.fleisch is None:
                    print(
                        "Weder --eier noch --fleisch angegeben. Unbekannt ist nicht "
                        "null — lieber nichts eintragen als eine geratene Zahl."
                    )
                    return 1
                archiv.setze_praeparat(
                    conn,
                    Praeparat(
                        tenant_id=a.betrieb,
                        praeparat_id=praeparat_id(a.anlegen),
                        name=a.anlegen,
                        wartezeit_eier_tage=a.eier,
                        wartezeit_fleisch_tage=a.fleisch,
                        quelle=a.quelle,
                        hinweis=a.hinweis,
                    ),
                )
                print(f"{a.anlegen} eingetragen.")
            mittel = archiv.praeparate_fuer(conn, a.betrieb)
            if not mittel:
                print("Noch keine Mittel hinterlegt. Ohne sie gibt es keine Wartezeit.")
                return 0

            def tage(wert: int | None) -> str:
                """Unbekannt bekommt einen Strich, keine Null."""
                return f"{wert} T" if wert is not None else "—"

            print(f"  {'Mittel':28s} {'Eier':>6s} {'Fleisch':>8s}  Quelle")
            for m in mittel:
                print(
                    f"  {m.name:28s} {tage(m.wartezeit_eier_tage):>6s} "
                    f"{tage(m.wartezeit_fleisch_tage):>8s}  {m.quelle or ''}"
                )
            return 0

        if a.befehl == "pruefliste":
            if a.abhaken:
                if a.am is None:
                    print("--am fehlt: ein Abhaken ohne Datum ist nicht prüfbar.")
                    return 1
                ok = archiv.hake_vermerk_ab(conn, a.betrieb, a.abhaken, a.am, a.durch)
                print("Abgehakt." if ok else "Unbekannt oder längst erledigt.")
            offen = archiv.vermerke_fuer(conn, a.betrieb, nur_offene=not a.alle)
            if not offen:
                print("Nichts offen.")
                return 0
            for v in offen:
                stand = f"erledigt {v.erledigt_am}" if v.erledigt_am else "OFFEN"
                print(f"\n  [{stand}] {v.vermerk_id}  ({v.betrifft}, seit {v.angelegt_am})")
                print(f"    {v.text}")
            return 0 if a.alle else 2

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
            auftrag, _ = betrieb.mischauftrag(
                conn,
                a.betrieb,
                a.herde,
                a.mischen,
                a.stichtag,
                art=Ausgleichsart(a.art) if a.art else None,
            )
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
