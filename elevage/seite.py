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

SEITE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
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
.leer { color: var(--leise); padding: 8px 0; }
@media (prefers-reduced-motion: no-preference) {
  .toast { animation: hoch .2s ease-out; }
  @keyframes hoch { from { transform: translateY(8px); opacity: 0; } }
}
</style>
</head>
<body>
<div class="huelle">

<header class="karte">
  <div class="reihe">
    <div>
      <h1>Taktgeber</h1>
      <p class="leise" id="unterzeile">Prophylaxe und Fütterung je Herde</p>
    </div>
    <button class="still" id="thema" type="button">Ansicht wechseln</button>
  </div>
  <div class="kopf" style="margin-top:12px">
    <div><label for="betrieb">Betrieb</label>
      <input id="betrieb" value="standard" size="12"></div>
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

<section class="karte">
  <h2>Mischauftrag</h2>
  <div class="kopf">
    <div><label for="menge">Menge (kg)</label>
      <input id="menge" type="number" min="1" step="50" value="500"></div>
    <button class="tat" id="rechnen" type="button">Rechnen</button>
    <button class="still" id="buchen" type="button" hidden>Als gemischt buchen</button>
  </div>
  <div id="mischung" class="huelle-breit" style="margin-top:10px"></div>
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

</div>

<div class="toast" id="toast" hidden>
  <span id="toasttext"></span>
  <button type="button" id="undo">Rückgängig</button>
</div>

<script>
const $ = (id) => document.getElementById(id);
const heute = () => new Date().toISOString().slice(0, 10);
let bild = null;
let letzteQuittung = null;

function zeichen(ampel) {
  return { ROT: "!", GELB: "\\u203a", GRUEN: "\\u00b7", ERLEDIGT: "\\u2713" }[ampel] || "";
}
function wort(ampel) {
  return { ROT: "überfällig", GELB: "jetzt dran", GRUEN: "geplant", ERLEDIGT: "erledigt" }[ampel];
}
function fenster(t) {
  const kurz = (s) => s.slice(8, 10) + "." + s.slice(5, 7) + ".";
  return t.faelligVon === t.faelligBis ? kurz(t.faelligVon)
       : kurz(t.faelligVon) + "\\u2013" + kurz(t.faelligBis);
}

async function hole(pfad, optionen) {
  const antwort = await fetch(pfad, optionen);
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
    knopf.textContent = "Erledigt";
    knopf.style.marginTop = "6px";
    knopf.onclick = () => quittiere(t);
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
  const daten = await hole("/api/herden?betrieb=" + encodeURIComponent($("betrieb").value));
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
    const anzahl = await ladeHerden();
    if (!anzahl) {
      $("zustand").textContent =
        "Noch keine Herde für diesen Betrieb. Anlegen mit: elevage einstallen \\u2026";
      ["kopfzahlen", "futter", "block-ueberfaellig", "block-heute", "block-bestellen",
       "block-demnaechst", "block-erledigt", "block-befunde"].forEach((i) => $(i).hidden = true);
      return;
    }
    const p = new URLSearchParams({
      betrieb: $("betrieb").value, herde: $("herde").value, stichtag: $("stichtag").value,
    });
    if ($("vorrat").value) p.set("vorrat", $("vorrat").value);
    bild = await hole("/api/tagesbild?" + p);
    zeige();
    $("zustand").hidden = true;
  } catch (fehler) {
    $("zustand").hidden = false;
    $("zustand").textContent = "Das hat nicht geklappt: " + fehler.message;
  }
}

function zeige() {
  $("lage").textContent = zeichen(bild.ampel) + " " + wort(bild.ampel);
  $("lage").className = "lage " + bild.ampel;
  $("alter").textContent =
    "Tag " + bild.alterTage + " \\u00b7 Woche " + bild.alterWochen + " \\u00b7 "
    + bild.herde.tierzahl + " Tiere";
  $("phase").textContent = bild.phase ? "Futterphase: " + bild.phase.name
                                      : "Für diese Linie liegt kein Futterblatt vor.";
  $("kopfzahlen").hidden = false;

  const f = bild.futter;
  if (f && f.bedarfJeTagKg !== null) {
    let text = f.grammJeTierTag + " g/Tier/Tag \\u00b7 " + f.bedarfJeTagKg + " kg am Tag \\u00b7 "
             + f.bedarfBisHorizontKg + " kg für " + f.horizontTage + " Tage";
    if (f.reichtBis) text += " \\u00b7 Vorrat reicht bis " + f.reichtBis
                           + ", bestellen ab " + f.bestellenAb;
    $("futtertext").textContent = text;
    $("futterherkunft").textContent =
      f.quelle === "GEMESSEN" ? "Aus dem eigenen Mischprotokoll gerechnet."
                              : "Richtwert \\u2014 keine Zahl dieses Betriebs.";
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

  const kasten = $("befunde");
  kasten.replaceChildren();
  bild.issues.forEach((i) => {
    const p = document.createElement("p");
    p.className = "befund";
    p.textContent = i;
    kasten.appendChild(p);
  });
  $("block-befunde").hidden = bild.issues.length === 0;
}

async function quittiere(t) {
  try {
    const antwort = await hole("/api/quittung", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        betrieb: $("betrieb").value, herde: $("herde").value,
        schritt: t.schrittKey, am: $("stichtag").value,
      }),
    });
    letzteQuittung = antwort.quittungId;
    melde("\\u201e" + t.titel + "\\u201c abgehakt.", true);
    await lade();
  } catch (fehler) { melde("Nicht abgehakt: " + fehler.message, false); }
}

$("undo").onclick = async () => {
  if (!letzteQuittung) return;
  await hole("/api/quittung/widerrufen", {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ betrieb: $("betrieb").value, quittungId: letzteQuittung }),
  });
  letzteQuittung = null;
  $("toast").hidden = true;
  await lade();
};

async function rechne(buchen) {
  const koerper = {
    betrieb: $("betrieb").value, herde: $("herde").value,
    kg: Number($("menge").value), am: $("stichtag").value, buchen: !!buchen,
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
    $("buchen").hidden = !a.auftrag.freigegeben;
    if (buchen) melde(a.gebucht ? "Mischung protokolliert." : "Nicht gebucht.", false);
  } catch (fehler) { ziel.textContent = "Das hat nicht geklappt: " + fehler.message; }
}

$("rechnen").onclick = () => rechne(false);
$("buchen").onclick = () => rechne(true).then(lade);

$("melden").onclick = async () => {
  try {
    await hole("/api/vorfall", {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({
        betrieb: $("betrieb").value, herde: $("herde").value,
        art: $("vorfallart").value, am: $("vorfalltag").value,
        bemerkung: $("vorfalltext").value || null,
      }),
    });
    melde("Vorfall aufgenommen \\u2014 das Schema steht im Plan.", false);
    $("vorfalltext").value = "";
    await lade();
  } catch (fehler) { melde("Nicht aufgenommen: " + fehler.message, false); }
};

$("thema").onclick = () => {
  const jetzt = document.documentElement.dataset.thema;
  document.documentElement.dataset.thema = jetzt === "dunkel" ? "hell" : "dunkel";
};

$("laden").onclick = lade;
$("betrieb").onchange = lade;
$("herde").onchange = lade;
$("stichtag").value = heute();
$("vorfalltag").value = heute();
lade();
</script>
</body>
</html>
"""
