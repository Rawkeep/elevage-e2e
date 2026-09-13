"""Dünner Stdlib-HTTP-Server über den Taktgeber. Keine neue Abhängigkeit.

**Gebunden wird nur auf localhost.** Es gibt noch keine Anmeldung: der
Betrieb ist ein Auswahlfeld, keine Sicherheitsgrenze. Wer den Server ins
Netz stellen will, muss `ELEVAGE_ALLOW_REMOTE` setzen und bekommt dabei
eine Warnung — eine Mandantentrennung ohne Auth ist keine.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from elevage import archiv, betrieb
from elevage.models import Ereignis, EreignisArt, Quittung
from elevage.seite import SEITE
from elevage.takt import mischauftrag_fuer

STANDARD_PORT = 8791
LOKAL = "127.0.0.1"
MAX_KOERPER = 64 * 1024
"""Mehr als das schickt keine ehrliche Anfrage dieser Oberfläche."""


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


def baue_handler(db: Path | None) -> type[BaseHTTPRequestHandler]:
    """Der Handler bekommt den Datenbankpfad — keine globalen Zustände."""

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
                "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
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
        def do_GET(self) -> None:  # noqa: N802
            teile = urlparse(self.path)
            frage = {k: v[0] for k, v in parse_qs(teile.query).items()}
            try:
                if teile.path in ("/", "/index.html"):
                    self._sende(200, SEITE.encode(), "text/html; charset=utf-8")
                elif teile.path == "/api/herden":
                    self._herden(frage)
                elif teile.path == "/api/tagesbild":
                    self._tagesbild(frage)
                elif teile.path == "/api/verzehr":
                    self._verzehr(frage)
                else:
                    raise _Fehler(404, "Unbekannter Pfad")
            except _Fehler as fehler:
                self._json(fehler.status, {"fehler": fehler.text})
            except KeyError as fehler:
                self._json(404, {"fehler": str(fehler)})

        def do_POST(self) -> None:  # noqa: N802
            teile = urlparse(self.path)
            try:
                daten = self._koerper()
                if teile.path == "/api/quittung":
                    self._quittung(daten)
                elif teile.path == "/api/quittung/widerrufen":
                    self._widerrufen(daten)
                elif teile.path == "/api/vorfall":
                    self._vorfall(daten)
                elif teile.path == "/api/mischung":
                    self._mischung(daten)
                else:
                    raise _Fehler(404, "Unbekannter Pfad")
            except _Fehler as fehler:
                self._json(fehler.status, {"fehler": fehler.text})
            except (KeyError, ValueError) as fehler:
                self._json(400, {"fehler": str(fehler)})

        # --- Fachliches ---------------------------------------------
        def _herden(self, frage: dict[str, str]) -> None:
            with self._mit_db() as conn:
                herden = archiv.liste_herden(conn, frage.get("betrieb", "standard"))
            self._json(200, {"herden": [h.model_dump(by_alias=True, mode="json") for h in herden]})

        def _tagesbild(self, frage: dict[str, str]) -> None:
            vorrat = frage.get("vorrat")
            with self._mit_db() as conn:
                bild = betrieb.tagesbild(
                    conn,
                    frage.get("betrieb", "standard"),
                    _pflicht(dict(frage), "herde"),
                    _datum(frage.get("stichtag")),
                    vorrat_kg=float(vorrat) if vorrat else None,
                )
            self._json(200, bild.model_dump(by_alias=True, mode="json"))

        def _verzehr(self, frage: dict[str, str]) -> None:
            with self._mit_db() as conn:
                kurve, issues = betrieb.verzehrkurve(
                    conn, frage.get("betrieb", "standard"), _pflicht(dict(frage), "herde")
                )
            self._json(
                200, {"kurve": kurve.model_dump(by_alias=True, mode="json"), "issues": issues}
            )

        def _quittung(self, daten: dict[str, Any]) -> None:
            tenant = daten.get("betrieb", "standard")
            herde = _pflicht(daten, "herde")
            schritt = _pflicht(daten, "schritt")
            am = _datum(daten.get("am"))
            quittung = Quittung(
                tenant_id=tenant,
                herde_id=herde,
                schritt_key=schritt,
                quittung_id=daten.get("quittungId") or f"{herde}:{schritt}:{am.isoformat()}",
                erledigt_am=am,
                durch=daten.get("durch") or "",
                lot=daten.get("lot"),
                bemerkung=daten.get("bemerkung"),
            )
            with self._mit_db() as conn:
                if archiv.lade_herde(conn, tenant, herde) is None:
                    raise _Fehler(404, f"Unbekannte Herde: {herde}")
                neu = archiv.quittiere(conn, quittung)
            self._json(200, {"neu": neu, "quittungId": quittung.quittung_id})

        def _widerrufen(self, daten: dict[str, Any]) -> None:
            with self._mit_db() as conn:
                weg = archiv.widerrufe_quittung(
                    conn, daten.get("betrieb", "standard"), _pflicht(daten, "quittungId")
                )
            self._json(200, {"widerrufen": weg})

        def _vorfall(self, daten: dict[str, Any]) -> None:
            tenant = daten.get("betrieb", "standard")
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

        def _mischung(self, daten: dict[str, Any]) -> None:
            tenant = daten.get("betrieb", "standard")
            herde = _pflicht(daten, "herde")
            am = _datum(daten.get("am"))
            kg = float(_pflicht(daten, "kg"))
            if kg <= 0:
                raise _Fehler(400, "Menge muss größer als 0 sein")
            with self._mit_db() as conn:
                bild = betrieb.tagesbild(conn, tenant, herde, am)
                auftrag = mischauftrag_fuer(bild, kg, normieren=bool(daten.get("normieren")))
                if auftrag is None:
                    self._json(200, {"auftrag": None})
                    return
                gebucht = False
                if daten.get("buchen"):
                    if not auftrag.freigegeben:
                        raise _Fehler(409, "Gesperrter Auftrag wird nicht protokolliert")
                    gebucht = archiv.protokolliere_mischung(
                        conn,
                        tenant,
                        daten.get("nummer") or f"{herde}:{am.isoformat()}",
                        herde,
                        am,
                        auftrag,
                    )
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
            "Gebunden wird nur auf 127.0.0.1. Es gibt noch keine Anmeldung — der "
            "Betrieb ist ein Auswahlfeld, keine Sicherheitsgrenze. Für einen "
            "bewussten Ausnahmefall ELEVAGE_ALLOW_REMOTE setzen."
        )
    with archiv.oeffne(db):
        pass  # Schema einmal wandern lassen, bevor Anfragen kommen
    return ThreadingHTTPServer((ziel, port), baue_handler(db))


def laufe(port: int = STANDARD_PORT, db: Path | None = None, host: str | None = None) -> None:
    ziel = host or LOKAL
    server = starte(port, db, ziel)
    print(f"Taktgeber läuft auf http://{ziel}:{port}  (Strg+C beendet)")
    if ziel != LOKAL:
        print("WARNUNG: nicht auf localhost gebunden, und es gibt keine Anmeldung.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        server.server_close()
