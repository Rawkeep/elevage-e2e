"""Dünner Stdlib-HTTP-Server über den Taktgeber. Keine neue Abhängigkeit.

**Der Betrieb kommt aus der Sitzung, nie aus der Anfrage.** Damit ist die
Mandantentrennung eine Grenze und kein Auswahlfeld: wer angemeldet ist,
sieht genau einen Betrieb, und kein Parameter ändert das.

Drei weitere Entscheidungen, die man später schwer nachrüstet:

* Das Sitzungs-Cookie ist `HttpOnly` und `SameSite=Strict` — JavaScript
  kommt nicht heran, und fremde Seiten können keine Anfrage mitschicken.
* Anmeldeversuche sind gebremst (`VERSUCHE_JE_FENSTER`), je Konto **und**
  je Herkunft. Die Antwort unterscheidet nie zwischen „Konto unbekannt"
  und „Passwort falsch".
* Schreiben hängt an einer Rolle, nicht am Wohlwollen der Oberfläche.

Hinter einem Reverse-Proxy gehört TLS davor; `ELEVAGE_SECURE_COOKIE=1`
setzt dann zusätzlich das `Secure`-Flag.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import date, datetime, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from elevage import archiv, betrieb
from elevage.anmeldung import (
    SITZUNG_TAGE,
    PasswortZuKurz,
    hashe_passwort,
    laeuft_ab,
    neues_token,
    pruefe_passwort,
    token_hash,
)
from elevage.models import (
    Abgangsgrund,
    Ausgleichsart,
    Bestandsbewegung,
    Ereignis,
    EreignisArt,
    Praeparat,
    Quittung,
    Rolle,
    Sitzung,
)
from elevage.seite import ANMELDESEITE, DIENER, ERSTER_BENUTZER, SEITE
from elevage.version import stempel
from elevage.wartezeit import praeparat_id

STANDARD_PORT = 8791
LOKAL = "127.0.0.1"
MAX_KOERPER = 64 * 1024
"""Mehr als das schickt keine ehrliche Anfrage dieser Oberfläche."""

COOKIE = "elevage_sitzung"
VERSUCHE_JE_FENSTER = 5
FENSTER_SEKUNDEN = 900
"""Fünf Fehlversuche in 15 Minuten, dann Pause — je Konto und je Herkunft."""

SCHREIBENDE_ROLLEN = (Rolle.STALL, Rolle.LEITUNG)
LEITUNG_NUR = (Rolle.LEITUNG,)


class _Bremse:
    """Gedächtnis für Fehlversuche. Im Speicher — ein Neustart verzeiht."""

    def __init__(self) -> None:
        self._treffer: dict[str, list[float]] = {}

    def gesperrt(self, schluessel: str, jetzt: float) -> bool:
        frisch = [t for t in self._treffer.get(schluessel, []) if jetzt - t < FENSTER_SEKUNDEN]
        self._treffer[schluessel] = frisch
        return len(frisch) >= VERSUCHE_JE_FENSTER

    def merke(self, schluessel: str, jetzt: float) -> None:
        self._treffer.setdefault(schluessel, []).append(jetzt)

    def vergiss(self, schluessel: str) -> None:
        self._treffer.pop(schluessel, None)


class _Fehler(Exception):
    def __init__(self, status: int, text: str) -> None:
        super().__init__(text)
        self.status = status
        self.text = text


def _datum(text: str | None, vorgabe: date | None = None) -> date:
    if not text:
        if vorgabe is None:
            raise _Fehler(400, "Datum fehlt")
        return vorgabe
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as fehler:
        raise _Fehler(400, f"Kein gültiges Datum: {text}") from fehler


def _pflicht(daten: dict[str, Any], feld: str) -> Any:
    wert = daten.get(feld)
    if wert in (None, ""):
        raise _Fehler(400, f"Feld fehlt: {feld}")
    return wert


LEER_HASH = hashe_passwort("x" * 24)
"""Vergleichswert für unbekannte Konten — damit die Antwortzeit nichts verrät."""


ZEITZONE = os.environ.get("ELEVAGE_ZEITZONE", "UTC")
"""Welcher Tag gemeint ist, wenn jemand „heute" sagt.

`date.today()` liest die Uhr des Servers. Läuft der in UTC und der Betrieb
in Europa, ist abends ab 22 Uhr schon der Folgetag — und eine Quittung
landet auf dem falschen Datum. Togo liegt auf UTC, für andere Orte setzt
`ELEVAGE_ZEITZONE` (z. B. Europe/Berlin) den Betriebstag gerade."""


def heute() -> date:
    """Die einzige Stelle, an der der Server auf die Uhr sieht."""
    try:
        return datetime.now(ZoneInfo(ZEITZONE)).date()
    except (ZoneInfoNotFoundError, ValueError):
        # Eine unbekannte Zeitzone darf den Dienst nicht anhalten —
        # gemeldet wird sie beim Start.
        return datetime.now(timezone.utc).date()


def baue_handler(db: Path | None) -> type[BaseHTTPRequestHandler]:
    """Der Handler bekommt den Datenbankpfad — keine globalen Zustände."""
    bremse = _Bremse()

    class Handler(BaseHTTPRequestHandler):
        server_version = "Taktgeber"
        protocol_version = "HTTP/1.1"

        # --- Grundlagen ---------------------------------------------
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return  # der Stall braucht kein Zugriffsprotokoll

        def _sende(self, status: int, koerper: bytes, typ: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(koerper)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; worker-src 'self'; "
                # data: nur für Bilder — das Zeichen der Seite ist ein
                # Inline-SVG. Ohne diese Zeile blockt die eigene CSP das
                # eigene Favicon, und nur die Browser-Konsole sagt es.
                "img-src data:; "
                "connect-src 'self'; form-action 'none'; base-uri 'none'",
            )
            self.end_headers()
            self.wfile.write(koerper)

        def _json(self, status: int, daten: dict[str, Any]) -> None:
            self._sende(status, json.dumps(daten, ensure_ascii=False).encode(), "application/json")

        def _koerper(self) -> dict[str, Any]:
            laenge = int(self.headers.get("Content-Length") or 0)
            if laenge > MAX_KOERPER:
                raise _Fehler(413, "Anfrage zu groß")
            if laenge <= 0:
                return {}
            try:
                geladen = json.loads(self.rfile.read(laenge))
            except json.JSONDecodeError as fehler:
                raise _Fehler(400, "Kein gültiges JSON") from fehler
            if not isinstance(geladen, dict):
                raise _Fehler(400, "Erwartet wird ein JSON-Objekt")
            return geladen

        def _mit_db(self) -> Any:
            return archiv.oeffne(db)

        # --- Routen -------------------------------------------------
        # --- Sitzung ------------------------------------------------
        def _token(self) -> str | None:
            roh = self.headers.get("Cookie")
            if not roh:
                return None
            keks = SimpleCookie()
            keks.load(roh)
            eintrag = keks.get(COOKIE)
            return eintrag.value if eintrag else None

        def _sitzung(self) -> Sitzung:
            token = self._token()
            if not token:
                raise _Fehler(401, "Nicht angemeldet")
            with self._mit_db() as conn:
                sitzung = archiv.lade_sitzung(conn, token_hash(token), heute())
            if sitzung is None:
                raise _Fehler(401, "Nicht angemeldet")
            return sitzung

        def _darf(self, rollen: tuple[Rolle, ...]) -> Sitzung:
            sitzung = self._sitzung()
            if sitzung.rolle not in rollen:
                raise _Fehler(403, f"Rolle {sitzung.rolle.value} darf das nicht")
            return sitzung

        def _setze_cookie(self, token: str, tage: int) -> list[str]:
            teile = [
                f"{COOKIE}={token}",
                "Path=/",
                "HttpOnly",
                "SameSite=Strict",
                f"Max-Age={tage * 86400}",
            ]
            if os.environ.get("ELEVAGE_SECURE_COOKIE"):
                teile.append("Secure")
            return teile

        def _pruefe_herkunft(self) -> None:
            """Fremde Seite darf keine Anfrage stellen — zusätzlich zu SameSite."""
            herkunft = self.headers.get("Origin")
            if not herkunft:
                return  # kein Browser; SameSite schützt den Browserfall
            erwartet = self.headers.get("Host") or ""
            if urlparse(herkunft).netloc != erwartet:
                raise _Fehler(403, "Fremde Herkunft")

        # --- Routen -------------------------------------------------
        def do_GET(self) -> None:  # noqa: N802
            teile = urlparse(self.path)
            frage = {k: v[0] for k, v in parse_qs(teile.query).items()}
            try:
                with self._mit_db() as conn:
                    leer = archiv.zaehle_benutzer(conn) == 0
                if leer:
                    self._sende(200, ERSTER_BENUTZER.encode(), "text/html; charset=utf-8")
                    return
                if teile.path == "/api/health":
                    # Ohne Anmeldung, weil ein Wächter sie nicht hat — und
                    # ohne jede Betriebszahl, damit sie nichts verrät.
                    self._health()
                    return
                if teile.path == "/sw.js":
                    # Muss von der Wurzel kommen, sonst darf er nur /sw/ steuern.
                    self._sende(200, DIENER.encode(), "text/javascript; charset=utf-8")
                elif teile.path == "/anmelden":
                    self._sende(200, ANMELDESEITE.encode(), "text/html; charset=utf-8")
                elif teile.path in ("/", "/index.html"):
                    try:
                        self._sitzung()
                    except _Fehler:
                        self._umleitung("/anmelden")
                        return
                    self._sende(200, SEITE.encode(), "text/html; charset=utf-8")
                elif teile.path == "/api/ich":
                    sitzung = self._sitzung()
                    self._json(200, sitzung.model_dump(by_alias=True, mode="json"))
                elif teile.path == "/api/herden":
                    self._herden(frage)
                elif teile.path == "/api/tagesbild":
                    self._tagesbild(frage)
                elif teile.path == "/api/verzehr":
                    self._verzehr(frage)
                elif teile.path == "/api/praeparate":
                    self._praeparate()
                else:
                    raise _Fehler(404, "Unbekannter Pfad")
            except _Fehler as fehler:
                self._json(fehler.status, {"fehler": fehler.text})
            except KeyError as fehler:
                self._json(404, {"fehler": str(fehler)})

        def _umleitung(self, ziel: str) -> None:
            self.send_response(303)
            self.send_header("Location", ziel)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            teile = urlparse(self.path)
            try:
                self._pruefe_herkunft()
                daten = self._koerper()
                if teile.path == "/api/anmelden":
                    self._anmelden(daten)
                elif teile.path == "/api/abmelden":
                    self._abmelden()
                elif teile.path == "/api/quittung":
                    self._quittung(daten)
                elif teile.path == "/api/quittung/widerrufen":
                    self._widerrufen(daten)
                elif teile.path == "/api/vorfall":
                    self._vorfall(daten)
                elif teile.path == "/api/mischung":
                    self._mischung(daten)
                elif teile.path == "/api/vermerk/abhaken":
                    self._vermerk(daten)
                elif teile.path == "/api/praeparat":
                    self._praeparat(daten)
                elif teile.path == "/api/abgang":
                    self._abgang(daten)
                elif teile.path == "/api/passwort":
                    self._passwort(daten)
                else:
                    raise _Fehler(404, "Unbekannter Pfad")
            except _Fehler as fehler:
                self._json(fehler.status, {"fehler": fehler.text})
            except (KeyError, ValueError) as fehler:
                self._json(400, {"fehler": str(fehler)})

        # --- Anmelden -----------------------------------------------
        def _anmelden(self, daten: dict[str, Any]) -> None:
            name = str(daten.get("benutzer") or "")
            passwort = str(daten.get("passwort") or "")
            jetzt = time.monotonic()
            herkunft = self.client_address[0]
            schluessel = [f"konto:{name}", f"herkunft:{herkunft}"]
            if any(bremse.gesperrt(k, jetzt) for k in schluessel):
                raise _Fehler(429, "Zu viele Versuche. Bitte später erneut.")

            with self._mit_db() as conn:
                gefunden = archiv.benutzer_mit_hash(conn, name)
                # Auch ohne Treffer wird gerechnet, damit die Antwortzeit nicht
                # verrät, ob es das Konto gibt.
                vergleich = gefunden[1] if gefunden else LEER_HASH
                stimmt = pruefe_passwort(passwort, vergleich)
                if not gefunden or not stimmt or not gefunden[0].aktiv:
                    for k in schluessel:
                        bremse.merke(k, jetzt)
                    raise _Fehler(401, "Anmeldename oder Passwort stimmt nicht.")
                benutzer = gefunden[0]
                token = neues_token()
                archiv.raeume_sitzungen_auf(conn, heute())
                archiv.oeffne_sitzung(
                    conn, token_hash(token), benutzer, heute(), laeuft_ab(heute())
                )
            for k in schluessel:
                bremse.vergiss(k)

            koerper = json.dumps(
                {"betrieb": benutzer.tenant_id, "rolle": benutzer.rolle.value},
                ensure_ascii=False,
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(koerper)))
            self.send_header("Set-Cookie", "; ".join(self._setze_cookie(token, SITZUNG_TAGE)))
            self.end_headers()
            self.wfile.write(koerper)

        def _passwort(self, daten: dict[str, Any]) -> None:
            """Das alte Passwort wird verlangt — ein offener Rechner soll
            nicht reichen, um jemanden auszusperren."""
            sitzung = self._sitzung()
            alt = str(daten.get("alt") or "")
            neu = str(daten.get("neu") or "")
            with self._mit_db() as conn:
                gefunden = archiv.benutzer_mit_hash(conn, sitzung.benutzer_id)
                if gefunden is None or not pruefe_passwort(alt, gefunden[1]):
                    raise _Fehler(401, "Das bisherige Passwort stimmt nicht.")
                try:
                    archiv.setze_passwort(conn, sitzung.benutzer_id, hashe_passwort(neu))
                except PasswortZuKurz as fehler:
                    raise _Fehler(400, str(fehler)) from fehler
            self._json(200, {"geaendert": True, "sitzungen_beendet": True})

        def _abmelden(self) -> None:
            token = self._token()
            if token:
                with self._mit_db() as conn:
                    archiv.schliesse_sitzung(conn, token_hash(token))
            koerper = b'{"abgemeldet": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(koerper)))
            self.send_header(
                "Set-Cookie", f"{COOKIE}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"
            )
            self.end_headers()
            self.wfile.write(koerper)

        # --- Fachliches ---------------------------------------------
        def _health(self) -> None:
            """Prüft die Datenbank mit, nicht nur den Prozess."""
            zustand = {"status": "ok", **stempel()}
            try:
                with self._mit_db() as conn:
                    conn.execute("SELECT 1 FROM schema_version LIMIT 1").fetchone()
            except sqlite3.Error as fehler:
                zustand = {"status": "fehler", "grund": str(fehler), **stempel()}
            self._json(200 if zustand["status"] == "ok" else 503, zustand)

        def _herden(self, frage: dict[str, str]) -> None:
            sitzung = self._sitzung()
            with self._mit_db() as conn:
                herden = archiv.liste_herden(conn, sitzung.tenant_id)
            self._json(200, {"herden": [h.model_dump(by_alias=True, mode="json") for h in herden]})

        def _tagesbild(self, frage: dict[str, str]) -> None:
            sitzung = self._sitzung()
            vorrat = frage.get("vorrat")
            with self._mit_db() as conn:
                bild = betrieb.tagesbild(
                    conn,
                    sitzung.tenant_id,
                    _pflicht(dict(frage), "herde"),
                    _datum(frage.get("stichtag")),
                    vorrat_kg=float(vorrat) if vorrat else None,
                )
            self._json(200, bild.model_dump(by_alias=True, mode="json"))

        def _verzehr(self, frage: dict[str, str]) -> None:
            sitzung = self._sitzung()
            with self._mit_db() as conn:
                kurve, issues = betrieb.verzehrkurve(
                    conn, sitzung.tenant_id, _pflicht(dict(frage), "herde")
                )
            self._json(
                200, {"kurve": kurve.model_dump(by_alias=True, mode="json"), "issues": issues}
            )

        def _abgang(self, daten: dict[str, Any]) -> None:
            sitzung = self._darf(SCHREIBENDE_ROLLEN)
            herde = _pflicht(daten, "herde")
            am = _datum(daten.get("am"))
            tiere = int(_pflicht(daten, "tiere"))
            if tiere <= 0:
                raise _Fehler(400, "Anzahl muss größer als 0 sein")
            grund = Abgangsgrund(daten.get("grund") or "VERENDET")
            with self._mit_db() as conn:
                if archiv.lade_herde(conn, sitzung.tenant_id, herde) is None:
                    raise _Fehler(404, f"Unbekannte Herde: {herde}")
                neu = archiv.buche_bewegung(
                    conn,
                    Bestandsbewegung(
                        tenant_id=sitzung.tenant_id,
                        herde_id=herde,
                        bewegung_id=daten.get("nummer")
                        or f"{herde}:{am.isoformat()}:{grund.value}",
                        am=am,
                        abgang=tiere,
                        grund=grund,
                        bemerkung=daten.get("bemerkung"),
                    ),
                )
            self._json(200, {"neu": neu})

        def _praeparate(self) -> None:
            sitzung = self._sitzung()
            with self._mit_db() as conn:
                mittel = archiv.praeparate_fuer(conn, sitzung.tenant_id)
            self._json(
                200,
                {"praeparate": [m.model_dump(by_alias=True, mode="json") for m in mittel]},
            )

        def _praeparat(self, daten: dict[str, Any]) -> None:
            # Eine Wartezeit einzutragen heißt, für sie geradezustehen.
            sitzung = self._darf(LEITUNG_NUR)
            name = str(_pflicht(daten, "name"))
            eier = daten.get("wartezeitEierTage")
            fleisch = daten.get("wartezeitFleischTage")
            if eier is None and fleisch is None:
                raise _Fehler(400, "Keine Wartezeit angegeben — unbekannt ist nicht null.")
            with self._mit_db() as conn:
                archiv.setze_praeparat(
                    conn,
                    Praeparat(
                        tenant_id=sitzung.tenant_id,
                        praeparat_id=praeparat_id(name),
                        name=name,
                        wartezeit_eier_tage=eier,
                        wartezeit_fleisch_tage=fleisch,
                        quelle=daten.get("quelle"),
                        hinweis=daten.get("hinweis"),
                    ),
                )
            self._json(200, {"name": name})

        def _quittung(self, daten: dict[str, Any]) -> None:
            sitzung = self._darf(SCHREIBENDE_ROLLEN)
            tenant = sitzung.tenant_id
            herde = _pflicht(daten, "herde")
            schritt = _pflicht(daten, "schritt")
            am = _datum(daten.get("am"))
            quittung = Quittung(
                tenant_id=tenant,
                herde_id=herde,
                schritt_key=schritt,
                quittung_id=daten.get("quittungId") or f"{herde}:{schritt}:{am.isoformat()}",
                erledigt_am=am,
                durch=daten.get("durch") or sitzung.name,
                praeparat=daten.get("praeparat"),
                lot=daten.get("lot"),
                bemerkung=daten.get("bemerkung"),
            )
            with self._mit_db() as conn:
                if archiv.lade_herde(conn, tenant, herde) is None:
                    raise _Fehler(404, f"Unbekannte Herde: {herde}")
                neu = archiv.quittiere(conn, quittung)
            self._json(200, {"neu": neu, "quittungId": quittung.quittung_id})

        def _widerrufen(self, daten: dict[str, Any]) -> None:
            sitzung = self._darf(SCHREIBENDE_ROLLEN)
            with self._mit_db() as conn:
                weg = archiv.widerrufe_quittung(
                    conn, sitzung.tenant_id, _pflicht(daten, "quittungId")
                )
            self._json(200, {"widerrufen": weg})

        def _vorfall(self, daten: dict[str, Any]) -> None:
            sitzung = self._darf(SCHREIBENDE_ROLLEN)
            tenant = sitzung.tenant_id
            herde = _pflicht(daten, "herde")
            am = _datum(daten.get("am"))
            art = EreignisArt(daten.get("art") or "GUMBORO")
            ereignis = Ereignis(
                tenant_id=tenant,
                herde_id=herde,
                ereignis_id=daten.get("ereignisId") or f"{herde}:{art.value}:{am.isoformat()}",
                art=art,
                festgestellt_am=am,
                bemerkung=daten.get("bemerkung"),
            )
            with self._mit_db() as conn:
                if archiv.lade_herde(conn, tenant, herde) is None:
                    raise _Fehler(404, f"Unbekannte Herde: {herde}")
                neu = archiv.melde_ereignis(conn, ereignis)
            self._json(200, {"neu": neu, "ereignisId": ereignis.ereignis_id})

        def _vermerk(self, daten: dict[str, Any]) -> None:
            # Einen Prüfvermerk abhaken heißt: die Zahl wurde am Original
            # verglichen. Das ist eine Leitungsentscheidung, kein Handgriff.
            sitzung = self._darf(LEITUNG_NUR)
            with self._mit_db() as conn:
                ok = archiv.hake_vermerk_ab(
                    conn,
                    sitzung.tenant_id,
                    _pflicht(daten, "vermerkId"),
                    _datum(daten.get("am")),
                    daten.get("durch") or sitzung.name,
                )
            self._json(200, {"abgehakt": ok})

        def _mischung(self, daten: dict[str, Any]) -> None:
            sitzung = self._darf(SCHREIBENDE_ROLLEN)
            tenant = sitzung.tenant_id
            herde = _pflicht(daten, "herde")
            am = _datum(daten.get("am"))
            kg = float(_pflicht(daten, "kg"))
            if kg <= 0:
                raise _Fehler(400, "Menge muss größer als 0 sein")
            roh = daten.get("art")
            with self._mit_db() as conn:
                try:
                    auftrag, gebucht = betrieb.mischauftrag(
                        conn,
                        tenant,
                        herde,
                        kg,
                        am,
                        art=Ausgleichsart(roh) if roh else None,
                        buchen=bool(daten.get("buchen")),
                        nummer=daten.get("nummer"),
                    )
                except ValueError as fehler:
                    raise _Fehler(409, str(fehler)) from fehler
                if auftrag is None:
                    self._json(200, {"auftrag": None})
                    return
            self._json(
                200,
                {"auftrag": auftrag.model_dump(by_alias=True, mode="json"), "gebucht": gebucht},
            )

    return Handler


def starte(
    port: int = STANDARD_PORT, db: Path | None = None, host: str | None = None
) -> ThreadingHTTPServer:
    """Server bauen und binden — laufen lassen macht der Aufrufer."""
    ziel = host or LOKAL
    if ziel != LOKAL and not os.environ.get("ELEVAGE_ALLOW_REMOTE"):
        raise SystemExit(
            "Gebunden wird nur auf 127.0.0.1. Für eine andere Adresse "
            "ELEVAGE_ALLOW_REMOTE setzen — und TLS davor terminieren, sonst "
            "reist das Passwort im Klartext."
        )
    with archiv.oeffne(db):
        pass  # Schema einmal wandern lassen, bevor Anfragen kommen
    return ThreadingHTTPServer((ziel, port), baue_handler(db))


def laufe(port: int = STANDARD_PORT, db: Path | None = None, host: str | None = None) -> None:
    ziel = host or LOKAL
    server = starte(port, db, ziel)
    print(f"Taktgeber läuft auf http://{ziel}:{port}  (Strg+C beendet)")
    try:
        ZoneInfo(ZEITZONE)
        print(f"Betriebstag nach Zeitzone {ZEITZONE} — heute ist der {heute()}.")
    except (ZoneInfoNotFoundError, ValueError):
        print(
            f"WARNUNG: Zeitzone {ZEITZONE!r} ist unbekannt, gerechnet wird in UTC. "
            "ELEVAGE_ZEITZONE prüfen."
        )
    if ziel != LOKAL and not os.environ.get("ELEVAGE_SECURE_COOKIE"):
        print(
            "WARNUNG: nicht auf localhost gebunden und ELEVAGE_SECURE_COOKIE ist "
            "nicht gesetzt — ohne TLS davor reisen Passwort und Sitzung im Klartext."
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        server.server_close()
