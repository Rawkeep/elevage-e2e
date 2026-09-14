"""Die ganze Oberfläche als ein String — kein Build, kein CDN.

Gestaltet nach dem Architektur-Briefing (Branche Agrar, Zielgruppe intern):
erdige Töne statt Agrar-Grün-Klischee, große Schrift und Touch-Ziele ab
44 px für die Bedienung im Stehen und mit Handschuhen, wenig Bytes für
schmale Leitungen, Dark Mode über Tokens, Bewegung nur mit
`prefers-reduced-motion`. Farbe trägt nie allein — jede Ampel hat zusätzlich
ein Zeichen und ein Wort.

**Glas mit Rückweg.** Die Flächen sind durchscheinend (`backdrop-filter`)
über einem ruhigen Grund aus zwei CSS-Farbfeldern — kein Bild, keine Bytes.
Das ist Optik, kein Selbstzweck, und sie darf die Lesbarkeit nicht kosten:
die Trägerflächen bleiben deckend genug für Kontrast über 4,5:1, und wo der
Browser kein `backdrop-filter` kann oder jemand weniger Transparenz
eingestellt hat, werden dieselben Flächen deckend gezeichnet.

**Jede Breite ohne Querscroll.** Jedes Bedienfeld sitzt in einem `.feld` mit
`min-width: 0`. Ohne das wächst ein `<select>` auf die Breite seiner
längsten Option und schiebt die ganze Seite quer.

Die drei Seiten teilen sich Grundlagen, Übersetzer und Zusammenbau — eine
Quelle, nicht drei. `test_seite.py` hält fest, dass hier keine externe
Adresse steht.
"""

from __future__ import annotations

from elevage.sprache import woerterbuch

DIENER = """// Service Worker: die Seite muss auch ohne Netz aufgehen.
//
// Zwei getrennte Vorräte, weil sie Verschiedenes bedeuten: die SEITE ist
// unveränderlich (cache first, sonst wäre der Stall bei jedem Funkloch
// weiß), die DATEN sind es nicht (network first, damit niemand mit einem
// Tagesbild von gestern arbeitet, wenn ein frisches erreichbar ist).
const SEITE_VORRAT = "taktgeber-seite-v2";
const DATEN_VORRAT = "taktgeber-daten-v2";
const SEITENPFADE = ["/", "/anmelden"];

self.addEventListener("install", (ereignis) => {
  ereignis.waitUntil(
    caches.open(SEITE_VORRAT).then((vorrat) => vorrat.addAll(SEITENPFADE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (ereignis) => {
  ereignis.waitUntil(
    caches.keys()
      .then((namen) => Promise.all(namen
        .filter((n) => n !== SEITE_VORRAT && n !== DATEN_VORRAT)
        .map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (ereignis) => {
  const anfrage = ereignis.request;
  if (anfrage.method !== "GET") return;  // Schreiben regelt die Warteschlange
  const pfad = new URL(anfrage.url).pathname;

  if (pfad.startsWith("/api/")) {
    ereignis.respondWith(
      fetch(anfrage).then((antwort) => {
        if (antwort.ok) {
          const kopie = antwort.clone();
          caches.open(DATEN_VORRAT).then((v) => v.put(anfrage, kopie));
        }
        return antwort;
      }).catch(() => caches.match(anfrage).then((alt) => alt || new Response(
        JSON.stringify({ fehler: "Kein Netz und nichts im Zwischenspeicher." }),
        { status: 503, headers: { "content-type": "application/json" } }
      )))
    );
    return;
  }

  ereignis.respondWith(
    caches.match(anfrage).then((alt) => alt || fetch(anfrage).then((antwort) => {
      if (antwort.ok && SEITENPFADE.includes(pfad)) {
        const kopie = antwort.clone();
        caches.open(SEITE_VORRAT).then((v) => v.put(anfrage, kopie));
      }
      return antwort;
    }))
  );
});
"""
"""Der Service Worker als String — wie die Seite, kein Build, keine Datei."""


FAVICON = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E"
    "%3Crect width='16' height='16' rx='3' fill='%23134e57'/%3E"
    "%3Crect x='4' y='3.5' width='8' height='2' rx='1' fill='%23faf7f2'/%3E"
    "%3Crect x='4' y='7' width='8' height='2' rx='1' fill='%23e0b352'/%3E"
    "%3Crect x='4' y='10.5' width='8' height='2' rx='1' fill='%23f09077'/%3E"
    "%3C/svg%3E"
)
"""Drei Balken in Rot, Gelb, Grün — das Zeichen der Seite, inline statt Datei.

Ohne dieses Zeichen fragt jeder Browser /favicon.ico an und bekommt 404."""


ZEICHEN = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 192 192'>"
    "<rect width='192' height='192' rx='36' fill='#134e57'/>"
    "<rect x='48' y='42' width='96' height='24' rx='12' fill='#faf7f2'/>"
    "<rect x='48' y='84' width='96' height='24' rx='12' fill='#e0b352'/>"
    "<rect x='48' y='126' width='96' height='24' rx='12' fill='#f09077'/>"
    "</svg>"
)
"""Dasselbe Zeichen wie das Favicon, nur groß — für den Startbildschirm.

Ein SVG statt PNG: ein Bild in jeder Größe, ohne Datei und ohne Bytes zu
verschwenden. Ausgeliefert wird es vom eigenen Server, nicht als data:-URL —
einige Browser laden Manifest-Icons nicht aus data:."""

MANIFEST = """{
  "name": "Taktgeber — Prophylaxe und F\\u00fctterung",
  "short_name": "Taktgeber",
  "description": "Impftermine, Futterwechsel und Mischauftr\\u00e4ge je Herde.",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait-primary",
  "background_color": "#f6f1e9",
  "theme_color": "#134e57",
  "lang": "fr",
  "icons": [
    {"src": "/zeichen.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
    {"src": "/zeichen.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "maskable"}
  ]
}
"""
"""Ohne Manifest ist es eine Webseite, mit Manifest eine App.

`display: standalone` nimmt die Adressleiste weg, `start_url` und `scope`
halten die Installation auf dieser Anwendung. Die Farben sind die des
Themas — sonst blitzt beim Start ein weißer Rahmen auf."""


UEBERSETZER = """
// Nur die Oberfläche wird über dieses Wörterbuch übersetzt. Präparatnamen
// und Rezeptposten bleiben, wie sie sind; Schritte und Befunde tragen ihre
// zweite Fassung am Datensatz (titelFr, hinweisFr, textFr) — dafür ist
// `wortlaut()` da, nicht dieses Wörterbuch.
const WOERTER = WOERTERBUCH_HIER;
// Französisch ist die Vorgabe: die Blätter sind französisch, der Stall auch.
let SPRACHE = "fr";
try { SPRACHE = localStorage.getItem("taktgeber-sprache") || "fr"; } catch (f) {}

function txt(text) {
  // Heißt NICHT t(): so heißt in diesem Skript überall der Termin, und ein
  // verdeckter Name ergibt zur Laufzeit "t is not a function".
  const buch = WOERTER[SPRACHE];
  return (buch && buch[text]) || text;   // fehlt eine Vokabel: deutscher Text
}

// Kommandos bleiben, wie sie sind — eine übersetzte Kommandozeile
// funktioniert nicht mehr.
const UNBERUEHRT = ["CODE", "PRE", "SAMP", "KBD", "SCRIPT", "STYLE"];

function uebersetzeSeite() {
  // Die Sprachkennung gehört ans Dokument, bevor irgendetwas abbricht —
  // Vorleser und Rechtschreibprüfung lesen sie.
  document.documentElement.lang = SPRACHE;
  if (SPRACHE === "de") return;
  const lauf = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const knoten = [];
  while (lauf.nextNode()) knoten.push(lauf.currentNode);
  knoten.forEach((k) => {
    if (!k.parentElement || UNBERUEHRT.includes(k.parentElement.tagName)) return;
    const roh = k.nodeValue.trim();
    if (!roh) return;
    // Ein Absatz im Markup trägt Umbrüche und Einrückung. Nachgeschlagen
    // wird die geglättete Fassung, ersetzt wird das gefundene Stück.
    const flach = roh.replace(/\\s+/g, " ");
    const uebersetzt = txt(flach);
    if (uebersetzt !== flach) k.nodeValue = k.nodeValue.replace(roh, uebersetzt);
  });
  document.querySelectorAll("[placeholder]").forEach((feld) => {
    feld.placeholder = txt(feld.placeholder);
  });
  document.documentElement.lang = SPRACHE;
}

function sprachwahl(kennung) {
  const wahl = document.getElementById(kennung);
  wahl.value = SPRACHE;
  wahl.onchange = () => {
    try { localStorage.setItem("taktgeber-sprache", wahl.value); } catch (f) {}
    window.location.reload();   // einmal sauber neu aufbauen statt halb übersetzt
  };
}
"""
"""Derselbe Übersetzungslauf für alle drei Seiten — einer, nicht drei."""


GRUNDLAGEN = """
:root {
  color-scheme: light dark;

  /* Erdige Grundtöne — bewusst gegen das Agrar-Grün-Klischee. */
  --grund:      #f6f1e9;
  --grund-2:    #efe7db;
  --glas:       rgba(255, 255, 255, .74);
  --glas-stark: rgba(255, 255, 255, .90);
  --kante:      rgba(120, 96, 68, .22);
  --glanz:      rgba(255, 255, 255, .65);
  --schatten:   0 1px 2px rgba(60, 44, 26, .06), 0 8px 24px rgba(60, 44, 26, .07);

  --text:       #221b13;
  --leise:      #57493c;
  --terrakotta: #8f3418;
  --petrol:     #0f4a54;
  --ocker:      #7a5709;

  --rot-feld:   rgba(178, 64, 32, .10);
  --gelb-feld:  rgba(190, 140, 20, .13);
  --gruen-feld: rgba(15, 74, 84, .09);

  --schrift: 17px;
  --radius: 14px;
  --ziel: 44px;
  --blur: blur(16px) saturate(150%);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-thema="hell"]) {
    --grund:      #14100d;
    --grund-2:    #1c1712;
    --glas:       rgba(44, 37, 30, .70);
    --glas-stark: rgba(48, 40, 33, .88);
    --kante:      rgba(226, 205, 176, .17);
    --glanz:      rgba(255, 236, 210, .10);
    --schatten:   0 1px 2px rgba(0, 0, 0, .35), 0 10px 30px rgba(0, 0, 0, .40);

    --text:       #f4ece2;
    --leise:      #c3b3a0;
    --terrakotta: #ff9c7f;
    --petrol:     #86cdd8;
    --ocker:      #e8bd5e;

    --rot-feld:   rgba(255, 120, 80, .14);
    --gelb-feld:  rgba(232, 189, 94, .14);
    --gruen-feld: rgba(134, 205, 216, .12);
  }
}

:root[data-thema="dunkel"] {
  --grund:      #14100d;
  --grund-2:    #1c1712;
  --glas:       rgba(44, 37, 30, .70);
  --glas-stark: rgba(48, 40, 33, .88);
  --kante:      rgba(226, 205, 176, .17);
  --glanz:      rgba(255, 236, 210, .10);
  --schatten:   0 1px 2px rgba(0, 0, 0, .35), 0 10px 30px rgba(0, 0, 0, .40);

  --text:       #f4ece2;
  --leise:      #c3b3a0;
  --terrakotta: #ff9c7f;
  --petrol:     #86cdd8;
  --ocker:      #e8bd5e;

  --rot-feld:   rgba(255, 120, 80, .14);
  --gelb-feld:  rgba(232, 189, 94, .14);
  --gruen-feld: rgba(134, 205, 216, .12);
}

* { box-sizing: border-box; }

body {
  margin: 0;
  min-height: 100vh;
  background: var(--grund);
  /* Zwei weiche Farbfelder als Grund — reines CSS, kein Bild, keine Bytes.
     Sie geben dem Glas etwas zum Durchscheinen; ohne sie wäre es nur grau. */
  background-image:
    radial-gradient(60rem 40rem at 12% -10%, rgba(15, 74, 84, .16), transparent 60%),
    radial-gradient(50rem 36rem at 105% 8%, rgba(178, 84, 40, .14), transparent 62%),
    linear-gradient(180deg, var(--grund) 0%, var(--grund-2) 100%);
  background-attachment: fixed;
  color: var(--text);
  font: var(--schrift)/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}

/* Glas ist Optik, nicht Funktion: wo der Browser es nicht kann oder der
   Mensch weniger Transparenz eingestellt hat, wird dieselbe Fläche deckend
   gezeichnet. Der Text bleibt in jedem Fall lesbar. */
@supports not (backdrop-filter: blur(1px)) {
  :root { --glas: var(--grund); --glas-stark: var(--grund); --blur: none; }
}
@media (prefers-reduced-transparency: reduce) {
  :root { --glas: var(--grund); --glas-stark: var(--grund); --blur: none; }
}

.glas {
  background: var(--glas);
  backdrop-filter: var(--blur);
  -webkit-backdrop-filter: var(--blur);
  border: 1px solid var(--kante);
  border-radius: var(--radius);
  box-shadow: var(--schatten), inset 0 1px 0 var(--glanz);
}

select, input, button {
  font: inherit;
  min-height: var(--ziel);
  max-width: 100%;
  border-radius: 10px;
  border: 1px solid var(--kante);
  background: var(--glas-stark);
  color: var(--text);
  padding: 6px 12px;
}
button { cursor: pointer; }
button:focus-visible, select:focus-visible, input:focus-visible {
  outline: 3px solid var(--ocker); outline-offset: 2px;
}
label { display: block; font-size: .82rem; color: var(--leise); margin-bottom: 4px; }
[hidden] { display: none !important; }
"""

BAUSTEINE = """
.huelle { max-width: 72rem; margin: 0 auto; padding: 16px; }
.karte { padding: 18px; margin-bottom: 14px; }

/* Auf breiten Schirmen zwei Spalten: links, was zu tun ist, rechts der
   Stand und die Eingaben. Eine einzige Spalte lässt 1920 px zu 80 %
   leer und macht aus jeder Seite eine Wand. */
.raster { display: grid; gap: 14px; align-items: start; }
/* Rasterkinder schrumpfen sonst nicht unter ihre min-content-Breite und
   schieben die Seite quer — bei 320 px waren es fünf Pixel. */
.raster > *, .spalte > *, .stand > * { min-width: 0; }
@media (min-width: 62rem) {
  .raster { grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr); }
  .raster > .karte, .spalte > .karte { margin-bottom: 0; }
  .spalte { display: grid; gap: 14px; align-content: start; }
}

h1 { font-size: 1.5rem; margin: 0 0 2px; letter-spacing: -.01em; }
h2 {
  font-size: .82rem; margin: 0 0 14px; letter-spacing: .09em;
  text-transform: uppercase; color: var(--leise);
}
/* Untergruppen tragen keine eigene Karte mehr, nur eine leise Marke. */
h3 {
  font-size: .78rem; margin: 18px 0 8px; letter-spacing: .07em;
  text-transform: uppercase; color: var(--leise); font-weight: 650;
}
h2 + .block > h3, .stand > .block > h3 { margin-top: 0; }

/* Der Stand ist ein Streifen, keine Säule: was nebeneinander passt,
   steht nebeneinander. */
.stand { display: grid; gap: 14px 22px; grid-template-columns: 1fr; }
@media (min-width: 46rem) {
  .stand { grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); }
}
.leise { color: var(--leise); font-size: .92rem; }
.winzig { font-size: .84rem; }

/* Jede Zeile darf umbrechen, und jedes Kind darf schrumpfen. Ohne
   min-width:0 wächst ein <select> auf die Breite seiner längsten Option
   und schiebt die ganze Seite quer — genau das war der Fehler. */
.kopf { display: flex; flex-wrap: wrap; gap: 10px 12px; align-items: flex-end; }
.kopf > .feld { flex: 1 1 11rem; min-width: 0; }
.kopf > .feld.schmal { flex: 1 1 7rem; }
.kopf > button { flex: 0 0 auto; }
/* Auf dem Handy ist der Knopf die Handlung: volle Breite, ein Ziel fuer
   den Daumen statt eines Restes am Zeilenende. */
@media (max-width: 30rem) { .kopf > button.tat { flex: 1 1 100%; } }
.feld > select, .feld > input { width: 100%; }
select { text-overflow: ellipsis; }

button.tat {
  background: var(--petrol); border-color: transparent;
  color: var(--grund); font-weight: 650;
}
button.still { background: transparent; }
button:hover { border-color: var(--petrol); }

.reihe {
  display: flex; flex-wrap: wrap; gap: 8px 12px;
  align-items: flex-start; justify-content: space-between;
}
li.posten .reihe > :first-child { flex: 1 1 16rem; min-width: 0; }
li.posten .reihe > :last-child { flex: 0 0 auto; text-align: right; }
header .reihe { align-items: center; }
.werkzeuge { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
/* Sprache, Ansicht und Abmelden sind Einstellungen, keine Arbeit. Auf dem
   Handy liegen sie hinter einem Knopf; am Schirm ist Platz, da stehen sie. */
.menue { border: 0; padding: 0; margin: 0; }
.menue > summary { min-height: var(--ziel); justify-content: center; }
.menue > summary::before { display: none; }
.menue > summary > span { font-size: 1.5rem; line-height: 1; }
/* Zugeklappt heisst zugeklappt: `.werkzeuge` setzt display:flex, und das
   schlaegt die Browser-Regel, die die Kinder eines geschlossenen <details>
   versteckt. Derselbe Stolperstein wie beim Toast. */
.menue:not([open]) > .werkzeuge { display: none; }
.menue > :not(summary) { margin-top: 10px; }
@media (max-width: 61.99rem) {
  .menue[open] > .werkzeuge {
    position: absolute; inset-inline-end: 0; inset-block-start: 100%;
    z-index: 15; flex-direction: column; align-items: stretch;
    min-width: 13rem; padding: 12px; border-radius: var(--radius);
    background: var(--glas-stark); border: 1px solid var(--kante);
    box-shadow: var(--schatten);
    -webkit-backdrop-filter: var(--blur); backdrop-filter: var(--blur);
  }
  header .reihe { position: relative; }
}
@media (min-width: 62rem) {
  .menue > summary { display: none; }
  .menue > :not(summary) { margin-top: 0; }
  .menue { display: block; }
}
.werkzeuge label { margin: 0; }
.werkzeuge select, .werkzeuge button { min-height: 38px; }

/* Der Stand als Wertetafel statt als drei Karten. */
.tafel { display: grid; gap: 10px 18px; grid-template-columns: 1fr; }
@media (min-width: 26rem) { .tafel { grid-template-columns: auto 1fr; } }
.tafel dt {
  font-size: .78rem; letter-spacing: .06em; text-transform: uppercase;
  color: var(--leise); align-self: baseline;
}
.tafel dd { margin: 0; min-width: 0; overflow-wrap: anywhere; }

/* Die Antwortzeile: der einzige große Text der Seite außer dem Titel. */
.jetzt { display: flex; flex-direction: column; gap: 4px; }
.jetzt-satz {
  margin: 0; font-size: 1.15rem; font-weight: 700; line-height: 1.35;
  display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;
}
.jetzt-dazu { margin: 0; font-size: .95rem; }
.jetzt.ROT .jetzt-satz { color: var(--terrakotta); }
.jetzt.GELB .jetzt-satz { color: var(--ocker); }
.jetzt.GRUEN .jetzt-satz { color: var(--petrol); }
@media (min-width: 46rem) { .jetzt-satz { font-size: 1.3rem; } }

.ROT { color: var(--terrakotta); }
.GELB { color: var(--ocker); }
.GRUEN, .ERLEDIGT { color: var(--petrol); }

ul { margin: 0; padding: 0; }
li.posten {
  list-style: none; border-left: 4px solid var(--kante);
  border-radius: 10px; padding: 10px 13px; margin-bottom: 7px;
  background: var(--gruen-feld); overflow-wrap: anywhere;
}
li.ROT { border-left-color: var(--terrakotta); background: var(--rot-feld); }
li.GELB { border-left-color: var(--ocker); background: var(--gelb-feld); }
li.GRUEN, li.ERLEDIGT { border-left-color: var(--petrol); background: var(--gruen-feld); }

.titel { font-weight: 650; }
.mittel { font-size: .9rem; color: var(--leise); }
.frist { font-variant-numeric: tabular-nums; font-weight: 700; white-space: nowrap; }

/* Was man selten braucht, liegt zugeklappt da — sichtbar, aber nicht im Weg. */
details { border-top: 1px solid var(--kante); padding-top: 12px; margin-top: 16px; }
details[open] { padding-bottom: 4px; }
summary {
  cursor: pointer; font-size: .78rem; letter-spacing: .07em;
  text-transform: uppercase; color: var(--leise); font-weight: 650;
  min-height: 32px; display: flex; align-items: center; gap: 8px;
}
summary:focus-visible { outline: 3px solid var(--ocker); outline-offset: 3px; }
/* Ohne Zeichen liest sich ein zugeklappter Abschnitt wie eine tote
   Überschrift — und `display:flex` schluckt den eingebauten Pfeil.
   Also einer aus zwei Rändern, gedreht. */
summary::marker { content: ""; }
summary::-webkit-details-marker { display: none; }
summary::before {
  content: ""; flex: 0 0 auto; width: 6px; height: 6px;
  border-right: 2px solid currentColor; border-bottom: 2px solid currentColor;
  transform: rotate(-45deg); margin-inline-end: 3px;
}
details[open] > summary::before { transform: rotate(45deg); }
summary:hover { color: var(--text); }
/* Die Zahl steht in einem eigenen Knoten: der Übersetzungslauf schlägt
   ganze Textknoten nach, und „Befunde (8)“ steht in keinem Wörterbuch. */
.anzahl { font-variant-numeric: tabular-nums; opacity: .75; }
.anzahl:not(:empty)::before { content: "("; }
.anzahl:not(:empty)::after { content: ")"; }
details > :not(summary) { margin-top: 10px; }

/* --- Die Bereichsleiste (nur Handy und Tablett) ------------------- */
.leiste {
  position: fixed; inset-inline: 0; inset-block-end: 0; z-index: 20;
  /* Kräftiger als die Karten: was darunter durchscrollt, darf die
     Beschriftung nicht stören. */
  background: var(--glas-stark);
  display: grid; grid-template-columns: repeat(4, 1fr);
  border-radius: 0; border-block-start: 1px solid var(--kante);
  padding-block-end: env(safe-area-inset-bottom, 0);
}
.leiste button {
  background: none; border: 0; border-radius: 0; box-shadow: none;
  min-height: 58px; padding: 6px 2px 8px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 2px; font-size: .72rem; font-weight: 650; color: var(--leise);
  letter-spacing: .02em; position: relative;
}
.leiste button:hover { border-color: transparent; }
.leiste .leiste-zeichen { width: 21px; height: 21px; }
.leiste button[aria-current="true"] { color: var(--petrol); }
.leiste button[aria-current="true"]::before {
  content: ""; position: absolute; inset-block-start: 0; inset-inline: 22%;
  height: 3px; border-radius: 0 0 3px 3px; background: currentColor;
}
.marke {
  position: absolute; inset-block-start: 5px; inset-inline-start: 50%;
  margin-inline-start: 5px; min-width: 18px; padding: 0 5px;
  border-radius: 999px; background: var(--terrakotta); color: var(--grund);
  font-size: .68rem; line-height: 18px; font-variant-numeric: tabular-nums;
}
.marke:empty { display: none; }

@media (max-width: 61.99rem) {
  body.bereiche { padding-block-end: 72px; }
  /* Sichtbar ist genau ein Bereich — das ist der Unterschied zwischen
     einer App und einer langen Seite. */
  body.bereiche [data-bereich] { display: none; }
  body.bereiche[data-offen="heute"] [data-bereich="heute"],
  body.bereiche[data-offen="stand"] [data-bereich="stand"],
  body.bereiche[data-offen="eintragen"] [data-bereich="eintragen"],
  body.bereiche[data-offen="pruefen"] [data-bereich="pruefen"] { display: block; }
  body.bereiche[data-offen="stand"] [data-bereich="stand"] { display: grid; }
}
@media (min-width: 62rem) { #leiste { display: none; } #nichts { display: none; } }

.breit { overflow-x: auto; }
#anfang pre {
  margin: 8px 0 12px; padding: 12px 14px; border-radius: 10px;
  background: var(--gruen-feld); border: 1px solid var(--kante);
  font-size: .86rem; line-height: 1.5;
}
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--kante); }
td.zahl, th.zahl { text-align: right; white-space: nowrap; }

.befund {
  font-size: .9rem; border-left: 3px solid var(--ocker);
  padding-left: 11px; margin-bottom: 9px; color: var(--leise);
  overflow-wrap: anywhere;
}

.toast {
  position: fixed; inset-block-end: 16px; inset-inline: 16px;
  max-width: 34rem; margin-inline: auto; padding: 12px 16px;
  display: flex; gap: 12px; align-items: center; justify-content: space-between;
  flex-wrap: wrap;
}
.toast button { min-height: 38px; }

body[data-rolle="LESER"] button.tat:not(#laden):not(#rechnen) { display: none; }
body:not([data-rolle="LEITUNG"]) #vermerke button { display: none; }
/* Ein Programmwechsel verschiebt Impftermine — das ist keine Stallarbeit. */
body:not([data-rolle="LEITUNG"]) #programmwechsel { display: none; }

@media (prefers-reduced-motion: no-preference) {
  summary::before { transition: transform .15s ease; }
  .toast { animation: hoch .2s ease-out; }
  @keyframes hoch { from { transform: translateY(8px); opacity: 0; } }
}
"""

_KOPF = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="FAVICON_HIER">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="apple-touch-icon" href="/zeichen.svg">
<meta name="theme-color" content="#134e57">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="description" content="Impftermine, Futterwechsel und Mischaufträge je Herde.">
<title>Taktgeber</title>
<style>"""

_SEITE_MARKUP = """
</style>
</head>
<body>
<div class="huelle">

<p class="karte glas" id="offlineband" role="status" hidden
   style="border-color:var(--ocker);background:var(--gelb-feld);font-weight:650">
  <span id="offlinetext"></span>
  <button class="still" id="nachreichen" type="button"
          style="margin-left:10px;min-height:38px">Jetzt nachreichen</button>
</p>

<header class="karte glas">
  <div class="reihe">
    <div>
      <h1>Taktgeber</h1>
      <p class="leise" id="unterzeile" style="margin:0">Prophylaxe und Fütterung je Herde</p>
    </div>
    <details class="menue" id="menue">
      <summary aria-label="Menü"><span aria-hidden="true">⋯</span></summary>
      <div class="werkzeuge">
        <span class="leise" id="wer"></span>
        <label for="sprache" class="leise">Sprache</label>
        <select id="sprache">
          <option value="de">Deutsch</option>
          <option value="fr">Français</option>
        </select>
        <button class="still" id="thema" type="button">Ansicht wechseln</button>
        <button class="still" id="abmelden" type="button">Abmelden</button>
      </div>
    </details>
  </div>
  <div class="kopf" style="margin-top:14px">
    <div class="feld"><label for="herde">Herde</label><select id="herde"></select></div>
    <div class="feld"><label for="stichtag">Stichtag</label>
      <input id="stichtag" type="date"></div>
    <div class="feld schmal"><label for="vorrat">Futtervorrat (kg)</label>
      <input id="vorrat" type="number" min="0" step="10" placeholder="optional"></div>
    <button class="tat" id="laden" type="button">Anzeigen</button>
  </div>
</header>

<p id="zustand" class="karte glas" role="status">Lade …</p>

<!-- Der erste Bildschirm eines neuen Betriebs. Eine Zeile „keine Herde“
     sagt, dass nichts da ist — nicht, wie etwas hinkommt. -->
<section class="karte glas" id="anfang" hidden>
  <h2>Noch keine Herde</h2>
  <p>Der Taktgeber rechnet alles aus dem Einstalldatum: Impftermine,
     Futterwechsel, Verzehr und Mischauftrag. Ohne eine eingestallte Herde
     gibt es nichts zu takten.</p>
  <p class="leise">Auf dem Rechner, auf dem der Taktgeber läuft:</p>
  <pre class="breit"><code>elevage einstallen --herde H1 --name "Stall Nord" \
    --tierart LEGEHENNE --einstall 2026-03-02 --tiere 1200</code></pre>
  <p class="leise winzig">Danach diese Seite neu laden. Welches
     Prophylaxe-Blatt gilt, lässt sich jederzeit wechseln.</p>
</section>

<!-- Die eine Frage, die jemand im Stall hat: was ist jetzt zu tun?
     Sie wird hier beantwortet, statt aus drei Blöcken zusammengesucht. -->
<section class="karte glas jetzt" id="jetzt" hidden aria-live="polite">
  <p class="jetzt-satz" id="jetzt-satz"></p>
  <p class="jetzt-dazu leise" id="jetzt-dazu"></p>
</section>

<section class="karte glas stand" id="kopfzahlen" data-bereich="stand" hidden>
  <div>
    <h3>Stand</h3>
    <p style="margin:0" id="alter"></p>
    <p class="leise winzig" id="phase" style="margin:8px 0 0"></p>
  </div>

  <div class="block" id="futter" hidden>
    <h3>Futter</h3>
    <p id="futtertext" style="margin:0"></p>
    <p class="leise winzig" id="futterherkunft" style="margin:4px 0 0"></p>
  </div>

  <div class="block" id="sperre" hidden>
    <h3>Wartezeit</h3>
    <p id="sperrtext" style="margin:0;font-weight:650"></p>
    <ul id="sperrliste" style="margin-top:8px"></ul>
  </div>

  <div class="block" id="block-programm">
    <h3>Programm</h3>
    <p id="programmtext" style="margin:0;font-weight:650"></p>
    <p class="leise winzig" id="programmherausgeber" style="margin:4px 0 0"></p>
    <details id="merksaetze" hidden>
      <summary>Merksätze des Blattes</summary>
      <ul id="merkliste"></ul>
    </details>
  </div>

  <div class="block" id="block-ruhe" hidden>
    <h3>Ruhe</h3>
    <p id="ruhetext" style="margin:0"></p>
  </div>

  <div class="block" id="block-tierarzt" hidden>
    <h3>Tierarzt</h3>
    <p id="tierarzttext" style="margin:0"></p>
  </div>
</section>

<div class="raster">

<section class="karte glas" id="karte-aufgaben" data-bereich="heute" data-sammel hidden>
  <h2>Was zu tun ist</h2>
  <div class="block" id="block-ueberfaellig" hidden><h3>Überfällig</h3><ul></ul></div>
  <div class="block" id="block-heute" hidden><h3>Jetzt dran</h3><ul></ul></div>
  <div class="block" id="block-bestellen" hidden>
    <h3>Jetzt besorgen</h3>
    <p class="leise winzig" style="margin:-4px 0 9px">Vorlauf läuft — muss da sein,
       bevor der Tag kommt.</p>
    <ul></ul>
  </div>
  <details class="block" id="block-demnaechst" hidden>
    <summary><span>Demnächst</span><span class="anzahl"></span></summary>
    <ul></ul>
  </details>
  <details class="block" id="block-erledigt" hidden>
    <summary><span>Zuletzt erledigt</span><span class="anzahl"></span></summary>
    <ul></ul>
  </details>
</section>

<div class="spalte">

<section class="karte glas" data-bereich="eintragen">
  <h2>Eintragen</h2>
  <div class="block">
    <h3>Mischauftrag</h3>
    <div class="kopf">
      <div class="feld schmal"><label for="menge">Menge (kg)</label>
        <input id="menge" type="number" min="1" step="50" value="500"></div>
      <div class="feld"><label for="art">Bei Überhang</label>
        <select id="art">
          <option value="AUSGLEICH">ausgleichen</option>
          <option value="VERBATIM">wie im Blatt</option>
          <option value="ANTEILIG">anteilig skalieren</option>
        </select></div>
      <button class="tat" id="rechnen" type="button">Rechnen</button>
      <button class="still" id="buchen" type="button" hidden>Als gemischt buchen</button>
    </div>
    <div id="mischung" class="breit" style="margin-top:12px"></div>
  </div>

  <details>
    <summary>Abgang buchen</summary>
    <div class="kopf">
      <div class="feld schmal"><label for="abgangtiere">Tiere</label>
        <input id="abgangtiere" type="number" min="1" step="1"></div>
      <div class="feld"><label for="abgangGrund">Grund</label>
        <select id="abgangGrund">
          <option value="VERENDET">verendet</option>
          <option value="GEKEULT">gekeult</option>
          <option value="VERKAUFT">verkauft</option>
          <option value="SONSTIGES">sonstiges</option>
        </select></div>
      <div class="feld"><label for="abgangTag">Am</label><input id="abgangTag" type="date"></div>
      <button class="tat" id="buchen-abgang" type="button">Buchen</button>
    </div>
    <p class="leise winzig" style="margin-bottom:0">Verkauft ist kein Verlust — der Grund
       entscheidet, ob es in die Verlustquote zählt.</p>
  </details>

  <details id="programmwechsel">
    <summary>Programm wechseln</summary>
    <div class="kopf">
      <div class="feld"><label for="programmwahl">Programm</label>
        <select id="programmwahl"></select></div>
      <button class="tat" id="programmsetzen" type="button">Übernehmen</button>
    </div>
    <p class="leise winzig" style="margin-bottom:0">Abgehakte Schritte bleiben
       abgehakt. Welches Blatt gilt, entscheidet der Betrieb.</p>
  </details>

  <details id="programmvergleich">
    <summary>Blätter vergleichen</summary>
    <div class="kopf">
      <div class="feld"><label for="vergleichlinks">Links</label>
        <select id="vergleichlinks"></select></div>
      <div class="feld"><label for="vergleichrechts">Rechts</label>
        <select id="vergleichrechts"></select></div>
      <button class="tat" id="vergleichen" type="button">Gegenüberstellen</button>
    </div>
    <div id="vergleichtafel" class="breit" style="margin-top:12px"></div>
  </details>

  <details>
    <summary>Vorfall melden</summary>
    <div class="kopf">
      <div class="feld schmal"><label for="vorfallart">Art</label>
        <select id="vorfallart"><option value="GUMBORO">Gumboro</option></select></div>
      <div class="feld"><label for="vorfalltag">Festgestellt am</label>
        <input id="vorfalltag" type="date"></div>
      <div class="feld"><label for="vorfalltext">Beobachtung</label>
        <input id="vorfalltext" placeholder="optional"></div>
      <button class="tat" id="melden" type="button">Melden</button>
    </div>
    <p class="leise winzig" style="margin-bottom:0">Das Schema startet am gemeldeten Tag.</p>
  </details>
</section>

<section class="karte glas" id="karte-pruefen" data-bereich="pruefen" data-sammel hidden>
  <h2>Zu prüfen</h2>
  <div class="block" id="block-vermerke" hidden>
    <h3>Offene Ausgleiche</h3>
    <p class="leise winzig" style="margin:-4px 0 9px">Bleibt liegen, bis jemand am
       Original nachsieht.</p>
    <ul id="vermerke"></ul>
  </div>
  <details class="block" id="block-befunde" hidden>
    <summary><span>Befunde</span><span class="anzahl"></span></summary>
    <div id="befunde"></div>
  </details>
</section>

</div>
</div>

<p class="karte glas leise" id="nichts" hidden>Hier ist gerade nichts.</p>

<footer class="leise" style="text-align:center;padding:4px 0 24px">
  <span id="stempel"></span>
</footer>

</div>

<!-- Auf dem Handy eine App statt einer Rolle: vier Bereiche, einer sichtbar.
     Ab 62 rem verschwindet die Leiste und alles steht wieder nebeneinander. -->
<nav class="leiste glas" id="leiste" aria-label="Bereiche" hidden>
  <button type="button" data-ziel="heute" aria-current="true">
    <svg class="leiste-zeichen" viewBox="0 0 24 24" aria-hidden="true"
         fill="none" stroke="currentColor" stroke-width="2"
         stroke-linecap="round" stroke-linejoin="round"><path d='M4 12l5 5L20 6'/></svg>
    <span>Heute</span><span class="marke" data-marke="heute"></span>
  </button>
  <button type="button" data-ziel="stand">
    <svg class="leiste-zeichen" viewBox="0 0 24 24" aria-hidden="true"
         fill="none" stroke="currentColor" stroke-width="2"
         stroke-linecap="round" stroke-linejoin="round"><path d='M4 6h16M4 12h16M4 18h16'/></svg>
    <span>Stand</span>
  </button>
  <button type="button" data-ziel="eintragen">
    <svg class="leiste-zeichen" viewBox="0 0 24 24" aria-hidden="true"
         fill="none" stroke="currentColor" stroke-width="2"
         stroke-linecap="round" stroke-linejoin="round"><path d='M4 20h4L20 8l-4-4L4 16v4z'/></svg>
    <span>Eintragen</span>
  </button>
  <button type="button" data-ziel="pruefen">
    <svg class="leiste-zeichen" viewBox="0 0 24 24" aria-hidden="true"
         fill="none" stroke="currentColor" stroke-width="2"
         stroke-linecap="round" stroke-linejoin="round"><circle cx='11' cy='11' r='6'/>
         <path d='M15.5 15.5L21 21'/></svg>
    <span>Prüfen</span><span class="marke" data-marke="pruefen"></span>
  </button>
</nav>

<div class="toast glas" id="toast" hidden>
  <span id="toasttext"></span>
  <button type="button" id="undo">Rückgängig</button>
</div>

<script>
const $ = (id) => document.getElementById(id);
"""

_SEITE_SKRIPT = """
const heute = () => new Date().toISOString().slice(0, 10);
let bild = null;
let letzteQuittung = null;
let programme = [];

function zeichen(ampel) {
  return { ROT: "!", GELB: "\\u203a", GRUEN: "\\u00b7", ERLEDIGT: "\\u2713" }[ampel] || "";
}
function wort(ampel) {
  return txt({ ROT: "überfällig", GELB: "jetzt dran",
               GRUEN: "geplant", ERLEDIGT: "erledigt" }[ampel]);
}
function fenster(t) {
  const kurz = (s) => s.slice(8, 10) + "." + s.slice(5, 7) + ".";
  return t.faelligVon === t.faelligBis ? kurz(t.faelligVon)
       : kurz(t.faelligVon) + "\\u2013" + kurz(t.faelligBis);
}

const SCHLANGE_SCHLUESSEL = "taktgeber-warteschlange";

// Nur Schreibpfade, deren Nummer aus dem Inhalt entsteht — sie dürfen
// beliebig oft nachgereicht werden, ohne doppelt zu wirken.
const NACHREICHBAR = [
  "/api/quittung", "/api/quittung/widerrufen", "/api/vorfall",
  "/api/abgang", "/api/vermerk/abhaken",
];

function schlange() {
  try { return JSON.parse(localStorage.getItem(SCHLANGE_SCHLUESSEL) || "[]"); }
  catch (fehler) { return []; }
}

function setzeSchlange(eintraege) {
  try { localStorage.setItem(SCHLANGE_SCHLUESSEL, JSON.stringify(eintraege)); }
  catch (fehler) { /* privates Fenster: dann eben nur diese Sitzung */ }
  zeigeBand();
}

function zeigeBand() {
  const offen = schlange();
  const band = $("offlineband");
  if (!offen.length && navigator.onLine) { band.hidden = true; return; }
  $("offlinetext").textContent = !navigator.onLine
    ? (offen.length
        ? txt("Kein Netz") + " \\u00b7 " + offen.length + " " + txt("Eingaben warten")
        : txt("Kein Netz — die Seite arbeitet aus dem Zwischenspeicher."))
    : offen.length + " " + txt("Eingaben noch nicht beim Server");
  $("nachreichen").hidden = !offen.length || !navigator.onLine;
  band.hidden = false;
}

async function nachreichen() {
  let offen = schlange();
  while (offen.length) {
    const eintrag = offen[0];
    try {
      const antwort = await fetch(eintrag.pfad, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify(eintrag.koerper),
      });
      if (!antwort.ok && antwort.status >= 500) break;  // Server schwächelt: später
    } catch (fehler) { break; }                          // immer noch kein Netz
    offen = offen.slice(1);
    setzeSchlange(offen);
  }
  if (!schlange().length) await lade();
}

async function sendeOderMerken(pfad, koerper) {
  // Geht der Versand nicht durch, wandert die Eingabe in die Warteschlange
  // statt verloren zu gehen. Möglich ist das nur, weil die Nummern
  // serverseitig aus dem Inhalt entstehen: zweimal geschickt wirkt einmal.
  try {
    return await hole(pfad, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify(koerper),
    });
  } catch (fehler) {
    if (!NACHREICHBAR.includes(pfad) || fehler.message === "abgemeldet") throw fehler;
    setzeSchlange(schlange().concat([{ pfad: pfad, koerper: koerper }]));
    return { gemerkt: true };
  }
}

async function hole(pfad, optionen) {
  const antwort = await fetch(pfad, optionen);
  if (antwort.status === 401) {
    window.location.href = "/anmelden";
    throw new Error("abgemeldet");
  }
  const inhalt = await antwort.json();
  if (!antwort.ok) throw new Error(inhalt.fehler || txt("Unbekannter Fehler"));
  return inhalt;
}

function melde(text, rueckgaengig) {
  $("toasttext").textContent = text;
  $("undo").hidden = !rueckgaengig;
  $("toast").hidden = false;
  clearTimeout(melde.uhr);
  melde.uhr = setTimeout(() => { $("toast").hidden = true; }, 9000);
}

// Die Blätter SIND französisch. In der französischen Ansicht steht
// deshalb ihr eigener Wortlaut, nicht der deutsche Titel durch ein
// Wörterbuch gedreht. Fehlt er, gilt dieselbe Regel wie im Wörterbuch:
// lieber Deutsch als ein leeres Feld.
function wortlaut(objekt, feld) {
  const fr = objekt[feld + "Fr"];
  return SPRACHE === "fr" && fr ? fr : objekt[feld];
}

function postenZeile(t, mitKnopf) {
  const li = document.createElement("li");
  li.className = "posten " + t.ampel;
  const kopf = document.createElement("div");
  kopf.className = "reihe";
  const links = document.createElement("div");
  const titel = document.createElement("div");
  titel.className = "titel";
  titel.textContent = zeichen(t.ampel) + " " + wortlaut(t, "titel");
  links.appendChild(titel);
  if (t.praeparate && t.praeparate.length) {
    const m = document.createElement("div");
    m.className = "mittel";
    m.textContent = t.praeparate.join(" / ");
    links.appendChild(m);
  }
  if (t.hinweis) {
    const h = document.createElement("div");
    h.className = "mittel";
    h.textContent = wortlaut(t, "hinweis");
    links.appendChild(h);
  }
  if (t.dosisJeLiter) {
    const d = document.createElement("div");
    d.className = "mittel";
    d.textContent = txt("Dosis") + ": " + t.dosisJeLiter;
    links.appendChild(d);
  }
  if (t.erledigtAm) {
    const e = document.createElement("div");
    e.className = "mittel";
    e.textContent = txt("erledigt am") + " " + t.erledigtAm
      + (t.lot ? " \\u00b7 " + txt("Charge") + " " + t.lot : "");
    links.appendChild(e);
  }
  kopf.appendChild(links);
  const rechts = document.createElement("div");
  const frist = document.createElement("div");
  frist.className = "frist " + t.ampel;
  frist.textContent = fenster(t) + " \\u00b7 " + wort(t.ampel);
  rechts.appendChild(frist);
  if (mitKnopf) {
    const knopf = document.createElement("button");
    knopf.className = "tat";
    knopf.type = "button";
    knopf.textContent = txt("Erledigt");
    knopf.style.marginTop = "6px";
    knopf.onclick = () => (t.praeparate && t.praeparate.length > 1)
      ? frageMittel(li, t) : quittiere(t, null);
    rechts.appendChild(knopf);
  }
  kopf.appendChild(rechts);
  li.appendChild(kopf);
  return li;
}

// Eine Sammelkarte lebt von ihren Blöcken: sind alle leer, verschwindet
// auch die Überschrift. Sonst stünde \u201eZu pr\u00fcfen\u201c \u00fcber dem Nichts.
function karten() {
  document.querySelectorAll("[data-sammel]").forEach((karte) => {
    const bloecke = Array.from(karte.querySelectorAll(".block"));
    karte.hidden = bloecke.every((block) => block.hidden);
  });
}

function zaehle(block, anzahl) {
  // Zugeklappt muss man sehen, wie viel drunter liegt — sonst klappt es
  // niemand auf, und ein Befund, den niemand liest, ist keiner.
  const marke = block.querySelector(".anzahl");
  if (marke) marke.textContent = String(anzahl);
}

function fuelle(id, liste, mitKnopf) {
  const block = $(id);
  const ul = block.querySelector("ul");
  ul.replaceChildren();
  liste.forEach((t) => ul.appendChild(postenZeile(t, mitKnopf)));
  block.hidden = liste.length === 0;
  zaehle(block, liste.length);
}

async function ladeHerden() {
  const daten = await hole("/api/herden");
  const wahl = $("herde");
  const vorher = wahl.value;
  wahl.replaceChildren();
  daten.herden.forEach((h) => {
    const o = document.createElement("option");
    o.value = h.herdeId;
    o.textContent = h.name + " (" + h.herdeId + ")";
    wahl.appendChild(o);
  });
  if (vorher) wahl.value = vorher;
  return daten.herden.length;
}

async function lade() {
  $("zustand").hidden = false;
  $("zustand").textContent = txt("Lade …");
  try {
    const ich = await hole("/api/ich");
    $("wer").textContent = ich.name + " \\u00b7 " + ich.tenantId + " \\u00b7 " + ich.rolle;
    document.body.dataset.rolle = ich.rolle;
    const anzahl = await ladeHerden();
    if (!anzahl) {
      $("zustand").hidden = true;
      $("anfang").hidden = false;
      ["jetzt", "kopfzahlen", "sperre", "futter", "block-ueberfaellig", "block-heute",
       "block-bestellen", "block-demnaechst", "block-erledigt", "block-vermerke",
       "block-befunde"].forEach((i) => $(i).hidden = true);
      karten();
      return;
    }
    const p = new URLSearchParams({
      herde: $("herde").value, stichtag: $("stichtag").value,
    });
    if ($("vorrat").value) p.set("vorrat", $("vorrat").value);
    await ladeProgramme();
    $("anfang").hidden = true;
    bild = await hole("/api/tagesbild?" + p);
    zeige();
    fuelleProgrammwahl();
    $("zustand").hidden = true;
  } catch (fehler) {
    $("zustand").hidden = false;
    $("zustand").textContent = txt("Das hat nicht geklappt:") + " " + fehler.message;
  }
}

function jetztSatz() {
  // Eine Rangfolge, kein Urteil: überfällig schlägt fällig schlägt Ruhe.
  // Die Zahlen stehen im Tagesbild, hier wird nur ausgewählt, was zählt.
  const rot = bild.ueberfaellig.length;
  const gelb = bild.heute.length;
  if (rot) {
    return {
      ampel: "ROT",
      satz: rot === 1 ? txt("1 Aufgabe ist überfällig")
                      : rot + " " + txt("Aufgaben sind überfällig"),
      dazu: wortlaut(bild.ueberfaellig[0], "titel"),
    };
  }
  if (gelb) {
    return {
      ampel: "GELB",
      satz: gelb === 1 ? txt("1 Aufgabe steht heute an")
                       : gelb + " " + txt("Aufgaben stehen heute an"),
      dazu: wortlaut(bild.heute[0], "titel"),
    };
  }
  const naechste = bild.demnaechst[0] || bild.bestellen[0];
  return {
    ampel: "GRUEN",
    satz: txt("Heute ist nichts fällig."),
    dazu: naechste
      ? txt("Als Nächstes") + ": " + wortlaut(naechste, "titel") + " \u00b7 " + fenster(naechste)
      : txt("In den nächsten sieben Tagen steht nichts an."),
  };
}

function zeige() {
  const jetzt = jetztSatz();
  $("jetzt").className = "karte glas jetzt " + jetzt.ampel;
  $("jetzt-satz").textContent = zeichen(jetzt.ampel) + " " + jetzt.satz;
  $("jetzt-dazu").textContent = jetzt.dazu;
  $("jetzt").hidden = false;

  const stand = bild.bestand;
  const imStall = stand ? stand.tierzahl : bild.herde.tierzahl;
  const verlust = stand && stand.abgangGesamt
    ? " (" + txt("von") + " " + stand.eingestallt + ", \\u2212"
      + stand.verlusteProzent + " %)"
    : "";
  $("alter").textContent =
    txt("Tag") + " " + bild.alterTage + " \\u00b7 " + txt("Woche") + " "
    + bild.alterWochen + " \\u00b7 " + imStall + " " + txt("Tiere") + verlust;
  $("phase").textContent = bild.phase
    ? txt("Futterphase") + ": " + wortlaut(bild.phase, "name")
    : txt("Für diese Linie liegt kein Futterblatt vor.");
  $("kopfzahlen").hidden = false;

  const laufend = (bild.sperren || []).filter((s) => s.laeuftNoch);
  const sperrliste = $("sperrliste");
  sperrliste.replaceChildren();
  if (laufend.length) {
    const spaeteste = laufend.map((s) => s.freigabeAb).sort().pop();
    const was = laufend[0].erzeugnis === "EIER" ? "Eier" : "Fleisch";
    $("sperrtext").textContent = txt(was) + " " + txt("gesperrt bis") + " " + spaeteste;
    laufend.forEach((s) => {
      const li = document.createElement("li");
      li.className = "posten ROT";
      li.textContent = s.praeparat + " \\u00b7 " + txt("letzte Gabe") + " " + s.letzteGabe
        + " \\u00b7 " + s.wartezeitTage + " " + txt("Tage") + " \\u00b7 "
        + txt("frei ab") + " " + s.freigabeAb;
      sperrliste.appendChild(li);
    });
  }
  $("sperre").hidden = laufend.length === 0;

  const f = bild.futter;
  if (f && f.bedarfJeTagKg !== null) {
    let text = f.grammJeTierTag + " " + txt("g/Tier/Tag") + " \\u00b7 "
             + f.bedarfJeTagKg + " " + txt("kg am Tag") + " \\u00b7 "
             + f.bedarfBisHorizontKg + " " + txt("kg für") + " "
             + f.horizontTage + " " + txt("Tage");
    if (f.reichtBis) text += " \\u00b7 " + txt("Vorrat reicht bis") + " " + f.reichtBis
                           + ", " + txt("bestellen ab") + " " + f.bestellenAb;
    $("futtertext").textContent = text;
    $("futterherkunft").textContent = txt(
      f.quelle === "GEMESSEN" ? "Aus dem eigenen Mischprotokoll gerechnet."
                              : "Richtwert — keine Zahl dieses Betriebs.");
    $("futter").hidden = false;
  } else { $("futter").hidden = true; }

  $("programmtext").textContent =
    SPRACHE === "fr" && bild.programmTitelFr ? bild.programmTitelFr : bild.programmTitel;
  const blatt = (programme || []).find((x) => x.programmId === bild.programmId);
  $("programmherausgeber").textContent = blatt ? blatt.herausgeber : "";

  // Die Merksätze stehen im Blatt und nicht im Kalender: Biosicherheit,
  // Lüftung, „nur gesunde Tiere impfen". Sie taugen zu keinem Termin.
  const merk = $("merkliste");
  merk.replaceChildren();
  ((blatt && blatt.hinweise) || []).forEach((h) => {
    const li = document.createElement("li");
    li.className = "befund";
    li.style.listStyle = "none";
    li.textContent = wortlaut(h, "text");
    merk.appendChild(li);
  });
  $("merksaetze").hidden = !(blatt && blatt.hinweise && blatt.hinweise.length);

  // Eine Pause ist eine Anweisung, keine Aufgabe — sie steht hier und
  // nicht in der Liste, weil sie nichts zum Abhaken ist.
  const ruhe = bild.ruhe || [];
  $("ruhetext").textContent = ruhe
    .map((r) => wortlaut(r, "titel") + " (" + txt("bis") + " "
                + fenster(r).split("\u2013").pop() + ")")
    .join(" \u00b7 ");
  $("block-ruhe").hidden = ruhe.length === 0;

  const arzt = bild.tierarzt;
  $("tierarzttext").textContent = arzt
    ? [arzt.name, arzt.praxis, arzt.telefon, arzt.email].filter((x) => x).join(" \u00b7 ")
    : "";
  $("block-tierarzt").hidden = !arzt;

  fuelle("block-ueberfaellig", bild.ueberfaellig, true);
  fuelle("block-heute", bild.heute, true);
  fuelle("block-bestellen", bild.bestellen, false);
  const schonGenannt = new Set(bild.bestellen.map((t) => t.schrittKey));
  fuelle("block-demnaechst",
         bild.demnaechst.filter((t) => !schonGenannt.has(t.schrittKey)), false);
  fuelle("block-erledigt", bild.erledigt.slice(-5), false);

  const liste = $("vermerke");
  liste.replaceChildren();
  (bild.vermerke || []).forEach((v) => {
    const li = document.createElement("li");
    li.className = "posten GELB";
    const reihe = document.createElement("div");
    reihe.className = "reihe";
    const links = document.createElement("div");
    const kopf = document.createElement("div");
    kopf.className = "titel";
    kopf.textContent = "\\u203a " + v.betrifft;
    const text = document.createElement("div");
    text.className = "mittel";
    text.textContent = wortlaut(v, "text");
    links.append(kopf, text);
    const knopf = document.createElement("button");
    knopf.className = "tat";
    knopf.type = "button";
    knopf.textContent = txt("Geprüft");
    knopf.onclick = () => hakeAb(v);
    reihe.append(links, knopf);
    li.appendChild(reihe);
    liste.appendChild(li);
  });
  $("block-vermerke").hidden = (bild.vermerke || []).length === 0;

  const kasten = $("befunde");
  kasten.replaceChildren();
  bild.issues.forEach((i) => {
    const p = document.createElement("p");
    p.className = "befund";
    p.textContent = wortlaut(i, "text");
    kasten.appendChild(p);
  });
  $("block-befunde").hidden = bild.issues.length === 0;
  zaehle($("block-befunde"), bild.issues.length);
  karten();
  marken();
  zeigeLeere();
  uebersetzeSeite();
}

function frageMittel(li, t) {
  // Das Programm nennt Alternativen; welche gegeben wurde, weiß nur der
  // Mensch. Ohne diese Angabe lässt sich keine Wartezeit rechnen.
  if (li.querySelector(".mittelwahl")) return;
  const kasten = document.createElement("div");
  kasten.className = "mittelwahl kopf";
  kasten.style.marginTop = "10px";
  const feld = document.createElement("div");
  feld.className = "feld";
  const beschriftung = document.createElement("label");
  const kennung = "mittel-" + t.schrittKey;
  beschriftung.setAttribute("for", kennung);
  beschriftung.textContent = txt("Welches Mittel wurde gegeben?");
  const wahl = document.createElement("select");
  wahl.id = kennung;
  t.praeparate.forEach((name) => {
    const o = document.createElement("option");
    o.value = name;
    o.textContent = name;
    wahl.appendChild(o);
  });
  feld.append(beschriftung, wahl);
  const ja = document.createElement("button");
  ja.className = "tat";
  ja.type = "button";
  ja.textContent = txt("Abhaken");
  ja.onclick = () => quittiere(t, wahl.value);
  const nein = document.createElement("button");
  nein.className = "still";
  nein.type = "button";
  nein.textContent = txt("Abbrechen");
  nein.onclick = () => kasten.remove();
  kasten.append(feld, ja, nein);
  li.appendChild(kasten);
  wahl.focus();
}

async function quittiere(t, mittel) {
  try {
    const antwort = await sendeOderMerken("/api/quittung", {
      herde: $("herde").value, schritt: t.schrittKey,
      am: $("stichtag").value, praeparat: mittel,
    });
    if (antwort.gemerkt) {
      melde("\\u201e" + t.titel + "\\u201c " + txt("abgehakt — wird nachgereicht."), false);
      return;
    }
    letzteQuittung = antwort.quittungId;
    melde("\\u201e" + t.titel + "\\u201c " + txt("abgehakt."), true);
    await lade();
  } catch (fehler) {
    melde(txt("Nicht abgehakt:") + " " + fehler.message, false);
  }
}

async function hakeAb(v) {
  try {
    await sendeOderMerken("/api/vermerk/abhaken", {
      vermerkId: v.vermerkId, am: $("stichtag").value,
    });
    melde(txt("Als geprüft abgehakt."), false);
    await lade();
  } catch (fehler) {
    melde(txt("Nicht abgehakt:") + " " + fehler.message, false);
  }
}

$("undo").onclick = async () => {
  if (!letzteQuittung) return;
  await sendeOderMerken("/api/quittung/widerrufen", { quittungId: letzteQuittung });
  letzteQuittung = null;
  $("toast").hidden = true;
  await lade();
};

async function rechne(buchen) {
  const koerper = {
    herde: $("herde").value, kg: Number($("menge").value),
    am: $("stichtag").value, art: $("art").value, buchen: !!buchen,
  };
  const ziel = $("mischung");
  try {
    const a = await hole("/api/mischung", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify(koerper),
    });
    ziel.replaceChildren();
    if (!a.auftrag) { ziel.textContent = txt("Kein Rezept für diese Linie."); return; }
    const tabelle = document.createElement("table");
    const kopf = tabelle.createTHead().insertRow();
    [txt("Rohstoff"), "kg"].forEach((x, i) => {
      const th = document.createElement("th");
      th.textContent = x; if (i) th.className = "zahl"; kopf.appendChild(th);
    });
    const rumpf = tabelle.createTBody();
    a.auftrag.zeilen.forEach((z) => {
      const r = rumpf.insertRow();
      r.insertCell().textContent = z.name;
      const c = r.insertCell(); c.textContent = z.kg.toFixed(2); c.className = "zahl";
    });
    const summe = rumpf.insertRow();
    summe.insertCell().textContent = txt("Ist-Einwaage");
    const sc = summe.insertCell();
    sc.textContent = a.auftrag.istEinwaageKg.toFixed(2); sc.className = "zahl";
    summe.style.fontWeight = "700";
    ziel.appendChild(tabelle);
    a.auftrag.issues.forEach((i) => {
      const p = document.createElement("p");
      p.className = "befund";
      p.textContent = wortlaut(i, "text");
      ziel.appendChild(p);
    });
    $("buchen").hidden = !a.auftrag.freigegeben || a.auftrag.ausgleich === "VERBATIM";
    if (buchen) melde(txt(a.gebucht ? "Mischung protokolliert." : "Nicht gebucht."), false);
  } catch (fehler) {
    ziel.textContent = txt("Das hat nicht geklappt:") + " " + fehler.message;
  }
}

async function ladeProgramme() {
  // Die Blätter kommen einmal und ändern sich nicht — ein Neuladen je
  // Tagesbild wäre ein Anruf ohne neue Antwort.
  if (programme.length) return programme;
  const daten = await hole("/api/programme");
  programme = daten.programme;
  return programme;
}

function fuelleProgrammwahl() {
  // Nur die Blätter der Tierart dieser Herde — ein Legehennenplan für
  // Masthühner wäre eine Wahl, die der Server ohnehin ablehnt.
  if (!bild) return;
  const passend = programme.filter((x) => x.tierart === bild.herde.tierart);
  // Vorbelegt wird das geltende Blatt gegen das nächste andere — ein Blatt
  // mit sich selbst zu vergleichen ergibt eine Tabelle ohne Unterschied.
  const anderes = passend.find((x) => x.programmId !== bild.programmId);
  const vorwahl = {
    programmwahl: bild.programmId,
    vergleichlinks: bild.programmId,
    vergleichrechts: anderes && anderes.programmId,
  };
  Object.keys(vorwahl).forEach((id) => {
    const wahl = $(id);
    const vorher = wahl.value;
    wahl.replaceChildren();
    passend.forEach((x) => {
      const opt = document.createElement("option");
      opt.value = x.programmId;
      opt.textContent = x.titel;
      wahl.appendChild(opt);
    });
    wahl.value = vorher || vorwahl[id] || "";
  });
  // Ein einziges Blatt lässt sich mit nichts vergleichen.
  $("programmvergleich").hidden = passend.length < 2;
  $("programmwechsel").hidden = passend.length < 2;
}

$("programmsetzen").onclick = async () => {
  try {
    await hole("/api/programm", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ herde: $("herde").value, programm: $("programmwahl").value }),
    });
    melde(txt("Das Programm dieser Herde wurde gewechselt."), false);
    await lade();
  } catch (fehler) { melde(txt("Das hat nicht geklappt:") + " " + fehler.message, false); }
};

function zeigeVergleich(v) {
  const ziel = $("vergleichtafel");
  ziel.replaceChildren();
  const tabelle = document.createElement("table");
  const kopf = document.createElement("tr");
  [txt("Thema"), v.linksTitel, v.rechtsTitel].forEach((text) => {
    const th = document.createElement("th");
    th.textContent = text;
    kopf.appendChild(th);
  });
  tabelle.appendChild(kopf);
  v.zeilen.filter((z) => !z.gleich).forEach((z) => {
    const tr = document.createElement("tr");
    [z.thema, z.links || "\u2014", z.rechts || "\u2014"].forEach((text) => {
      const td = document.createElement("td");
      td.textContent = text;
      tr.appendChild(td);
    });
    tabelle.appendChild(tr);
  });
  ziel.appendChild(tabelle);
  const gleich = v.zeilen.filter((z) => z.gleich).map((z) => z.thema);
  if (gleich.length) {
    const p = document.createElement("p");
    p.className = "leise winzig";
    p.textContent = txt("Gleich in beiden") + ": " + gleich.join(", ");
    ziel.appendChild(p);
  }
  (v.issues || []).forEach((i) => {
    const p = document.createElement("p");
    p.className = "befund";
    p.textContent = wortlaut(i, "text");
    ziel.appendChild(p);
  });
  const schluss = document.createElement("p");
  schluss.className = "leise winzig";
  schluss.textContent = txt("Welches Blatt gilt, entscheidet der Betrieb.");
  ziel.appendChild(schluss);
}

$("vergleichen").onclick = async () => {
  const p = new URLSearchParams({
    links: $("vergleichlinks").value, rechts: $("vergleichrechts").value,
  });
  try {
    zeigeVergleich(await hole("/api/vergleich?" + p));
    uebersetzeSeite();
  } catch (fehler) { melde(txt("Das hat nicht geklappt:") + " " + fehler.message, false); }
};

$("rechnen").onclick = () => rechne(false);
$("buchen").onclick = () => rechne(true).then(lade);

$("buchen-abgang").onclick = async () => {
  const tiere = Number($("abgangtiere").value);
  if (!tiere) { melde(txt("Wie viele Tiere?"), false); return; }
  try {
    await sendeOderMerken("/api/abgang", {
      herde: $("herde").value, tiere: tiere,
      grund: $("abgangGrund").value, am: $("abgangTag").value,
    });
    $("abgangtiere").value = "";
    melde(txt("Gebucht — der Futterbedarf rechnet ab jetzt damit."), false);
    await lade();
  } catch (fehler) {
    melde(txt("Nicht gebucht:") + " " + fehler.message, false);
  }
};

$("melden").onclick = async () => {
  try {
    await sendeOderMerken("/api/vorfall", {
      herde: $("herde").value, art: $("vorfallart").value,
      am: $("vorfalltag").value, bemerkung: $("vorfalltext").value || null,
    });
    melde(txt("Vorfall aufgenommen — das Schema steht im Plan."), false);
    $("vorfalltext").value = "";
    await lade();
  } catch (fehler) {
    melde(txt("Nicht aufgenommen:") + " " + fehler.message, false);
  }
};

$("thema").onclick = () => {
  const jetzt = document.documentElement.dataset.thema;
  document.documentElement.dataset.thema = jetzt === "dunkel" ? "hell" : "dunkel";
};

$("abmelden").onclick = async () => {
  await fetch("/api/abmelden", { method: "POST" });
  window.location.href = "/anmelden";
};

// --- Bereiche: auf dem Handy eine App, auf dem Schirm eine Seite -------
const BEREICH_SCHLUESSEL = "taktgeber-bereich";
const BEREICHE = ["heute", "stand", "eintragen", "pruefen"];

function bereichWaehlen(ziel) {
  if (!BEREICHE.includes(ziel)) ziel = "heute";
  document.body.dataset.offen = ziel;
  document.querySelectorAll("#leiste button").forEach((k) => {
    k.setAttribute("aria-current", k.dataset.ziel === ziel ? "true" : "false");
  });
  try { localStorage.setItem(BEREICH_SCHLUESSEL, ziel); } catch (f) {}
  zeigeLeere();
  window.scrollTo(0, 0);   // Ein Bereichswechsel ist ein Seitenwechsel.
}

function zeigeLeere() {
  // Der Hinweis steht nur da, wenn der offene Bereich wirklich leer ist —
  // neben einer vollen Karte waere er Laerm.
  const offen = document.body.dataset.offen;
  const karten = document.querySelectorAll('[data-bereich="' + offen + '"]');
  const voll = Array.from(karten).some((e) => !e.hidden);
  $("nichts").hidden = voll || !document.body.classList.contains("bereiche");
}

function marken() {
  // Die Zahl am Knopf ist der halbe Grund fuer die Leiste: man sieht, wo
  // etwas liegt, ohne hinzugehen.
  const zahl = (n) => (n ? String(n) : "");
  document.querySelector('[data-marke="heute"]').textContent =
    zahl(bild ? bild.ueberfaellig.length + bild.heute.length : 0);
  document.querySelector('[data-marke="pruefen"]').textContent =
    zahl(bild ? (bild.vermerke || []).length + bild.issues.length : 0);
}

function leisteAufbauen() {
  // Die Leiste gehoert zur schmalen Ansicht. Wer am Schirm sitzt, sieht
  // alles nebeneinander und braucht keine Bereiche.
  const schmal = window.matchMedia("(max-width: 61.99rem)").matches;
  document.body.classList.toggle("bereiche", schmal);
  $("leiste").hidden = !schmal;
  if (schmal && !document.body.dataset.offen) {
    let gemerkt = "heute";
    try { gemerkt = localStorage.getItem(BEREICH_SCHLUESSEL) || "heute"; } catch (f) {}
    bereichWaehlen(gemerkt);
  }
  zeigeLeere();
}

document.querySelectorAll("#leiste button").forEach((k) => {
  k.onclick = () => bereichWaehlen(k.dataset.ziel);
});
function menueSetzen() {
  // Am Schirm gibt es kein Menü: <details> muss dort offen sein, sonst
  // versteckt es seinen Inhalt, den die CSS-Regel längst wieder zeigt.
  const breit = window.matchMedia("(min-width: 62rem)").matches;
  if (breit) $("menue").open = true;
}

window.addEventListener("resize", () => { leisteAufbauen(); menueSetzen(); });
leisteAufbauen();
menueSetzen();
// Ein Klick ausserhalb schliesst das Menü — sonst bleibt es im Weg stehen.
document.addEventListener("click", (e) => {
  const menue = $("menue");
  if (menue.open && !menue.contains(e.target)
      && !window.matchMedia("(min-width: 62rem)").matches) {
    menue.open = false;
  }
});

sprachwahl("sprache");
$("nachreichen").onclick = nachreichen;
window.addEventListener("online", () => { zeigeBand(); nachreichen(); });
window.addEventListener("offline", zeigeBand);

if ("serviceWorker" in navigator) {
  // Ohne ihn ist die Seite im Funkloch weiß. Scheitert die Anmeldung
  // (privates Fenster, kein TLS), läuft alles wie bisher weiter.
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

$("laden").onclick = lade;
$("herde").onchange = lade;
$("stichtag").value = heute();
$("vorfalltag").value = heute();
$("abgangTag").value = heute();

fetch("/api/health").then((a) => a.json()).then((h) => {
  $("stempel").textContent = txt("Version") + " " + h.version + " \\u00b7 " + h.commit;
}).catch(() => {});

uebersetzeSeite();
zeigeBand();
nachreichen();
lade();
</script>
</body>
</html>
"""

_ANMELDUNG_MARKUP = """
body { display: grid; place-items: center; padding: 16px; }
main { width: min(26rem, 100%); padding: 24px; }
h1 { font-size: 1.4rem; margin: 0 0 4px; letter-spacing: -.01em; }
p.leise { color: var(--leise); font-size: .92rem; margin-top: 0; }
label { margin: 16px 0 4px; }
input, button { width: 100%; }
button[type=submit] {
  margin-top: 20px; background: var(--petrol); border-color: transparent;
  color: var(--grund); font-weight: 650;
}
#fehler { color: var(--terrakotta); font-weight: 650; margin-top: 16px; }
.wozu { margin: 14px 0 16px; padding: 0; list-style: none; font-size: .95rem; }
.wozu li {
  padding: 0 0 0 20px; margin-bottom: 8px; position: relative;
  overflow-wrap: anywhere;
}
.wozu li::before {
  content: "›"; position: absolute; inset-inline-start: 4px;
  color: var(--petrol); font-weight: 700;
}
.winzig { font-size: .84rem; }
.fuss { margin-top: 20px; display: flex; align-items: center; gap: 10px; }
.fuss label { margin: 0; white-space: nowrap; }
.fuss select { min-height: 38px; flex: 1 1 8rem; min-width: 0; }
</style>
</head>
<body>
<main class="glas">
  <h1>Taktgeber</h1>
  <p class="leise">Prophylaxe und Fütterung je Herde</p>
  <!-- Erster Kontakt. Wer hier steht, soll in zwei Sätzen wissen, wofür
       er sich anmeldet — und was das Werkzeug NICHT tut. -->
  <ul class="wozu">
    <li>Sagt jeden Tag, welche Impfung, Entwurmung oder Futterumstellung
        ansteht — gerechnet aus dem Einstalldatum.</li>
    <li>Rechnet den Mischauftrag und sperrt ihn, wenn das Rezept nicht
        aufgeht.</li>
    <li>Merkt sich, was abgehakt wurde, und meldet, was überfällig ist.</li>
  </ul>
  <p class="leise winzig">Der Plan entscheidet, nicht das Gefühl. Jeder Termin
     kommt aus einer Subtraktion, keiner aus einer Schätzung.</p>
  <form id="form">
    <label for="benutzer">Anmeldename</label>
    <input id="benutzer" name="benutzer" autocomplete="username" autocapitalize="none"
           required autofocus>
    <label for="passwort">Passwort</label>
    <input id="passwort" name="passwort" type="password"
           autocomplete="current-password" required>
    <button type="submit">Anmelden</button>
  </form>
  <p id="fehler" role="alert" hidden></p>
  <div class="fuss">
    <label for="sprache">Sprache</label>
    <select id="sprache">
      <option value="de">Deutsch</option>
      <option value="fr">Français</option>
    </select>
  </div>
</main>
<script>
"""

_ANMELDUNG_SKRIPT = """
const form = document.getElementById("form");
const fehler = document.getElementById("fehler");
form.onsubmit = async (ereignis) => {
  ereignis.preventDefault();
  fehler.hidden = true;
  const antwort = await fetch("/api/anmelden", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      benutzer: document.getElementById("benutzer").value,
      passwort: document.getElementById("passwort").value,
    }),
  });
  if (antwort.ok) { window.location.href = "/"; return; }
  const inhalt = await antwort.json().catch(() => ({}));
  fehler.textContent = txt(inhalt.fehler || "Anmeldung fehlgeschlagen.");
  fehler.hidden = false;
};

sprachwahl("sprache");
uebersetzeSeite();
</script>
</body>
</html>
"""

_ERSTER_MARKUP = """
body { display: grid; place-items: center; padding: 16px; }
main { width: min(36rem, 100%); padding: 24px; }
h1 { font-size: 1.4rem; margin: 0 0 8px; }
code {
  display: block; background: var(--glas-stark); border: 1px solid var(--kante);
  padding: 12px 14px; border-radius: 10px; margin-top: 12px;
  overflow-x: auto; font-size: .9rem;
}
.fuss { margin-top: 20px; display: flex; align-items: center; gap: 10px; }
.fuss label { margin: 0; white-space: nowrap; }
.fuss select { min-height: 38px; flex: 1 1 8rem; min-width: 0; }
</style>
</head>
<body>
<main class="glas">
  <h1>Noch kein Benutzer angelegt</h1>
  <p>Ohne Benutzer gibt es keine Anmeldung und damit keinen Zugang. Den ersten
     legst du auf dem Rechner an, auf dem der Taktgeber läuft:</p>
  <code>elevage benutzer --anlegen leitung --betrieb hof
       --name "Vorname Nachname" --rolle LEITUNG</code>
  <p>Das Passwort wird dabei abgefragt und steht nicht in der Kommandozeile.
     Danach diese Seite neu laden.</p>
  <div class="fuss">
    <label for="sprache">Sprache</label>
    <select id="sprache">
      <option value="de">Deutsch</option>
      <option value="fr">Français</option>
    </select>
  </div>
</main>
<script>
"""

_ERSTER_SKRIPT = """
sprachwahl("sprache");
uebersetzeSeite();
</script>
</body>
</html>
"""


def _baue(*teile: str) -> str:
    """Zusammensetzen und die beiden Platzhalter einsetzen — einmal je Seite."""
    return (
        "".join(teile).replace("FAVICON_HIER", FAVICON).replace("WOERTERBUCH_HIER", woerterbuch())
    )


SEITE = _baue(_KOPF, GRUNDLAGEN, BAUSTEINE, _SEITE_MARKUP, UEBERSETZER, _SEITE_SKRIPT)

ANMELDESEITE = _baue(_KOPF, GRUNDLAGEN, _ANMELDUNG_MARKUP, UEBERSETZER, _ANMELDUNG_SKRIPT)

ERSTER_BENUTZER = _baue(_KOPF, GRUNDLAGEN, _ERSTER_MARKUP, UEBERSETZER, _ERSTER_SKRIPT)
