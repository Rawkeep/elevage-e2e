"""Die Oberfläche: 0 externe Requests, bedienbar, barrierefrei genug."""

import re

from elevage.seite import SEITE

SVG_NAMENSRAUM = "http://www.w3.org/2000/svg"
"""Der einzige erlaubte http-Text in der Seite.

Das ist die Kennung des SVG-Namensraums im Inline-Favicon — eine Zeichenkette,
die der Browser nie abruft. Ohne sie rendert die data:-URL nicht. Jede andere
Adresse wäre ein echter Request und damit ein Regelbruch."""


def test_null_externe_requests():
    """Hausregel: was ausgeliefert wird, holt nichts aus dem Netz."""
    ohne_namensraum = SEITE.replace(SVG_NAMENSRAUM, "")
    for muster in (r"https?://", r"src=[\"']//", r"href=[\"']//", r"cdn\.", r"fonts\.g"):
        assert not re.search(muster, ohne_namensraum), f"externer Verweis: {muster}"


def test_das_zeichen_der_seite_ist_inline():
    """Sonst fragt jeder Browser /favicon.ico an und bekommt 404."""
    assert 'rel="icon" href="data:image/svg+xml,' in SEITE
    assert SEITE.count(SVG_NAMENSRAUM) == 1


def test_kein_build_noetig():
    """Alles inline — kein Bundler, keine Datei daneben."""
    assert "<script>" in SEITE and "<style>" in SEITE
    assert not re.search(r"<script[^>]+src=", SEITE)
    assert not re.search(r"<link[^>]+stylesheet", SEITE)


def test_grundgeruest_stimmt():
    assert '<html lang="de">' in SEITE
    assert 'name="viewport"' in SEITE
    assert SEITE.count("<h1") == 1
    assert "<title>" in SEITE


def test_jedes_eingabefeld_hat_ein_label():
    """Placeholder ist kein Label (Briefing: Barrierefreiheit)."""
    ids = set(re.findall(r'<(?:input|select)[^>]*\bid="([^"]+)"', SEITE))
    beschriftet = set(re.findall(r'<label for="([^"]+)"', SEITE))
    assert ids - beschriftet == set(), f"ohne Label: {ids - beschriftet}"


def test_touch_ziele_und_schriftgroesse_aus_dem_briefing():
    """Bedienung im Stehen, mit Handschuhen, bei Sonnenlicht."""
    assert "--ziel: 44px" in SEITE
    assert "min-height: var(--ziel)" in SEITE
    schrift = re.search(r"--schrift:\s*(\d+)px", SEITE)
    assert schrift and int(schrift.group(1)) >= 14


def test_farbe_traegt_nie_allein():
    """Jede Ampel hat zusätzlich ein Zeichen und ein Wort."""
    assert "function zeichen(" in SEITE
    assert "function wort(" in SEITE
    assert "überfällig" in SEITE and "jetzt dran" in SEITE


def test_dark_mode_und_ruhige_bewegung():
    assert "prefers-color-scheme: dark" in SEITE
    assert 'data-thema="dunkel"' in SEITE
    assert "prefers-reduced-motion" in SEITE


def test_undo_statt_confirm_kaskade():
    """Briefing-Muster: destruktiv sofort ausführen, dann rückgängig anbieten."""
    assert "Rückgängig" in SEITE
    assert "/api/quittung/widerrufen" in SEITE
    assert "confirm(" not in SEITE


def test_alle_drei_zustaende_sind_gebaut():
    assert "Lade \\u2026" in SEITE  # laden
    assert "Noch keine Herde für diesen Betrieb" in SEITE  # leer, als Anleitung
    assert "Das hat nicht geklappt" in SEITE  # fehler, mit nächstem Schritt


def test_pruefliste_und_ausgleichswahl_sind_bedienbar():
    """Ein Ausgleich muss abhakbar sein, sonst ist er kein Vermerk."""
    assert "Zu prüfen" in SEITE
    assert "/api/vermerk/abhaken" in SEITE
    for art in ("AUSGLEICH", "VERBATIM", "ANTEILIG"):
        assert f'value="{art}"' in SEITE


def test_verbatim_kann_nicht_gebucht_werden():
    """1067 kg unter der Überschrift 1000 kg gehören in kein Protokoll."""
    assert 'a.auftrag.ausgleich === "VERBATIM"' in SEITE
