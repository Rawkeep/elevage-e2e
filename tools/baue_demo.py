"""Erzeugt die statische Demo für GitHub Pages aus der echten Engine.

**Es gibt nur eine Oberfläche.** Die Demo ist dieselbe `seite.SEITE`, davor
geschoben eine Attrappe für `fetch`, die vorgerechnete Antworten liefert
statt den Server zu fragen. So kann die Demo nicht von der Anwendung
abdriften — sie *ist* die Anwendung, nur ohne Rückseite.

Die Zahlen kommen aus `takt.rechne()` mit festem Stichtag und erfundenen
Betriebsdaten. Deterministisch: derselbe Lauf ergibt dieselbe Datei, ein
Test rechnet das nach.

    python3 -m tools.baue_demo        # schreibt docs/index.html
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from elevage.anpassung import wirksames_rezept
from elevage.mischung import baue_mischauftrag
from elevage.models import (
    Ausgleichsart,
    Ereignis,
    EreignisArt,
    Herde,
    Pruefvermerk,
    Quittung,
    Tierart,
    Tierarzt,
)
from elevage.programme import alle_programme
from elevage.seite import SEITE
from elevage.takt import rechne
from elevage.vergleich import vergleiche
from elevage.verzehr import aus_mischungen, kombiniere, richtwert

WURZEL = Path(__file__).resolve().parents[1]
ZIEL = WURZEL / "docs" / "index.html"

STICHTAG = date(2026, 4, 30)
EINSTALL = date(2026, 3, 2)
ERLEDIGT_AB_TAGEN = 6
"""Was länger zurückliegt, gilt in der Demo als abgehakt — sonst sieht man
nur eine Wand aus Überfälligem statt des Takts."""

HERDE = Herde(
    tenant_id="demo",
    herde_id="H1",
    name="Stall Nord",
    tierart=Tierart.LEGEHENNE,
    einstalldatum=EINSTALL,
    tierzahl=1200,
)

TIERARZT = Tierarzt(
    tenant_id="demo",
    name="Dr. A. Mensah",
    praxis="Tierarztpraxis Kara",
    telefon="00 00 00 00",
    hinweis="Erfunden wie die übrigen Demo-Daten — echte Kontaktdaten stehen "
    "in keiner öffentlichen Seite.",
)
"""Bewusst erfunden: die Demo läuft öffentlich, und der Tierarzt auf dem
echten Blatt ist eine Person mit Telefonnummer."""

VORFALL = Ereignis(
    tenant_id="demo",
    herde_id="H1",
    ereignis_id="V1",
    art=EreignisArt.GUMBORO,
    festgestellt_am=STICHTAG - timedelta(days=2),
    bemerkung="Tiere apathisch, Kot wässrig",
)

MISCHUNGEN = [(EINSTALL + timedelta(days=7 * n), 150.0 + 60.0 * n) for n in range(1, 9)]
"""Acht wöchentliche Mischungen — damit die Verzehrkurve bis in die laufende
Woche etwas Gemessenes hat und die Demo nicht auf Richtwerten steht."""


def _bild(
    quittungen: list[Quittung],
    vermerke: list[Pruefvermerk],
    programm_id: str | None = None,
) -> Any:
    gemessen, kurven_issues = aus_mischungen(
        HERDE.tierart, HERDE.tierzahl, HERDE.einstalldatum, MISCHUNGEN
    )
    herde = HERDE.model_copy(update={"programm_id": programm_id})
    return rechne(
        herde,
        STICHTAG,
        quittungen,
        [VORFALL],
        kurve=kombiniere(gemessen, richtwert(HERDE.tierart)),
        vorrat_kg=650.0,
        kurven_issues=kurven_issues,
        vermerke=vermerke,
        tierarzt=TIERARZT,
    )


def _quittungen(programm_id: str | None) -> list[Quittung]:
    """Was länger zurückliegt, gilt als abgehakt — je Blatt neu gerechnet,
    weil die Schrittschlüssel des einen im anderen nicht vorkommen."""
    roh = _bild([], [], programm_id)
    return [
        Quittung(
            tenant_id="demo",
            herde_id="H1",
            schritt_key=t.schritt_key,
            quittung_id=f"demo-{t.schritt_key}",
            erledigt_am=t.faellig_von,
            durch="Kofi A.",
            lot="LOT-4711",
        )
        for t in roh.ueberfaellig
        if (STICHTAG - t.faellig_bis).days > ERLEDIGT_AB_TAGEN
    ]


def baue_daten() -> dict[str, Any]:
    roh = _bild([], [])
    quittungen = _quittungen(None)

    phase = roh.phase
    auftraege: dict[str, Any] = {}
    vermerke: list[Pruefvermerk] = []
    if phase is not None:
        wirksam = wirksames_rezept(phase, [])
        for art in Ausgleichsart:
            for menge in (500, 1000):
                auftrag = baue_mischauftrag(wirksam, menge, art=art)
                auftraege[f"{art.value}:{menge}"] = auftrag.model_dump(by_alias=True, mode="json")
        vermerke.append(
            Pruefvermerk(
                tenant_id="demo",
                vermerk_id=f"ausgleich:{wirksam.key}",
                betrifft=f"Rezept {wirksam.key}",
                text=next(
                    i for i in baue_mischauftrag(wirksam, 1000).issues if "Ausgeglichen" in i
                ),
                angelegt_am=STICHTAG - timedelta(days=9),
            )
        )

    bild = _bild(quittungen, vermerke)

    # Jedes Blatt einmal durchgerechnet: in der Demo wechselt das Programm
    # wirklich den Plan, statt nur die Überschrift zu tauschen.
    blaetter = alle_programme(HERDE.tierart)
    bilder = {
        x.programm_id: _bild(_quittungen(x.programm_id), vermerke, x.programm_id).model_dump(
            by_alias=True, mode="json"
        )
        for x in blaetter
    }
    gegenueber = {
        f"{links.programm_id}|{rechts.programm_id}": vergleiche(links, rechts).model_dump(
            by_alias=True, mode="json"
        )
        for links in blaetter
        for rechts in blaetter
        if links is not rechts
    }

    return {
        "ich": {"tenantId": "demo", "benutzerId": "kofi", "name": "Kofi A.", "rolle": "LEITUNG"},
        "herden": [HERDE.model_dump(by_alias=True, mode="json")],
        "tagesbild": bild.model_dump(by_alias=True, mode="json"),
        "bilder": bilder,
        "programme": [
            {
                "programmId": x.programm_id,
                "titel": x.titel,
                "tierart": x.tierart.value,
                "herausgeber": x.herausgeber or x.quelle,
                "vorgabe": x.vorgabe,
                "schritte": len(x.schritte),
                "dauerregeln": len(x.dauerregeln),
                "hinweise": x.hinweise,
            }
            for x in alle_programme()
        ],
        "vergleiche": gegenueber,
        "auftraege": auftraege,
        "stichtag": STICHTAG.isoformat(),
    }


ATTRAPPE = """
<div id="demo-band" style="background:#8a6412;color:#fff;padding:10px 16px;
     font:600 15px/1.5 system-ui,sans-serif;text-align:center">
  Demo mit erfundenen Betriebsdaten — Stichtag DATUM_HIER.
  Eingaben bleiben im Browser, es wird nichts gespeichert.
  <a href="https://github.com/Rawkeep/elevage-e2e" style="color:#fff">Quelltext</a>
</div>
<script>
// Attrappe für fetch: dieselbe Seite, nur ohne Rückseite. Abhaken wirkt
// im Speicher dieser Registerkarte, damit der Takt sichtbar wird — mehr
// verspricht das Band oben auch nicht.
const DEMO = DATEN_HIER;

// Das gewählte Blatt übersteht ein Neuladen — der Sprachwechsel lädt die
// Seite neu, und ohne das spränge die Demo stillschweigend zurück auf das
// Vorgabe-Blatt. In der Anwendung steht die Wahl in der Datenbank; die
// Demo hat keine, also merkt sie sich das eine Feld für diese Registerkarte.
const DEMO_BLATT = "taktgeber-demo-programm";
try {
  const gemerkt = sessionStorage.getItem(DEMO_BLATT);
  if (gemerkt && DEMO.bilder[gemerkt]) {
    DEMO.tagesbild = DEMO.bilder[gemerkt];
    DEMO.herden[0].programmId = gemerkt;
  }
} catch (f) {}

const antwort = (inhalt, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(inhalt),
    { status, headers: { "content-type": "application/json" } }));

function verschiebe(schrittKey, erledigt) {
  const bild = DEMO.tagesbild;
  const toepfe = ["ueberfaellig", "heute", "demnaechst", "bestellen", "erledigt"];
  let posten = null;
  for (const topf of toepfe) {
    const stelle = bild[topf].findIndex((t) => t.schrittKey === schrittKey);
    if (stelle >= 0) { posten = bild[topf].splice(stelle, 1)[0]; break; }
  }
  if (!posten) return;
  if (erledigt) {
    posten.ampel = "ERLEDIGT";
    posten.erledigtAm = DEMO.stichtag;
    posten.lot = "LOT-4711";
    bild.erledigt.push(posten);
  } else {
    posten.ampel = "ROT";
    posten.erledigtAm = null;
    posten.lot = null;
    bild.ueberfaellig.push(posten);
  }
  bild.ampel = bild.ueberfaellig.length ? "ROT" : (bild.heute.length ? "GELB" : "GRUEN");
}

const echtesFetch = window.fetch.bind(window);
window.fetch = async (pfad, optionen) => {
  if (typeof pfad !== "string" || !pfad.startsWith("/api/")) {
    return echtesFetch(pfad, optionen);
  }
  const daten = optionen && optionen.body ? JSON.parse(optionen.body) : {};
  if (pfad === "/api/ich") return antwort(DEMO.ich);
  if (pfad.startsWith("/api/herden")) return antwort({ herden: DEMO.herden });
  if (pfad.startsWith("/api/tagesbild")) return antwort(DEMO.tagesbild);
  if (pfad.startsWith("/api/programme")) return antwort({ programme: DEMO.programme });
  if (pfad.startsWith("/api/vergleich")) {
    const frage = new URLSearchParams(pfad.split("?")[1] || "");
    const treffer = DEMO.vergleiche[frage.get("links") + "|" + frage.get("rechts")];
    if (!treffer) return antwort({ fehler: "In der Demo nicht gerechnet." }, 400);
    return antwort(treffer);
  }
  if (pfad === "/api/programm") {
    // Der Wechsel ist echt: jedes Blatt ist vorgerechnet mitgeliefert.
    const anderes = DEMO.bilder[daten.programm];
    if (!anderes) return antwort({ fehler: "In der Demo nicht gerechnet." }, 400);
    DEMO.tagesbild = anderes;
    DEMO.herden[0].programmId = daten.programm;
    try { sessionStorage.setItem(DEMO_BLATT, daten.programm); } catch (f) {}
    return antwort({ herde: DEMO.herden[0] });
  }
  if (pfad === "/api/quittung") {
    verschiebe(daten.schritt, true);
    return antwort({ neu: true, quittungId: daten.schritt });
  }
  if (pfad === "/api/quittung/widerrufen") {
    verschiebe(daten.quittungId, false);
    return antwort({ widerrufen: true });
  }
  if (pfad === "/api/mischung") {
    const auftrag = DEMO.auftraege[(daten.art || "AUSGLEICH") + ":" + daten.kg];
    if (!auftrag) {
      return antwort({ fehler: "In der Demo sind nur 500 und 1000 kg gerechnet." }, 400);
    }
    return antwort({ auftrag: auftrag, gebucht: false });
  }
  if (pfad === "/api/vermerk/abhaken") {
    DEMO.tagesbild.vermerke = DEMO.tagesbild.vermerke.filter(
      (v) => v.vermerkId !== daten.vermerkId);
    return antwort({ abgehakt: true });
  }
  if (pfad === "/api/vorfall") {
    return antwort({ fehler: "In der Demo nicht möglich — das Schema läuft bereits." }, 400);
  }
  if (pfad === "/api/abmelden") return antwort({ abgemeldet: true });
  return antwort({ fehler: "In der Demo nicht vorhanden." }, 404);
};
</script>
"""


def baue_seite() -> str:
    daten = json.dumps(baue_daten(), ensure_ascii=False, sort_keys=True, indent=None)
    attrappe = ATTRAPPE.replace("DATEN_HIER", daten).replace(
        "DATUM_HIER", STICHTAG.strftime("%d.%m.%Y")
    )
    # Direkt vor den Skriptblock der Seite, damit fetch schon ersetzt ist.
    marke = "<script>\nconst $ = (id) => document.getElementById(id);"
    if marke not in SEITE:
        raise RuntimeError("Ankerpunkt in seite.SEITE nicht gefunden")
    seite = SEITE.replace(marke, attrappe + marke)
    # Der Stichtag der Demo statt des heutigen Datums.
    return seite.replace(
        "const heute = () => new Date().toISOString().slice(0, 10);",
        f'const heute = () => "{STICHTAG.isoformat()}";',
    )


def main() -> int:
    ZIEL.parent.mkdir(parents=True, exist_ok=True)
    ZIEL.write_text(baue_seite(), encoding="utf-8")
    (ZIEL.parent / ".nojekyll").write_text("", encoding="utf-8")
    print(f"{ZIEL.relative_to(WURZEL)} geschrieben ({ZIEL.stat().st_size} Bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
