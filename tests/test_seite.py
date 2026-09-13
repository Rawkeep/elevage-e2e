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
    assert 'txt("Lade …")' in SEITE  # laden
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


def test_beim_abhaken_wird_nach_dem_mittel_gefragt():
    """Ohne diese Angabe lässt sich keine Wartezeit rechnen."""
    assert "Welches Mittel wurde gegeben?" in SEITE
    assert "function frageMittel(" in SEITE
    assert "praeparat: mittel" in SEITE


def test_die_wartezeit_hat_einen_eigenen_kasten():
    assert 'id="sperre"' in SEITE
    assert "gesperrt bis" in SEITE


def test_abgaenge_lassen_sich_buchen():
    """Ohne sie rechnet der Futterbedarf auf Tiere, die nicht mehr da sind."""
    assert "Abgang buchen" in SEITE
    assert "/api/abgang" in SEITE
    assert "Verkauft ist kein Verlust" in SEITE


def test_die_seite_ueberlebt_ein_funkloch():
    """Offline war Qualitätsattribut Nr. 1 im Briefing."""
    from elevage.seite import DIENER

    assert 'navigator.serviceWorker.register("/sw.js")' in SEITE
    assert "SEITE_VORRAT" in DIENER and "DATEN_VORRAT" in DIENER
    # Seite aus dem Vorrat, Daten aus dem Netz: sonst arbeitet jemand mit gestern
    assert "caches.match(anfrage).then((alt) => alt || fetch(anfrage)" in DIENER
    assert "fetch(anfrage).then((antwort)" in DIENER


def test_eingaben_gehen_im_funkloch_nicht_verloren():
    assert "taktgeber-warteschlange" in SEITE
    assert "function sendeOderMerken" in SEITE or "async function sendeOderMerken" in SEITE
    assert "wird nachgereicht" in SEITE
    for pfad in ("/api/quittung", "/api/abgang", "/api/vorfall"):
        assert f'"{pfad}"' in SEITE


def test_nur_idempotente_wege_werden_nachgereicht():
    """Ein Mischauftrag braucht eine Antwort — den darf man nicht merken."""
    schlange = SEITE[SEITE.index("const NACHREICHBAR") : SEITE.index("function schlange")]
    assert "/api/mischung" not in schlange
    assert "/api/praeparat" not in schlange


def test_die_kopfzeile_zeigt_den_echten_bestand_nicht_die_einstallzahl():
    """Ein Fund der sehenden Abnahme: die Zahl war nie ausgetauscht worden."""
    assert "bild.bestand" in SEITE
    assert "stand ? stand.tierzahl : bild.herde.tierzahl" in SEITE
    assert "verlusteProzent" in SEITE


def test_die_uebersetzungsfunktion_heisst_nicht_t():
    """`t` ist in diesem Skript überall der Termin. Ein verdeckter Name
    ergibt zur Laufzeit einen Fehler, den kein Python-Test sieht."""
    import re

    assert "function txt(text)" in SEITE
    code = [
        zeile
        for zeile in SEITE[SEITE.index("<script>") :].splitlines()
        if not zeile.lstrip().startswith("//")  # Kommentare dürfen t() nennen
    ]
    uebrig = re.findall(r"(?<![A-Za-z0-9_.$])t\(", "\n".join(code))
    assert not uebrig, f"{len(uebrig)} Aufruf(e) der alten Funktion übrig"


def test_nichts_darf_die_seite_quer_schieben():
    """Unter 768 px lief die Seite über: ein <select> wächst auf die Breite
    seiner längsten Option, wenn sein Kasten nicht schrumpfen darf. Gemessen
    wurde das im Browser über acht Breiten; hier stehen die Regeln, die es
    verhindern."""
    for regel in (
        "max-width: 100%",  # kein Feld über den Rand
        ".kopf > .feld { flex: 1 1 11rem; min-width: 0; }",
        "flex-wrap: wrap",  # Kopfzeile darf umbrechen
        "text-overflow: ellipsis",  # langer Herdenname wird gekürzt
        "overflow-wrap: anywhere",  # lange Präparatlisten brechen um
        ".breit { overflow-x: auto; }",  # nur die Tabelle scrollt, nie die Seite
    ):
        assert regel in SEITE, regel


def test_glas_hat_einen_rueckweg():
    """Optik darf die Lesbarkeit nicht kosten: wo der Browser kein
    backdrop-filter kann oder jemand weniger Transparenz eingestellt hat,
    werden dieselben Flächen deckend gezeichnet."""
    assert "backdrop-filter: var(--blur)" in SEITE
    assert "-webkit-backdrop-filter" in SEITE
    assert "@supports not (backdrop-filter: blur(1px))" in SEITE
    assert "prefers-reduced-transparency: reduce" in SEITE
    assert SEITE.count("--glas: var(--grund)") == 2  # beide Rückwege


def test_der_grund_kostet_keine_bytes():
    """Das Glas braucht etwas zum Durchscheinen — aber kein Bild."""
    assert "radial-gradient" in SEITE
    assert "url(" not in SEITE.split("<script>")[0].replace("data:image/svg+xml", "")


def test_die_seite_steht_in_wenigen_karten():
    """Elf gestapelte Karten waren auf jeder Breite eine Wand. Die Abschnitte
    leben jetzt als Blöcke in vier Karten (Stand, Was zu tun ist, Eintragen,
    Zu prüfen); dazu kommen Band, Kopfzeile und Zustandszeile — die Zahl ist
    der Test."""
    assert SEITE.count('class="karte glas') <= 7
    for klasse in (".raster", ".spalte", ".stand", ".block"):
        assert klasse in SEITE, klasse
    # Zwei Spalten erst, wenn Platz da ist; darunter bleibt es eine Säule.
    assert "@media (min-width: 62rem)" in SEITE


def test_eine_sammelkarte_ohne_inhalt_verschwindet():
    """Sonst stünde „Zu prüfen" über dem Nichts."""
    assert "function karten()" in SEITE
    assert 'querySelectorAll("[data-sammel]")' in SEITE
    assert SEITE.count("data-sammel") == 3  # CSS-Wahl plus zwei Karten


def test_rasterkinder_duerfen_schrumpfen():
    """Ohne min-width:0 schiebt ein Rasterkind die Seite quer — bei 320 px
    waren es fünf Pixel, gemessen im Browser."""
    assert ".raster > *, .spalte > *, .stand > * { min-width: 0; }" in SEITE


def test_selten_gebrauchtes_liegt_zugeklappt():
    """Abgang, Vorfall und die erledigten Schritte sind nicht das Tagesgeschäft."""
    assert SEITE.count("<summary>") >= 3
    assert "<details" in SEITE
