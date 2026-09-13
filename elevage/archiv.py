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

from elevage.einstellung import BEKANNT
from elevage.models import (
    Benutzer,
    Ereignis,
    EreignisArt,
    Herde,
    Praeparat,
    Pruefvermerk,
    Quittung,
    Rezeptanpassung,
    Rolle,
    Sitzung,
    Tierart,
)

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
    (
        4,
        """
        CREATE TABLE rezept_anpassung (
            tenant_id    TEXT NOT NULL,
            rezept_key   TEXT NOT NULL,
            artikel_id   TEXT NOT NULL,
            kg_je_100    REAL NOT NULL CHECK (kg_je_100 >= 0),
            grund        TEXT,
            geaendert_am TEXT NOT NULL,
            PRIMARY KEY (tenant_id, rezept_key, artikel_id)
        );

        CREATE TABLE pruefvermerk (
            tenant_id      TEXT NOT NULL,
            vermerk_id     TEXT NOT NULL,
            betrifft       TEXT NOT NULL,
            text           TEXT NOT NULL,
            angelegt_am    TEXT NOT NULL,
            erledigt_am    TEXT,
            erledigt_durch TEXT,
            PRIMARY KEY (tenant_id, vermerk_id)
        );

        CREATE TABLE einstellung (
            tenant_id TEXT NOT NULL,
            schluessel TEXT NOT NULL,
            wert       TEXT NOT NULL,
            PRIMARY KEY (tenant_id, schluessel)
        );
        """,
    ),
    (
        5,
        """
        CREATE TABLE benutzer (
            benutzer_id   TEXT PRIMARY KEY,
            tenant_id     TEXT NOT NULL,
            name          TEXT NOT NULL,
            passwort_hash TEXT NOT NULL,
            rolle         TEXT NOT NULL DEFAULT 'STALL',
            aktiv         INTEGER NOT NULL DEFAULT 1,
            angelegt_am   TEXT NOT NULL
        );

        CREATE INDEX benutzer_nach_betrieb ON benutzer (tenant_id);

        CREATE TABLE sitzung (
            token_hash   TEXT PRIMARY KEY,
            benutzer_id  TEXT NOT NULL,
            tenant_id    TEXT NOT NULL,
            angelegt_am  TEXT NOT NULL,
            laeuft_ab_am TEXT NOT NULL,
            FOREIGN KEY (benutzer_id) REFERENCES benutzer (benutzer_id)
        );

        CREATE INDEX sitzung_nach_benutzer ON sitzung (benutzer_id);
        """,
    ),
    (
        6,
        """
        CREATE TABLE praeparat (
            tenant_id              TEXT NOT NULL,
            praeparat_id           TEXT NOT NULL,
            name                   TEXT NOT NULL,
            wartezeit_eier_tage    INTEGER,
            wartezeit_fleisch_tage INTEGER,
            quelle                 TEXT,
            hinweis                TEXT,
            PRIMARY KEY (tenant_id, praeparat_id)
        );

        ALTER TABLE quittung ADD COLUMN praeparat TEXT;
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
        " erledigt_am, durch, praeparat, lot, bemerkung)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            quittung.tenant_id,
            quittung.quittung_id,
            quittung.herde_id,
            quittung.schritt_key,
            quittung.erledigt_am.isoformat(),
            quittung.durch,
            quittung.praeparat,
            quittung.lot,
            quittung.bemerkung,
        ),
    )
    conn.commit()
    return cur.rowcount == 1


def widerrufe_quittung(conn: sqlite3.Connection, tenant_id: str, quittung_id: str) -> bool:
    """Abhaken rückgängig machen — das Gegenstück zum Undo in der Oberfläche.

    Die Briefing-Regel lautet Undo statt Nachfragen: sofort ausführen und
    zurücknehmbar machen, statt eine Bestätigungskaskade zu bauen.
    """
    cur = conn.execute(
        "DELETE FROM quittung WHERE tenant_id = ? AND quittung_id = ?",
        (tenant_id, quittung_id),
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
            praeparat=z["praeparat"],
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


# --- Rezeptanpassungen --------------------------------------------------


def setze_anpassung(conn: sqlite3.Connection, anpassung: Rezeptanpassung) -> None:
    """Menge eines Postens für diesen Betrieb festlegen. 0 kg heißt: entfällt."""
    conn.execute(
        "INSERT INTO rezept_anpassung (tenant_id, rezept_key, artikel_id, kg_je_100,"
        " grund, geaendert_am) VALUES (?, ?, ?, ?, ?, ?)"
        " ON CONFLICT (tenant_id, rezept_key, artikel_id) DO UPDATE SET"
        "  kg_je_100=excluded.kg_je_100, grund=excluded.grund,"
        "  geaendert_am=excluded.geaendert_am",
        (
            anpassung.tenant_id,
            anpassung.rezept_key,
            anpassung.artikel_id,
            anpassung.kg_je_100,
            anpassung.grund,
            anpassung.geaendert_am.isoformat(),
        ),
    )
    conn.commit()


def loesche_anpassung(
    conn: sqlite3.Connection, tenant_id: str, rezept_key: str, artikel_id: str
) -> bool:
    """Zurück zum Blattwert."""
    cur = conn.execute(
        "DELETE FROM rezept_anpassung WHERE tenant_id = ? AND rezept_key = ? AND artikel_id = ?",
        (tenant_id, rezept_key, artikel_id),
    )
    conn.commit()
    return cur.rowcount == 1


def anpassungen_fuer(conn: sqlite3.Connection, tenant_id: str) -> list[Rezeptanpassung]:
    zeilen = conn.execute(
        "SELECT * FROM rezept_anpassung WHERE tenant_id = ? ORDER BY rezept_key, artikel_id",
        (tenant_id,),
    )
    return [
        Rezeptanpassung(
            tenant_id=z["tenant_id"],
            rezept_key=z["rezept_key"],
            artikel_id=z["artikel_id"],
            kg_je_100=z["kg_je_100"],
            grund=z["grund"],
            geaendert_am=date.fromisoformat(z["geaendert_am"]),
        )
        for z in zeilen
    ]


# --- Prüfvermerke -------------------------------------------------------


def lege_vermerk_an(conn: sqlite3.Connection, vermerk: Pruefvermerk) -> bool:
    """Idempotent über die Vermerk-Nummer: derselbe Punkt liegt nur einmal.

    Ein erledigter Vermerk wird nicht wieder aufgemacht — sonst meldet sich
    jeder abgehakte Punkt beim nächsten Mischen erneut.
    """
    cur = conn.execute(
        "INSERT OR IGNORE INTO pruefvermerk (tenant_id, vermerk_id, betrifft, text,"
        " angelegt_am) VALUES (?, ?, ?, ?, ?)",
        (
            vermerk.tenant_id,
            vermerk.vermerk_id,
            vermerk.betrifft,
            vermerk.text,
            vermerk.angelegt_am.isoformat(),
        ),
    )
    conn.commit()
    return cur.rowcount == 1


def hake_vermerk_ab(
    conn: sqlite3.Connection, tenant_id: str, vermerk_id: str, am: date, durch: str = ""
) -> bool:
    cur = conn.execute(
        "UPDATE pruefvermerk SET erledigt_am = ?, erledigt_durch = ?"
        " WHERE tenant_id = ? AND vermerk_id = ? AND erledigt_am IS NULL",
        (am.isoformat(), durch, tenant_id, vermerk_id),
    )
    conn.commit()
    return cur.rowcount == 1


def vermerke_fuer(
    conn: sqlite3.Connection, tenant_id: str, *, nur_offene: bool = True
) -> list[Pruefvermerk]:
    sql = "SELECT * FROM pruefvermerk WHERE tenant_id = ?"
    if nur_offene:
        sql += " AND erledigt_am IS NULL"
    sql += " ORDER BY angelegt_am, vermerk_id"
    return [
        Pruefvermerk(
            tenant_id=z["tenant_id"],
            vermerk_id=z["vermerk_id"],
            betrifft=z["betrifft"],
            text=z["text"],
            angelegt_am=date.fromisoformat(z["angelegt_am"]),
            erledigt_am=date.fromisoformat(z["erledigt_am"]) if z["erledigt_am"] else None,
            erledigt_durch=z["erledigt_durch"],
        )
        for z in conn.execute(sql, (tenant_id,))
    ]


# --- Einstellungen ------------------------------------------------------


def setze_einstellung(
    conn: sqlite3.Connection, tenant_id: str, schluessel: str, wert: str | None
) -> None:
    """Unbekannte Schlüssel werden abgewiesen, nicht stillschweigend abgelegt."""
    if schluessel not in BEKANNT:
        raise KeyError(f"Unbekannte Einstellung: {schluessel}")
    if wert is None:
        conn.execute(
            "DELETE FROM einstellung WHERE tenant_id = ? AND schluessel = ?",
            (tenant_id, schluessel),
        )
    else:
        conn.execute(
            "INSERT INTO einstellung (tenant_id, schluessel, wert) VALUES (?, ?, ?)"
            " ON CONFLICT (tenant_id, schluessel) DO UPDATE SET wert = excluded.wert",
            (tenant_id, schluessel, wert),
        )
    conn.commit()


def einstellungen_fuer(conn: sqlite3.Connection, tenant_id: str) -> dict[str, str]:
    return {
        z["schluessel"]: z["wert"]
        for z in conn.execute(
            "SELECT schluessel, wert FROM einstellung WHERE tenant_id = ?", (tenant_id,)
        )
    }


# --- Präparate ----------------------------------------------------------


def setze_praeparat(conn: sqlite3.Connection, praeparat: Praeparat) -> None:
    """Ein Mittel und seine Wartezeit. None bleibt None — unbekannt ist nicht null."""
    conn.execute(
        "INSERT INTO praeparat (tenant_id, praeparat_id, name, wartezeit_eier_tage,"
        " wartezeit_fleisch_tage, quelle, hinweis) VALUES (?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT (tenant_id, praeparat_id) DO UPDATE SET"
        "  name=excluded.name, wartezeit_eier_tage=excluded.wartezeit_eier_tage,"
        "  wartezeit_fleisch_tage=excluded.wartezeit_fleisch_tage,"
        "  quelle=excluded.quelle, hinweis=excluded.hinweis",
        (
            praeparat.tenant_id,
            praeparat.praeparat_id,
            praeparat.name,
            praeparat.wartezeit_eier_tage,
            praeparat.wartezeit_fleisch_tage,
            praeparat.quelle,
            praeparat.hinweis,
        ),
    )
    conn.commit()


def praeparate_fuer(conn: sqlite3.Connection, tenant_id: str) -> list[Praeparat]:
    return [
        Praeparat(
            tenant_id=z["tenant_id"],
            praeparat_id=z["praeparat_id"],
            name=z["name"],
            wartezeit_eier_tage=z["wartezeit_eier_tage"],
            wartezeit_fleisch_tage=z["wartezeit_fleisch_tage"],
            quelle=z["quelle"],
            hinweis=z["hinweis"],
        )
        for z in conn.execute(
            "SELECT * FROM praeparat WHERE tenant_id = ? ORDER BY name", (tenant_id,)
        )
    ]


# --- Benutzer und Sitzungen ---------------------------------------------


def lege_benutzer_an(conn: sqlite3.Connection, benutzer: Benutzer, passwort_hash: str) -> None:
    """Anmeldename ist betriebsübergreifend eindeutig — er identifiziert den Betrieb."""
    conn.execute(
        "INSERT INTO benutzer (benutzer_id, tenant_id, name, passwort_hash, rolle,"
        " aktiv, angelegt_am) VALUES (?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT (benutzer_id) DO UPDATE SET"
        "  tenant_id=excluded.tenant_id, name=excluded.name,"
        "  passwort_hash=excluded.passwort_hash, rolle=excluded.rolle,"
        "  aktiv=excluded.aktiv",
        (
            benutzer.benutzer_id,
            benutzer.tenant_id,
            benutzer.name,
            passwort_hash,
            benutzer.rolle.value,
            int(benutzer.aktiv),
            benutzer.angelegt_am.isoformat(),
        ),
    )
    conn.commit()


def benutzer_mit_hash(conn: sqlite3.Connection, benutzer_id: str) -> tuple[Benutzer, str] | None:
    zeile = conn.execute("SELECT * FROM benutzer WHERE benutzer_id = ?", (benutzer_id,)).fetchone()
    if zeile is None:
        return None
    return (
        Benutzer(
            tenant_id=zeile["tenant_id"],
            benutzer_id=zeile["benutzer_id"],
            name=zeile["name"],
            rolle=Rolle(zeile["rolle"]),
            aktiv=bool(zeile["aktiv"]),
            angelegt_am=date.fromisoformat(zeile["angelegt_am"]),
        ),
        zeile["passwort_hash"],
    )


def zaehle_benutzer(conn: sqlite3.Connection) -> int:
    zeile = conn.execute("SELECT COUNT(*) AS n FROM benutzer").fetchone()
    return int(zeile["n"])


def liste_benutzer(conn: sqlite3.Connection, tenant_id: str) -> list[Benutzer]:
    return [
        Benutzer(
            tenant_id=z["tenant_id"],
            benutzer_id=z["benutzer_id"],
            name=z["name"],
            rolle=Rolle(z["rolle"]),
            aktiv=bool(z["aktiv"]),
            angelegt_am=date.fromisoformat(z["angelegt_am"]),
        )
        for z in conn.execute(
            "SELECT * FROM benutzer WHERE tenant_id = ? ORDER BY benutzer_id",
            (tenant_id,),
        )
    ]


def oeffne_sitzung(
    conn: sqlite3.Connection,
    token_hash_wert: str,
    benutzer: Benutzer,
    angelegt_am: date,
    laeuft_ab_am: date,
) -> None:
    conn.execute(
        "INSERT INTO sitzung (token_hash, benutzer_id, tenant_id, angelegt_am,"
        " laeuft_ab_am) VALUES (?, ?, ?, ?, ?)",
        (
            token_hash_wert,
            benutzer.benutzer_id,
            benutzer.tenant_id,
            angelegt_am.isoformat(),
            laeuft_ab_am.isoformat(),
        ),
    )
    conn.commit()


def lade_sitzung(conn: sqlite3.Connection, token_hash_wert: str, stichtag: date) -> Sitzung | None:
    """Abgelaufene Sitzungen gelten nicht — und werden gleich weggeräumt."""
    zeile = conn.execute(
        "SELECT s.*, b.name, b.rolle, b.aktiv FROM sitzung s"
        " JOIN benutzer b ON b.benutzer_id = s.benutzer_id"
        " WHERE s.token_hash = ?",
        (token_hash_wert,),
    ).fetchone()
    if zeile is None:
        return None
    if date.fromisoformat(zeile["laeuft_ab_am"]) < stichtag or not zeile["aktiv"]:
        schliesse_sitzung(conn, token_hash_wert)
        return None
    return Sitzung(
        tenant_id=zeile["tenant_id"],
        benutzer_id=zeile["benutzer_id"],
        rolle=Rolle(zeile["rolle"]),
        name=zeile["name"],
        laeuft_ab_am=date.fromisoformat(zeile["laeuft_ab_am"]),
    )


def schliesse_sitzung(conn: sqlite3.Connection, token_hash_wert: str) -> bool:
    cur = conn.execute("DELETE FROM sitzung WHERE token_hash = ?", (token_hash_wert,))
    conn.commit()
    return cur.rowcount == 1


def raeume_sitzungen_auf(conn: sqlite3.Connection, stichtag: date) -> int:
    cur = conn.execute("DELETE FROM sitzung WHERE laeuft_ab_am < ?", (stichtag.isoformat(),))
    conn.commit()
    return cur.rowcount


def tabellen(conn: sqlite3.Connection) -> list[str]:
    """Fachtabellen ohne die Schema-Buchführung und ohne die Anmeldung.

    `benutzer` und `sitzung` sind betriebsübergreifend: der Anmeldename sagt
    ja gerade, zu welchem Betrieb jemand gehört. Sie tragen trotzdem eine
    tenant_id, nur eben nicht als Mandantenfilter.
    """
    zeilen = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
        " AND name NOT LIKE 'sqlite_%' AND name <> 'schema_version'"
    )
    return sorted(z["name"] for z in zeilen)


def spalten(conn: sqlite3.Connection, tabelle: str) -> list[str]:
    return [z["name"] for z in conn.execute(f"PRAGMA table_info({tabelle})")]
