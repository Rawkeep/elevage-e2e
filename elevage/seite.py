"""Die ganze Oberfläche als ein String — kein Build, kein CDN.

Gestaltet nach dem Architektur-Briefing (Branche Agrar, Zielgruppe intern):
erdige Töne statt Agrar-Grün-Klischee, große Schrift und Touch-Ziele ab
44 px für die Bedienung im Stehen und mit Handschuhen, wenig Bytes für
schmale Leitungen, Dark Mode über Tokens, Bewegung nur mit
`prefers-reduced-motion`. Farbe trägt nie allein — jede Ampel hat zusätzlich
ein Zeichen und ein Wort.

`test_seite.py` hält fest, dass hier keine externe Adresse steht.
"""

from __future__ import annotations

from elevage.sprache import woerterbuch

DIENER = """// Service Worker: die Seite muss auch ohne Netz aufgehen.
//
// Zwei getrennte Vorräte, weil sie Verschiedenes bedeuten: die SEITE ist
// unveränderlich (cache first, sonst wäre der Stall bei jedem Funkloch
// weiß), die DATEN sind es nicht (network first, damit niemand mit einem
// Tagesbild von gestern arbeitet, wenn ein frisches erreichbar ist).
const SEITE_VORRAT = "taktgeber-seite-v1";
const DATEN_VORRAT = "taktgeber-daten-v1";
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
    "%3Crect width='16' height='16' rx='3' fill='%2312525c'/%3E"
    "%3Crect x='4' y='3.5' width='8' height='2' rx='1' fill='%23faf7f2'/%3E"
    "%3Crect x='4' y='7' width='8' height='2' rx='1' fill='%23e0b352'/%3E"
    "%3Crect x='4' y='10.5' width='8' height='2' rx='1' fill='%23f09077'/%3E"
    "%3C/svg%3E"
)
"""Drei Balken in Rot, Gelb, Grün — das Zeichen der Seite, inline statt Datei.

Ohne dieses Zeichen fragt jeder Browser /favicon.ico an und bekommt 404."""

_ROH = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="FAVICON_HIER">
<title>Taktgeber</title>
<style>
:root {
  color-scheme: light dark;
  --grund: #faf7f2;      --karte: #ffffff;      --rand: #ddd2c4;
  --text: #241d16;       --leise: #5d5145;
  --terrakotta: #9c3d22; --petrol: #12525c;     --ocker: #8a6412;
  --rot-feld: #fbeae5;   --gelb-feld: #fdf3dd;  --gruen-feld: #e6f0ef;
  --schrift: 17px; --radius: 10px; --ziel: 44px;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-thema="hell"]) {
    --grund: #191512;    --karte: #221d19;      --rand: #3d342c;
    --text: #f3ece4;     --leise: #b9aa9a;
    --terrakotta: #f09077; --petrol: #7fc6d1;   --ocker: #e0b352;
    --rot-feld: #3a201a; --gelb-feld: #352c14;  --gruen-feld: #1b2e2c;
  }
}
:root[data-thema="dunkel"] {
  --grund: #191512;      --karte: #221d19;      --rand: #3d342c;
  --text: #f3ece4;       --leise: #b9aa9a;
  --terrakotta: #f09077; --petrol: #7fc6d1;     --ocker: #e0b352;
  --rot-feld: #3a201a;   --gelb-feld: #352c14;  --gruen-feld: #1b2e2c;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--grund); color: var(--text);
  font: var(--schrift)/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
.huelle { max-width: 62rem; margin: 0 auto; padding: 16px; }
h1 { font-size: 1.45rem; margin: 0 0 2px; }
h2 { font-size: 1.05rem; margin: 0 0 10px; letter-spacing: .04em; text-transform: uppercase;
     color: var(--leise); }
.leise { color: var(--leise); font-size: .92rem; }
.karte { background: var(--karte); border: 1px solid var(--rand); border-radius: var(--radius);
         padding: 14px; margin-bottom: 14px; }
.kopf { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; }
label { display: block; font-size: .85rem; color: var(--leise); margin-bottom: 3px; }
select, input, button {
  font: inherit; min-height: var(--ziel); border-radius: 8px;
  border: 1px solid var(--rand); background: var(--karte); color: var(--text);
  padding: 6px 12px;
}
button { cursor: pointer; }
button.tat { background: var(--petrol); border-color: var(--petrol); color: var(--grund);
             font-weight: 600; }
button.still { background: transparent; }
button:focus-visible, select:focus-visible, input:focus-visible {
  outline: 3px solid var(--ocker); outline-offset: 2px;
}
.lage { display: inline-flex; align-items: center; gap: 8px; font-weight: 700;
        padding: 6px 14px; border-radius: 999px; border: 2px solid currentColor; }
.ROT { color: var(--terrakotta); } .GELB { color: var(--ocker); }
.GRUEN, .ERLEDIGT { color: var(--petrol); }
li.posten { list-style: none; border-left: 5px solid var(--rand); border-radius: 6px;
            padding: 10px 12px; margin-bottom: 8px; background: var(--grund); }
li.ROT { border-left-color: var(--terrakotta); background: var(--rot-feld); }
li.GELB { border-left-color: var(--ocker); background: var(--gelb-feld); }
li.GRUEN, li.ERLEDIGT { border-left-color: var(--petrol); background: var(--gruen-feld); }
ul { margin: 0; padding: 0; }
.titel { font-weight: 650; }
.mittel { font-size: .9rem; color: var(--leise); }
.reihe { display: flex; flex-wrap: wrap; gap: 8px; align-items: flex-start;
         justify-content: space-between; }
li.posten .reihe > :first-child { flex: 1 1 18rem; min-width: 0; }
li.posten .reihe > :last-child { flex: 0 0 auto; text-align: right; }
header .reihe, #kopfzahlen .reihe { align-items: center; }
.frist { font-variant-numeric: tabular-nums; font-weight: 700; white-space: nowrap; }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--rand); }
td.zahl, th.zahl { text-align: right; }
.huelle-breit { overflow-x: auto; }
.befund { font-size: .9rem; border-left: 4px solid var(--ocker); padding-left: 10px;
          margin-bottom: 8px; color: var(--leise); }
.toast { position: fixed; inset-block-end: 16px; inset-inline: 16px; max-width: 34rem;
         margin-inline: auto; background: var(--text); color: var(--grund);
         border-radius: var(--radius); padding: 12px 16px; display: flex; gap: 12px;
         align-items: center; justify-content: space-between; }
.toast button { background: transparent; border-color: currentColor; color: inherit;
                min-height: 36px; }
[hidden] { display: none !important; }
body[data-rolle="LESER"] button.tat:not(#laden):not(#rechnen) { display: none; }
body:not([data-rolle="LEITUNG"]) #vermerke button { display: none; }
.leer { color: var(--leise); padding: 8px 0; }
@media (prefers-reduced-motion: no-preference) {
  .toast { animation: hoch .2s ease-out; }
  @keyframes hoch { from { transform: translateY(8px); opacity: 0; } }
}
</style>
</head>
<body>
<div class="huelle">

<p class="karte" id="offlineband" role="status" hidden
   style="border-color:var(--ocker);background:var(--gelb-feld);font-weight:650">
  <span id="offlinetext"></span>
  <button class="still" id="nachreichen" type="button"
          style="margin-left:10px;min-height:36px">Jetzt nachreichen</button>
</p>

<header class="karte">
  <div class="reihe">
    <div>
      <h1>Taktgeber</h1>
      <p class="leise" id="unterzeile">Prophylaxe und Fütterung je Herde</p>
    </div>
    <div style="display:flex;gap:8px;align-items:center">
      <span class="leise" id="wer"></span>
      <label for="sprache" style="margin:0">Sprache</label>
      <select id="sprache" style="min-height:36px;padding:2px 8px">
        <option value="de">Deutsch</option>
        <option value="fr">Français</option>
      </select>
      <button class="still" id="thema" type="button">Ansicht wechseln</button>
      <button class="still" id="abmelden" type="button">Abmelden</button>
    </div>
  </div>
  <div class="kopf" style="margin-top:12px">
    <div><label for="herde">Herde</label><select id="herde"></select></div>
    <div><label for="stichtag">Stichtag</label><input id="stichtag" type="date"></div>
    <div><label for="vorrat">Futtervorrat (kg)</label>
      <input id="vorrat" type="number" min="0" step="10" size="6" placeholder="optional"></div>
    <button class="tat" id="laden" type="button">Anzeigen</button>
  </div>
</header>

<p id="zustand" class="karte" role="status">Lade …</p>

<section class="karte" id="kopfzahlen" hidden>
  <div class="reihe">
    <span class="lage" id="lage"></span>
    <span class="leise" id="alter"></span>
  </div>
  <p class="leise" id="phase" style="margin-bottom:0"></p>
</section>

<section class="karte" id="sperre" hidden>
  <h2>Wartezeit</h2>
  <p id="sperrtext" style="margin:0;font-weight:650"></p>
  <ul id="sperrliste" style="margin-top:8px"></ul>
</section>

<section class="karte" id="futter" hidden>
  <h2>Futter</h2>
  <p id="futtertext" style="margin:0"></p>
  <p class="leise" id="futterherkunft" style="margin:4px 0 0"></p>
</section>

<section class="karte" id="block-ueberfaellig" hidden><h2>Überfällig</h2><ul></ul></section>
<section class="karte" id="block-heute" hidden><h2>Jetzt dran</h2><ul></ul></section>
<section class="karte" id="block-bestellen" hidden>
  <h2>Jetzt besorgen</h2>
  <p class="leise" style="margin:-6px 0 10px">Vorlauf läuft — muss da sein, bevor der Tag kommt.</p>
  <ul></ul>
</section>
<section class="karte" id="block-demnaechst" hidden><h2>Demnächst</h2><ul></ul></section>
<section class="karte" id="block-erledigt" hidden><h2>Zuletzt erledigt</h2><ul></ul></section>

<section class="karte" id="block-vermerke" hidden>
  <h2>Zu prüfen</h2>
  <p class="leise" style="margin:-6px 0 10px">Bleibt liegen, bis jemand am Original nachsieht.</p>
  <ul id="vermerke"></ul>
</section>

<section class="karte">
  <h2>Mischauftrag</h2>
  <div class="kopf">
    <div><label for="menge">Menge (kg)</label>
      <input id="menge" type="number" min="1" step="50" value="500"></div>
    <div><label for="art">Bei Überhang</label>
      <select id="art">
        <option value="AUSGLEICH">über den Energieträger ausgleichen</option>
        <option value="VERBATIM">wie auf dem Blatt rechnen</option>
        <option value="ANTEILIG">alles anteilig skalieren</option>
      </select></div>
    <button class="tat" id="rechnen" type="button">Rechnen</button>
    <button class="still" id="buchen" type="button" hidden>Als gemischt buchen</button>
  </div>
  <div id="mischung" class="huelle-breit" style="margin-top:10px"></div>
</section>

<section class="karte">
  <h2>Abgang buchen</h2>
  <div class="kopf">
    <div><label for="abgangtiere">Tiere</label>
      <input id="abgangtiere" type="number" min="1" step="1" style="width:6rem"></div>
    <div><label for="abgangGrund">Grund</label>
      <select id="abgangGrund">
        <option value="VERENDET">verendet</option>
        <option value="GEKEULT">gekeult</option>
        <option value="VERKAUFT">verkauft</option>
        <option value="SONSTIGES">sonstiges</option>
      </select></div>
    <div><label for="abgangTag">Am</label><input id="abgangTag" type="date"></div>
    <button class="tat" id="buchen-abgang" type="button">Buchen</button>
  </div>
  <p class="leise" style="margin-bottom:0">Verkauft ist kein Verlust — der Grund
     entscheidet, ob es in die Verlustquote zählt.</p>
</section>

<section class="karte">
  <h2>Vorfall melden</h2>
  <div class="kopf">
    <div><label for="vorfallart">Art</label>
      <select id="vorfallart"><option value="GUMBORO">Gumboro</option></select></div>
    <div><label for="vorfalltag">Festgestellt am</label><input id="vorfalltag" type="date"></div>
    <div style="flex:1 1 12rem"><label for="vorfalltext">Beobachtung</label>
      <input id="vorfalltext" style="width:100%" placeholder="optional"></div>
    <button class="tat" id="melden" type="button">Melden</button>
  </div>
  <p class="leise" style="margin-bottom:0">Das Schema startet am gemeldeten Tag.</p>
</section>

<section class="karte" id="block-befunde" hidden><h2>Befunde</h2><div id="befunde"></div></section>

<footer class="leise" style="text-align:center;padding:8px 0 20px">
  <span id="stempel"></span>
</footer>

</div>

<div class="toast" id="toast" hidden>
  <span id="toasttext"></span>
  <button type="button" id="undo">Rückgängig</button>
</div>

<script>
const $ = (id) => document.getElementById(id);

// Nur die Oberfläche wird übersetzt, nicht die Daten: Präparatnamen,
// Rezeptposten und Befunde bleiben, wie sie sind. Ein Befund, der in der
// Übersetzung eine Nuance verliert, ist schlimmer als einer auf Deutsch.
const WOERTER = WOERTERBUCH_HIER;
let SPRACHE = "de";
try { SPRACHE = localStorage.getItem("taktgeber-sprache") || "de"; } catch (f) {}

function txt(text) {
  // Heißt NICHT t(): so heißt in diesem Skript überall der Termin, und ein
  // verdeckter Name ergibt zur Laufzeit "t is not a function".
  const buch = WOERTER[SPRACHE];
  return (buch && buch[text]) || text;   // fehlt eine Vokabel: deutscher Text
}

function uebersetzeSeite() {
  if (SPRACHE === "de") return;
  const lauf = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const knoten = [];
  while (lauf.nextNode()) knoten.push(lauf.currentNode);
  knoten.forEach((k) => {
    const roh = k.nodeValue.trim();
    if (!roh) return;
    const uebersetzt = txt(roh);
    if (uebersetzt !== roh) k.nodeValue = k.nodeValue.replace(roh, uebersetzt);
  });
  document.querySelectorAll("[placeholder]").forEach((feld) => {
    feld.placeholder = txt(feld.placeholder);
  });
  document.documentElement.lang = SPRACHE;
}
const heute = () => new Date().toISOString().slice(0, 10);
let bild = null;
let letzteQuittung = null;

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
    ? (offen.length ? "Kein Netz \u00b7 " + offen.length + " Eingabe(n) warten"
                    : "Kein Netz \u2014 die Seite arbeitet aus dem Zwischenspeicher.")
    : offen.length + " Eingabe(n) noch nicht beim Server";
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
  // Geht der Versand nicht durch, wandert die Eingabe in die
  // Warteschlange statt verloren zu gehen. Möglich ist das nur, weil die
  // Nummern serverseitig aus dem Inhalt entstehen: zweimal geschickt
  // wirkt einmal.
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
  if (antwort.status === 401) { window.location.href = "/anmelden"; throw new Error("abgemeldet"); }
  const inhalt = await antwort.json();
  if (!antwort.ok) throw new Error(inhalt.fehler || "Unbekannter Fehler");
  return inhalt;
}

function melde(text, rueckgaengig) {
  $("toasttext").textContent = text;
  $("undo").hidden = !rueckgaengig;
  $("toast").hidden = false;
  clearTimeout(melde.uhr);
  melde.uhr = setTimeout(() => { $("toast").hidden = true; }, 9000);
}

function postenZeile(t, mitKnopf) {
  const li = document.createElement("li");
  li.className = "posten " + t.ampel;
  const kopf = document.createElement("div");
  kopf.className = "reihe";
  const links = document.createElement("div");
  const titel = document.createElement("div");
  titel.className = "titel";
  titel.textContent = zeichen(t.ampel) + " " + t.titel;
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
    h.textContent = t.hinweis;
    links.appendChild(h);
  }
  if (t.erledigtAm) {
    const e = document.createElement("div");
    e.className = "mittel";
    e.textContent = "erledigt am " + t.erledigtAm + (t.lot ? " \\u00b7 Charge " + t.lot : "");
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

function fuelle(id, liste, mitKnopf) {
  const block = $(id);
  const ul = block.querySelector("ul");
  ul.replaceChildren();
  liste.forEach((t) => ul.appendChild(postenZeile(t, mitKnopf)));
  block.hidden = liste.length === 0;
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
  $("zustand").textContent = "Lade \\u2026";
  try {
    const ich = await hole("/api/ich");
    $("wer").textContent = ich.name + " \\u00b7 " + ich.tenantId + " \\u00b7 " + ich.rolle;
    document.body.dataset.rolle = ich.rolle;
    const anzahl = await ladeHerden();
    if (!anzahl) {
      $("zustand").textContent =
        "Noch keine Herde für diesen Betrieb. Anlegen mit: elevage einstallen \\u2026";
      ["kopfzahlen", "futter", "block-ueberfaellig", "block-heute", "block-bestellen",
       "block-demnaechst", "block-erledigt", "block-befunde"].forEach((i) => $(i).hidden = true);
      return;
    }
    const p = new URLSearchParams({
      herde: $("herde").value, stichtag: $("stichtag").value,
    });
    if ($("vorrat").value) p.set("vorrat", $("vorrat").value);
    bild = await hole("/api/tagesbild?" + p);
    zeige();
    $("zustand").hidden = true;
  } catch (fehler) {
    $("zustand").hidden = false;
    $("zustand").textContent = txt("Das hat nicht geklappt: ") + fehler.message;
  }
}

function zeige() {
  $("lage").textContent = zeichen(bild.ampel) + " " + wort(bild.ampel);
  $("lage").className = "lage " + bild.ampel;
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
    ? txt("Futterphase") + ": " + bild.phase.name
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
      li.textContent = s.praeparat + " \u00b7 letzte Gabe " + s.letzteGabe
        + " \u00b7 " + s.wartezeitTage + " Tage \u00b7 frei ab " + s.freigabeAb;
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
                              : "Richtwert \\u2014 keine Zahl dieses Betriebs.");
    $("futter").hidden = false;
  } else { $("futter").hidden = true; }

  fuelle("block-ueberfaellig", bild.ueberfaellig, true);
  fuelle("block-heute", bild.heute, true);
  fuelle("block-bestellen", bild.bestellen, false);
  const schonGenannt = new Set(bild.bestellen.map((t) => t.schrittKey));
  fuelle(
    "block-demnaechst",
    bild.demnaechst.filter((t) => !schonGenannt.has(t.schrittKey)),
    false
  );
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
    kopf.textContent = "\u203a " + v.betrifft;
    const text = document.createElement("div");
    text.className = "mittel";
    text.textContent = v.text;
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
    p.textContent = i;
    kasten.appendChild(p);
  });
  $("block-befunde").hidden = bild.issues.length === 0;
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
      melde("\\u201e" + t.titel + "\\u201c abgehakt \\u2014 wird nachgereicht.", false);
      return;
    }
    letzteQuittung = antwort.quittungId;
    melde("\\u201e" + t.titel + "\\u201c abgehakt.", true);
    await lade();
  } catch (fehler) { melde("Nicht abgehakt: " + fehler.message, false); }
}

$("undo").onclick = async () => {
  if (!letzteQuittung) return;
  await hole("/api/quittung/widerrufen", {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ quittungId: letzteQuittung }),
  });
  letzteQuittung = null;
  $("toast").hidden = true;
  await lade();
};

async function hakeAb(v) {
  try {
    await sendeOderMerken("/api/vermerk/abhaken", {
      vermerkId: v.vermerkId, am: $("stichtag").value,
    });
    melde("Als geprüft abgehakt.", false);
    await lade();
  } catch (fehler) { melde("Nicht abgehakt: " + fehler.message, false); }
}

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
    if (!a.auftrag) { ziel.textContent = "Kein Rezept für diese Linie."; return; }
    const t = document.createElement("table");
    const kopf = t.createTHead().insertRow();
    ["Rohstoff", "kg"].forEach((x, i) => {
      const th = document.createElement("th");
      th.textContent = x; if (i) th.className = "zahl"; kopf.appendChild(th);
    });
    const koerperEl = t.createTBody();
    a.auftrag.zeilen.forEach((z) => {
      const r = koerperEl.insertRow();
      r.insertCell().textContent = z.name;
      const c = r.insertCell(); c.textContent = z.kg.toFixed(2); c.className = "zahl";
    });
    const summe = koerperEl.insertRow();
    summe.insertCell().textContent = "Ist-Einwaage";
    const sc = summe.insertCell();
    sc.textContent = a.auftrag.istEinwaageKg.toFixed(2); sc.className = "zahl";
    summe.style.fontWeight = "700";
    ziel.appendChild(t);
    a.auftrag.issues.forEach((i) => {
      const p = document.createElement("p"); p.className = "befund"; p.textContent = i;
      ziel.appendChild(p);
    });
    $("buchen").hidden = !a.auftrag.freigegeben || a.auftrag.ausgleich === "VERBATIM";
    if (buchen) melde(a.gebucht ? "Mischung protokolliert." : "Nicht gebucht.", false);
  } catch (fehler) { ziel.textContent = txt("Das hat nicht geklappt: ") + fehler.message; }
}

$("rechnen").onclick = () => rechne(false);
$("buchen").onclick = () => rechne(true).then(lade);

$("melden").onclick = async () => {
  try {
    await sendeOderMerken("/api/vorfall", {
      herde: $("herde").value, art: $("vorfallart").value,
      am: $("vorfalltag").value, bemerkung: $("vorfalltext").value || null,
    });
    melde("Vorfall aufgenommen \\u2014 das Schema steht im Plan.", false);
    $("vorfalltext").value = "";
    await lade();
  } catch (fehler) { melde("Nicht aufgenommen: " + fehler.message, false); }
};

$("buchen-abgang").onclick = async () => {
  const tiere = Number($("abgangtiere").value);
  if (!tiere) { melde("Wie viele Tiere?", false); return; }
  try {
    await sendeOderMerken("/api/abgang", {
      herde: $("herde").value, tiere: tiere,
      grund: $("abgangGrund").value, am: $("abgangTag").value,
    });
    $("abgangtiere").value = "";
    melde("Gebucht \u2014 der Futterbedarf rechnet ab jetzt damit.", false);
    await lade();
  } catch (fehler) { melde("Nicht gebucht: " + fehler.message, false); }
};

$("thema").onclick = () => {
  const jetzt = document.documentElement.dataset.thema;
  document.documentElement.dataset.thema = jetzt === "dunkel" ? "hell" : "dunkel";
};

$("abmelden").onclick = async () => {
  await fetch("/api/abmelden", { method: "POST" });
  window.location.href = "/anmelden";
};

$("sprache").value = SPRACHE;
$("sprache").onchange = () => {
  SPRACHE = $("sprache").value;
  try { localStorage.setItem("taktgeber-sprache", SPRACHE); } catch (f) {}
  window.location.reload();   // einmal sauber neu aufbauen statt halb übersetzt
};

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
  $("stempel").textContent = "Version " + h.version + " \u00b7 " + h.commit;
}).catch(() => {});

uebersetzeSeite();
zeigeBand();
nachreichen();
lade();
</script>
</body>
</html>
"""

SEITE = _ROH.replace("FAVICON_HIER", FAVICON).replace("WOERTERBUCH_HIER", woerterbuch())

ANMELDESEITE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Taktgeber — Anmeldung</title>
<style>
:root {
  color-scheme: light dark;
  --grund: #faf7f2; --karte: #ffffff; --rand: #ddd2c4;
  --text: #241d16; --leise: #5d5145; --petrol: #12525c; --terrakotta: #9c3d22;
}
@media (prefers-color-scheme: dark) {
  :root { --grund: #191512; --karte: #221d19; --rand: #3d342c;
          --text: #f3ece4; --leise: #b9aa9a; --petrol: #7fc6d1; --terrakotta: #f09077; }
}
* { box-sizing: border-box; }
body { margin: 0; min-height: 100vh; display: grid; place-items: center;
       background: var(--grund); color: var(--text);
       font: 17px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { width: min(26rem, 100% - 32px); background: var(--karte);
       border: 1px solid var(--rand); border-radius: 10px; padding: 22px; }
h1 { font-size: 1.35rem; margin: 0 0 4px; }
p.leise { color: var(--leise); font-size: .92rem; margin-top: 0; }
label { display: block; font-size: .85rem; color: var(--leise); margin: 14px 0 3px; }
input, button { font: inherit; width: 100%; min-height: 44px; border-radius: 8px;
                border: 1px solid var(--rand); background: var(--grund);
                color: var(--text); padding: 6px 12px; }
button { margin-top: 18px; background: var(--petrol); border-color: var(--petrol);
         color: var(--grund); font-weight: 600; cursor: pointer; }
input:focus-visible, button:focus-visible { outline: 3px solid var(--petrol);
                                            outline-offset: 2px; }
#fehler { color: var(--terrakotta); font-weight: 600; margin-top: 14px; }
[hidden] { display: none !important; }
body[data-rolle="LESER"] button.tat:not(#laden):not(#rechnen) { display: none; }
body:not([data-rolle="LEITUNG"]) #vermerke button { display: none; }
</style>
</head>
<body>
<main>
  <h1>Taktgeber</h1>
  <p class="leise">Prophylaxe und Fütterung je Herde</p>
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
</main>
<script>
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
  fehler.textContent = inhalt.fehler || "Anmeldung fehlgeschlagen.";
  fehler.hidden = false;
};
</script>
</body>
</html>
"""

ERSTER_BENUTZER = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Taktgeber — noch kein Benutzer</title>
<style>
body { margin: 0; min-height: 100vh; display: grid; place-items: center;
       background: #faf7f2; color: #241d16;
       font: 17px/1.6 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { width: min(34rem, 100% - 32px); background: #fff; border: 1px solid #ddd2c4;
       border-radius: 10px; padding: 22px; }
code { display: block; background: #f2ece3; padding: 10px 12px; border-radius: 8px;
       margin-top: 10px; overflow-x: auto; }
</style>
</head>
<body>
<main>
  <h1>Noch kein Benutzer angelegt</h1>
  <p>Ohne Benutzer gibt es keine Anmeldung und damit keinen Zugang. Den ersten
     legst du auf dem Rechner an, auf dem der Taktgeber läuft:</p>
  <code>elevage benutzer --anlegen leitung --betrieb hof
       --name "Vorname Nachname" --rolle LEITUNG</code>
  <p>Das Passwort wird dabei abgefragt und steht nicht in der Kommandozeile.
     Danach diese Seite neu laden.</p>
</main>
</body>
</html>
"""
