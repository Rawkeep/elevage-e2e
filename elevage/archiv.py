"""Sendungsarchiv des Betriebs: SQLite aus der Standardbibliothek.

Keine neue Abhängigkeit — der Kern bleibt bei pydantic. Migrationen sind
nummeriert und stehen in einer Versionstabelle; es gibt kein ad-hoc ALTER
im Code (Go-Live-Checkliste des Briefings).

**Mandantentrennung ist hier Gesetz:** jede Tabelle trägt `tenant_id`,
jede Abfrage filtert darauf. `test_jede_tabelle_hat_tenant_id` bewacht das
als Fitness-Function — eine neue Tabelle ohne Mandanten fällt sofort auf.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from elevage.models import Ereignis, EreignisArt, Herde, Quittung, Tierart

STANDARD_PFAD = Path(os.environ.get("ELEVAGE_DB", Path.home() / ".elevage" / "elevage.db"))

MIGRATIONEN: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE herde (
            tenant_id      TEXT NOT NULL,
            herde_id       TEXT NOT NULL,
            name           TEXT NOT NULL,
            tierart        TEXT NOT NULL,
            einstalldatum  TEXT NOT NULL,
            tierzahl       INTEGER NOT NULL,
            hoher_virusdruck   INTEGER NOT NULL DEFAULT 0,
            spaete_schlachtung INTEGER NOT NULL DEFAULT 0,
            aktiv          INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (tenant_id, herde_id)
        );

        CREATE TABLE quittung (
            tenant_id    TEXT NOT NULL,
            quittung_id  TEXT NOT NULL,
            herde_id     TEXT NOT NULL,
            schritt_key  TEXT NOT NULL,
            erledigt_am  TEXT NOT NULL,
            durch        TEXT NOT NULL DEFAULT '',
            lot          TEXT,
            bemerkung    TEXT,
            PRIMARY KEY (tenant_id, quittung_id)
        );

        CREATE INDEX quittung_nach_herde
            ON quittung (tenant_id, herde_id, schritt_key);
        """,
    ),
    (
        2,
        """
        CREATE TABLE mischprotokoll (
            tenant_id    TEXT NOT NULL,
            protokoll_id TEXT NOT NULL,
            herde_id     TEXT NOT NULL,
            rezept_key   TEXT NOT NULL,
            gemischt_am  TEXT NOT NULL,
            ziel_kg      REAL NOT NULL,
            ist_kg       REAL NOT NULL,
            normiert     INTEGER NOT NULL DEFAULT 0,
            zeilen_json  TEXT NOT NULL,
            issues_json  TEXT NOT NULL DEFAULT '[]',
            PRIMARY KEY (tenant_id, protokoll_id)
        );
        """,
    ),
    (
        3,
        """
        CREATE TABLE ereignis (
            tenant_id       TEXT NOT NULL,
            ereignis_id     TEXT NOT NULL,
            herde_id        TEXT NOT NULL,
            art             TEXT NOT NULL,
            festgestellt_am TEXT NOT NULL,
            bemerkung       TEXT,
            PRIMARY KEY (tenant_id, ereignis_id)
        );

        CREATE INDEX ereignis_nach_herde ON ereignis (tenant_id, herde_id);
        """,
    ),
]


def _verbinde(pfad: Path) -> sqlite3.Connection:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(pfad)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migriere(conn: sqlite3.Connection) -> int:
    """Vorwärts, nummeriert, wiederholbar. Gibt die erreichte Version zurück."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version ("
        "  version INTEGER PRIMARY KEY, angewendet_am TEXT NOT NULL)"
    )
    zeile = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    stand = zeile["v"] or 0
    for nummer, sql in MIGRATIONEN:
        if nummer <= stand:
            continue
        conn.executescript(sql)
        conn.execute(
            "INSERT INTO schema_version (version, angewendet_am) VALUES (?, datetime('now'))",
            (nummer,),
        )
        stand = nummer
    conn.commit()
    return stand


@contextmanager
def oeffne(pfad: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Verbindung mit gewandertem Schema. `:memory:` geht über Path(':memory:')."""
    ziel = pfad or STANDARD_PFAD
    conn = _verbinde(ziel)
    try:
        migriere(conn)
        yield conn
    finally:
        conn.close()


# --- Herden -------------------------------------------------------------


def speichere_herde(conn: sqlite3.Connection, herde: Herde) -> None:
    """Anlegen oder aktualisieren — die Herde ist über (Mandant, Id) eindeutig."""
    conn.execute(
        "INSERT INTO herde (tenant_id, herde_id, name, tierart, einstalldatum, tierzahl,"
        " hoher_virusdruck, spaete_schlachtung)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT (tenant_id, herde_id) DO UPDATE SET"
        "  name=excluded.name, tierart=excluded.tierart,"
        "  einstalldatum=excluded.einstalldatum, tierzahl=excluded.tierzahl,"
        "  hoher_virusdruck=excluded.hoher_virusdruck,"
        "  spaete_schlachtung=excluded.spaete_schlachtung",
        (
            herde.tenant_id,
            herde.herde_id,
            herde.name,
            herde.tierart.value,
            herde.einstalldatum.isoformat(),
            herde.tierzahl,
            int(herde.hoher_virusdruck),
            int(herde.spaete_schlachtung),
        ),
    )
    conn.commit()


def _zu_herde(zeile: sqlite3.Row) -> Herde:
    return Herde(
        tenant_id=zeile["tenant_id"],
        herde_id=zeile["herde_id"],
        name=zeile["name"],
        tierart=Tierart(zeile["tierart"]),
        einstalldatum=date.fromisoformat(zeile["einstalldatum"]),
        tierzahl=zeile["tierzahl"],
        hoher_virusdruck=bool(zeile["hoher_virusdruck"]),
        spaete_schlachtung=bool(zeile["spaete_schlachtung"]),
    )


def lade_herde(conn: sqlite3.Connection, tenant_id: str, herde_id: str) -> Herde | None:
    zeile = conn.execute(
        "SELECT * FROM herde WHERE tenant_id = ? AND herde_id = ?", (tenant_id, herde_id)
    ).fetchone()
    return _zu_herde(zeile) if zeile else None


def liste_herden(
    conn: sqlite3.Connection, tenant_id: str, *, nur_aktive: bool = True
) -> list[Herde]:
    sql = "SELECT * FROM herde WHERE tenant_id = ?"
    if nur_aktive:
        sql += " AND aktiv = 1"
    sql += " ORDER BY einstalldatum DESC, herde_id"
    return [_zu_herde(z) for z in conn.execute(sql, (tenant_id,))]


def stalle_aus(conn: sqlite3.Connection, tenant_id: str, herde_id: str) -> None:
    """Ausstallen heißt inaktiv, nicht gelöscht — die Historie bleibt."""
    conn.execute(
        "UPDATE herde SET aktiv = 0 WHERE tenant_id = ? AND herde_id = ?",
        (tenant_id, herde_id),
    )
    conn.commit()


# --- Quittungen ---------------------------------------------------------


def quittiere(conn: sqlite3.Connection, quittung: Quittung) -> bool:
    """Ein Abhak-Ereignis ablegen.

    Gibt True zurück, wenn es neu war. Dieselbe `quittung_id` zweimal zu
    senden ist folgenlos — genau das braucht der spätere Offline-Sync, wenn
    das Handy seine Warteschlange wiederholt abschickt.
    """
    cur = conn.execute(
        "INSERT OR IGNORE INTO quittung (tenant_id, quittung_id, herde_id, schritt_key,"
        " erledigt_am, durch, lot, bemerkung) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            quittung.tenant_id,
            quittung.quittung_id,
            quittung.herde_id,
            quittung.schritt_key,
            quittung.erledigt_am.isoformat(),
            quittung.durch,
            quittung.lot,
            quittung.bemerkung,
        ),
    )
    conn.commit()
    return cur.rowcount == 1


def quittungen_fuer(conn: sqlite3.Connection, tenant_id: str, herde_id: str) -> list[Quittung]:
    zeilen = conn.execute(
        "SELECT * FROM quittung WHERE tenant_id = ? AND herde_id = ?"
        " ORDER BY erledigt_am, quittung_id",
        (tenant_id, herde_id),
    )
    return [
        Quittung(
            tenant_id=z["tenant_id"],
            herde_id=z["herde_id"],
            schritt_key=z["schritt_key"],
            quittung_id=z["quittung_id"],
            erledigt_am=date.fromisoformat(z["erledigt_am"]),
            durch=z["durch"],
            lot=z["lot"],
            bemerkung=z["bemerkung"],
        )
        for z in zeilen
    ]


# --- Mischprotokoll -----------------------------------------------------


def protokolliere_mischung(
    conn: sqlite3.Connection,
    tenant_id: str,
    protokoll_id: str,
    herde_id: str,
    gemischt_am: date,
    auftrag: object,
) -> bool:
    """Was gemischt wurde, bleibt nachweisbar — auch die Befunde dazu.

    Ein gesperrter Auftrag wird NICHT protokolliert: was nicht freigegeben
    ist, wurde nicht gemischt.
    """
    if not getattr(auftrag, "freigegeben", False):
        raise ValueError("Gesperrter Mischauftrag wird nicht protokolliert")
    cur = conn.execute(
        "INSERT OR IGNORE INTO mischprotokoll (tenant_id, protokoll_id, herde_id,"
        " rezept_key, gemischt_am, ziel_kg, ist_kg, normiert, zeilen_json, issues_json)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            tenant_id,
            protokoll_id,
            herde_id,
            auftrag.rezept_key,  # type: ignore[attr-defined]
            gemischt_am.isoformat(),
            auftrag.ziel_kg,  # type: ignore[attr-defined]
            auftrag.ist_einwaage_kg,  # type: ignore[attr-defined]
            int(auftrag.normiert),  # type: ignore[attr-defined]
            json.dumps(
                [{"artikelId": z.artikel_id, "kg": z.kg} for z in auftrag.zeilen],  # type: ignore[attr-defined]
                ensure_ascii=False,
            ),
            json.dumps(auftrag.issues, ensure_ascii=False),  # type: ignore[attr-defined]
        ),
    )
    conn.commit()
    return cur.rowcount == 1


# --- Vorfälle -----------------------------------------------------------


def melde_ereignis(conn: sqlite3.Connection, ereignis: Ereignis) -> bool:
    """Einen Vorfall festhalten. Wie die Quittung idempotent über die Id."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO ereignis (tenant_id, ereignis_id, herde_id, art,"
        " festgestellt_am, bemerkung) VALUES (?, ?, ?, ?, ?, ?)",
        (
            ereignis.tenant_id,
            ereignis.ereignis_id,
            ereignis.herde_id,
            ereignis.art.value,
            ereignis.festgestellt_am.isoformat(),
            ereignis.bemerkung,
        ),
    )
    conn.commit()
    return cur.rowcount == 1


def ereignisse_fuer(conn: sqlite3.Connection, tenant_id: str, herde_id: str) -> list[Ereignis]:
    zeilen = conn.execute(
        "SELECT * FROM ereignis WHERE tenant_id = ? AND herde_id = ?"
        " ORDER BY festgestellt_am, ereignis_id",
        (tenant_id, herde_id),
    )
    return [
        Ereignis(
            tenant_id=z["tenant_id"],
            herde_id=z["herde_id"],
            ereignis_id=z["ereignis_id"],
            art=EreignisArt(z["art"]),
            festgestellt_am=date.fromisoformat(z["festgestellt_am"]),
            bemerkung=z["bemerkung"],
        )
        for z in zeilen
    ]


def mischungen_fuer(
    conn: sqlite3.Connection, tenant_id: str, herde_id: str
) -> list[tuple[date, float]]:
    """(Datum, Ist-Einwaage) je protokollierter Mischung — Rohstoff der Verzehrkurve."""
    zeilen = conn.execute(
        "SELECT gemischt_am, ist_kg FROM mischprotokoll"
        " WHERE tenant_id = ? AND herde_id = ? ORDER BY gemischt_am",
        (tenant_id, herde_id),
    )
    return [(date.fromisoformat(z["gemischt_am"]), float(z["ist_kg"])) for z in zeilen]


def tabellen(conn: sqlite3.Connection) -> list[str]:
    """Fachtabellen ohne die Schema-Buchführung."""
    zeilen = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
        " AND name NOT LIKE 'sqlite_%' AND name <> 'schema_version'"
    )
    return sorted(z["name"] for z in zeilen)


def spalten(conn: sqlite3.Connection, tabelle: str) -> list[str]:
    return [z["name"] for z in conn.execute(f"PRAGMA table_info({tabelle})")]
