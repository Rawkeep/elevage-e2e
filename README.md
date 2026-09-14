# elevage-e2e — der Taktgeber

Ein Werkzeug für die Geflügelhaltung: es taktet **Prophylaxe** und
**Fütterung** je Herde, rechnet aus dem Einstalldatum, meldet Überfälliges
und sperrt einen Mischauftrag, dessen Rezept nicht aufgeht.

**Leitsatz:** Der Plan entscheidet, nicht das Gefühl — und schon gar nicht
ein Sprachmodell. Ein Impftermin fällt aus einer Subtraktion, sonst aus
nichts.

## Was es kann

```bash
python3 -m elevage.cli demo                       # drei Szenarien, ohne Datenbank

python3 -m elevage.cli einstallen --betrieb hof --herde H1 --name "Stall Nord" \
    --tierart LEGEHENNE --einstall 2026-03-02 --tiere 1200 [--programm VETO_PONDEUSE]
python3 -m elevage.cli herden --betrieb hof

python3 -m elevage.cli programm                              # welche Blätter es gibt
python3 -m elevage.cli programm --zeigen VETO_PONDEUSE       # ein Blatt ganz
python3 -m elevage.cli programm --vergleich IVOGRAIN_PONDEUSE VETO_PONDEUSE
python3 -m elevage.cli programm --betrieb hof --herde H1 --waehlen VETO_PONDEUSE
python3 -m elevage.cli tierarzt --betrieb hof --name "Dr. Beispiel" --telefon 0000
python3 -m elevage.cli tagesbild --betrieb hof --herde H1 --stichtag 2026-03-06 --mischen 500 --vorrat 400
python3 -m elevage.cli quittieren --betrieb hof --herde H1 \
    --schritt PONDEUSE_J7_GUMBORO_1 --am 2026-03-08 --durch Kofi --lot LOT-4711
python3 -m elevage.cli gemischt --betrieb hof --herde H1 --kg 500 --am 2026-03-09
python3 -m elevage.cli verzehr --betrieb hof --herde H1
python3 -m elevage.cli vorfall --betrieb hof --herde H1 --art GUMBORO --am 2026-03-24
python3 -m elevage.cli ausstallen --betrieb hof --herde H1   # Historie bleibt

python3 -m elevage.cli mischung --rezept PONTE_AB_21 --kg 1000 [--normieren]

python3 -m elevage.cli rezept --betrieb hof --rezept PONTE_AB_21 \
    --artikel MAIS --kg 43.3 --grund "am Original geprüft" --am 2026-03-20
python3 -m elevage.cli pruefliste --betrieb hof        # Exit 2, solange etwas offen ist
python3 -m elevage.cli einstellung --betrieb hof \
    --schluessel notfall.dosis.LEGEHENNE --wert "0,75 g/l"
python3 -m elevage.cli benutzer --betrieb hof --anlegen kofi --name "Kofi A." --rolle LEITUNG

python3 -m elevage.cli ui                    # Oberfläche auf 127.0.0.1:8791
```

Die Datenbank liegt unter `~/.elevage/elevage.db`; `--db` oder die
Umgebungsvariable `ELEVAGE_DB` legen sie woandershin.

`tagesbild` beendet sich mit Code 2, wenn etwas überfällig ist — damit kann
ein Wächter-Job daran hängen, ohne die Ausgabe zu lesen.

## Aufbau

| Modul | Aufgabe |
|---|---|
| `models.py` | Der Vertrag (Pydantic, JSON bleibt camelCase) — Änderungen hier zuerst |
| `programme.py` | Die Prophylaxe-Blätter als Daten, verbatim; wählbar je Herde |
| `vergleich.py` | Zwei Blätter gegenübergestellt — gerechnet, nicht formuliert |
| `rezepte.py` | Die drei Futter-Rezepturen + Artikelstamm |
| `plan.py` | Vorlage + Herde = Termine mit echten Daten, Ampel, Quittungen |
| `mischung.py` | Rezept × Chargengröße, mit Summenprobe und Sperre |
| `takt.py` | `rechne(herde, stichtag)` — das ganze Tagesbild |
| `notfall.py` | Gumboro-Schema und Leberschutz beim Futterwechsel (NB-Kasten) |
| `wartezeit.py` | Ab wann nach einer Behandlung wieder vermarktet werden darf |
| `bestand.py` | Wie viele Tiere wirklich im Stall stehen |
| `sprache.py` | Wörterbuch Deutsch/Französisch für die Oberfläche (Vorgabe: FR) |
| `version.py` | Ein Versionsstempel, gelesen statt zweimal geschrieben |
| `verzehr.py` | Verzehrkurve: gemessen aus dem Mischprotokoll, sonst Richtwert |
| `archiv.py` | SQLite (Stdlib): Herden, Quittungen, Mischprotokoll, Vorfälle |
| `betrieb.py` | Die Naht: Archiv rein, Tagesbild raus |
| `seite.py` | Die ganze Oberfläche als ein String — kein Build, kein CDN |
| `server.py` | Stdlib-HTTP-Server: Sitzungen, Rollen, Ratenbremse |
| `anmeldung.py` | Passwörter (scrypt) und Sitzungsmerkmale |
| `anpassung.py` | Blatt + Betriebsanpassungen = wirksames Rezept |
| `einstellung.py` | Was vom Blatt abweichen darf, weicht hier ab |
| `cli.py` | Dünne Schale, keine eigene Logik |

Datenfluss: `Herde` + `Stichtag` → `plan.schritte_fuer()` (Programm +
Legeperiode + Futterwechsel + ausgelöste Notfallschemata) →
`plan.baue_termine()` → `takt.rechne()` → `Tagesbild`. Die Oberfläche hängt
nur daran und ist austauschbar.

## Die Verzehrkurve lernt sich selbst

Ohne g/Tier/Tag gibt es keine Reichweite und keinen Bestelltag. Die Zahl
kommt aus zwei Quellen, in dieser Reihenfolge:

1. **Gemessen** aus dem eigenen Mischprotokoll — was zwischen zwei
   Mischungen verbraucht wurde, geteilt durch Tierzahl und Tage. Rasse,
   Klima und Fütterung stecken darin schon drin.
2. **Richtwert** als Lückenfüller. Die Werte in `verzehr.py` sind grobe
   Orientierung, **keine Betriebsdaten**, und werden von jedem gemessenen
   Punkt geschlagen.

Jeder Kurvenpunkt trägt seine Herkunft, und jede Prognose auf Richtwerten
sagt das im Klartext. Drei protokollierte Mischungen genügen, damit die
ersten Wochen auf eigenen Zahlen stehen.

## Was ein Vorfall auslöst

`elevage vorfall --art GUMBORO --am …` legt ein Ereignis ab und erzeugt
daraus zwei ganz normale Schritte — gleiche Ampel, gleiche Quittung:

| Tage | Schritt |
|---|---|
| Tag des Vorfalls + 3 | Desinfektion (VIRKON/VIRUNET) + Antikokzidium 1 g/l |
| danach + 3 | Leberschutz, um die Futteraufnahme wieder anzuschieben |

Dazu ohne Ereignis, aus den Rezepten abgeleitet: **Leberschutz von j-1 bis
j+2 um jeden Futterwechsel** (Tag 57 und Tag 148) — das verlangt der
NB-Kasten des Junghennen-Blattes, und es steht in keinem Tagesraster.

## Demo ansehen

**https://rawkeep.github.io/elevage-e2e/** — dieselbe Oberfläche mit
erfundenen Betriebsdaten. Abhaken, Rückgängig und die drei Ausgleichswege
funktionieren; Eingaben bleiben im Browser, gespeichert wird nichts.

Es gibt **nur eine Oberfläche**: die Demo ist `seite.SEITE`, davor geschoben
eine Attrappe für `fetch`, die vorgerechnete Antworten liefert statt den
Server zu fragen (`tools/baue_demo.py`). Die Zahlen kommen aus
`takt.rechne()` mit festem Stichtag. Der Pages-Lauf baut die Datei neu und
vergleicht sie mit der eingecheckten — eine Demo, die von der Engine
abgedriftet ist, geht nicht online.

```bash
python3 -m tools.baue_demo    # schreibt docs/index.html
```

**Einmalig einzuschalten:** *Settings → Pages → Build and deployment →
Source: **GitHub Actions***. Das Token des Workflows darf die Pages-Seite
nicht selbst anlegen, nur auf eine bestehende veröffentlichen. Bis der
Schalter steht, scheitert der Lauf an `configure-pages` — absichtlich,
denn eine stille Weiterfahrt hieße, es sei veröffentlicht.

Pages kann den Taktgeber selbst nicht hosten: die Anwendung braucht Python
und eine Datenbank, Pages liefert nur Dateien. Dafür sind `Dockerfile` und
`fly.toml` da.

## Die Oberfläche

`elevage ui` startet einen Stdlib-HTTP-Server auf `127.0.0.1:8791`. Die
Seite ist **ein String in `seite.py`** — kein Bundler, keine Datei daneben,
**0 externe Requests** (ein Test hält das fest, die Abnahme misst es am
echten Netzverkehr).

![Oberfläche, Desktop](taktgeber-desktop.png)

Gestaltet nach dem Architektur-Briefing (Agrar, intern): erdige Töne statt
Agrar-Grün, 17 px Grundschrift und Touch-Ziele ab 44 px für die Bedienung
im Stehen und mit Handschuhen, Dark Mode über Tokens, Bewegung nur mit
`prefers-reduced-motion`. **Farbe trägt nie allein** — jede Ampel hat
zusätzlich ein Zeichen und ein Wort („! überfällig", „› jetzt dran").
Abhaken folgt dem Undo-Muster: sofort ausführen, Toast mit „Rückgängig",
keine Bestätigungskaskade.

**Glas mit Rückweg.** Die Flächen sind durchscheinend (`backdrop-filter`)
über einem Grund aus zwei CSS-Farbfeldern — kein Bild, keine Bytes. Optik
darf die Lesbarkeit nicht kosten: gemessen im Browser liegt **kein** Text
unter WCAG AA, hell wie dunkel. Wo der Browser kein `backdrop-filter` kann
oder jemand `prefers-reduced-transparency` gesetzt hat, werden dieselben
Flächen deckend gezeichnet.

**Jede Breite ohne Querscroll.** Über acht Viewports von 320 bis 1920 px
gemessen, Anmeldeseite wie Hauptseite. Der Fehler davor: ein `<select>`
wächst auf die Breite seiner längsten Option, wenn sein Kasten nicht
schrumpfen darf — unter 768 px lief die Seite quer. Jetzt sitzt jedes
Bedienfeld in einem `.feld` mit `min-width: 0`, lange Herdennamen werden
gekürzt, und nur die Mischtabelle scrollt, nie die Seite.

## Anmeldung

**Der Betrieb kommt aus der Sitzung, nie aus der Anfrage.** Damit ist die
Mandantentrennung eine Grenze und kein Auswahlfeld: wer angemeldet ist,
sieht genau einen Betrieb, und kein Parameter ändert das.

```bash
elevage benutzer --betrieb hof --anlegen kofi --name "Kofi A." --rolle LEITUNG
elevage benutzer --betrieb hof --sperren kofi
```

Das Passwort wird abgefragt, nicht als Argument übergeben — sonst stünde es
in der Shell-Historie.

| Rolle | darf |
|---|---|
| `LESER` | sehen |
| `STALL` | zusätzlich abhaken, Vorfälle melden, mischen und buchen |
| `LEITUNG` | zusätzlich Prüfvermerke abhaken (= am Original verglichen) |

**Abweichung vom Briefing, bewusst und benannt:** dort steht „Standard-Auth
(OIDC/OAuth2 oder bewährte Lib) statt Eigenbau". Es gibt hier keinen
Identitätsanbieter und keine Fremdbibliothek, weil der Kern dep-arm bleibt
und der Betrieb offline läuft. Gebaut ist das Kleinste, was verteidigbar
ist — und **keine eigene Krypto**:

* `hashlib.scrypt` aus der Standardbibliothek als Schlüsselableitung, mit
  den Parametern im Hash, damit sie später erhöht werden können.
* Vergleiche über `hmac.compare_digest`, nie über `==`.
* Das Sitzungsmerkmal liegt **nur als SHA-256** in der Datenbank. Wer die
  Datei kopiert, hat damit keine gültige Sitzung.
* Cookie `HttpOnly` + `SameSite=Strict`, dazu ein Origin-Abgleich bei jedem
  POST. Anmeldeversuche sind gebremst (5 in 15 Minuten, je Konto **und** je
  Herkunft), und die Antwort unterscheidet nie zwischen „Konto unbekannt"
  und „Passwort falsch".

Kommt später OIDC dazu, ist `anmeldung.pruefe_passwort` die eine Naht, die
getauscht wird — sonst nichts.

## Betrieb

`elevage ui` bindet auf `127.0.0.1`. Für eine andere Adresse braucht es
`ELEVAGE_ALLOW_REMOTE=1`, und dann gehört **TLS davor** — ohne
`ELEVAGE_SECURE_COOKIE=1` warnt der Start, weil Passwort und Sitzung sonst
im Klartext reisen.

`Dockerfile` und `fly.toml` liegen bei: ein Deployable, SQLite auf einem
Volume, scale-to-zero, Region `cdg` (näher an Westafrika als `fra`). Kein
Build-Schritt fürs Frontend — die Seite ist ein String im Paket.

```bash
fly launch --no-deploy   # einmalig, App-Namen bestätigen
fly volumes create elevage_daten --size 1
fly deploy
fly ssh console -C "python -m elevage.cli benutzer --betrieb hof --anlegen kofi --name 'Kofi A.' --rolle LEITUNG"
```

## Wartezeiten — die Zahl steht auf der Packung

Das Junghennen-Blatt verordnet in der Legeperiode monatlich Entwurmung.
Während der Behandlung und für die Wartezeit danach dürfen die Eier nicht
in den Verkauf. Es gibt hier **keine eingebaute Wartezeitentabelle** — sie
hängt an Präparat, Dosis und Zulassungsland; eine erfundene Zahl wäre
schlimmer als keine.

```bash
elevage praeparat --betrieb hof --anlegen "TETRACOLIVIT" --eier 7 --quelle Beipackzettel
elevage quittieren --betrieb hof --herde H1 --schritt PONDEUSE_J23_ANTIBIOTIKUM \
    --am 2026-03-25 --praeparat TETRACOLIVIT
```

```
WARTEZEIT — Eier gesperrt bis 05.04.2026
  TETRACOLIVIT · letzte Gabe 29.03. · 7 Tage · frei ab 05.04.
```

Drei Regeln, die nicht verhandelbar sind:

1. **Unbekannt ist nicht null.** Ein Mittel ohne hinterlegte Wartezeit
   erzeugt einen Befund, keine Freigabe.
2. **Ohne festgehaltenes Präparat gibt es keine Rechnung.** Die Programme
   nennen je Schritt mehrere Alternativen; die Oberfläche fragt beim
   Abhaken, welche gegeben wurde.
3. **Die Frist läuft ab der letzten Gabe**, nicht ab dem Abhaken — bei
   einem mehrtägigen Schritt zählt das Ende des Behandlungsfensters.

Legehennen fragen nach Eier-, Masthühner nach Fleischwartezeit. Eine
Wartezeit einzutragen ist der Leitung vorbehalten.

## Verluste — die Tierzahl ist ein Anfangswert

Ohne Abgänge rechnet die Verzehrkurve dieselbe Futtermenge auf zu viele
Tiere; der Fehler wächst mit der Zeit und fällt nie auf. 140 kg auf 1000
statt auf die real verbliebenen 800 Tiere sind 20 statt 25 g/Tier/Tag.

```bash
elevage abgang --betrieb hof --herde H1 --tiere 12 --am 2026-03-18 --grund VERENDET
```

**Verkauft ist kein Verlust** — nur `VERENDET` und `GEKEULT` gehen in die
Quote, sonst sähe jeder Verkauf aus wie ein Ausbruch. Ab 5 % seit dem
Einstallen gibt es einen Befund, und eine **Häufung** (2 % in 7 Tagen)
wird getrennt gemeldet: dieselbe Zahl über Monate ist etwas anderes.

## Offline

Die Seite läuft im Funkloch weiter. Ein Service Worker (`seite.DIENER`,
ausgeliefert unter `/sw.js`) hält **zwei** Vorräte, weil sie Verschiedenes
bedeuten: die **Seite** cache-first (sonst ist der Stall bei jedem Funkloch
weiß), die **Daten** network-first (sonst arbeitet jemand mit dem
Tagesbild von gestern, obwohl ein frisches erreichbar wäre).

Geht ein Abhaken nicht durch, wandert es in eine Warteschlange im Browser
und wird bei Netzrückkehr nachgereicht. Möglich ist das nur, weil die
Nummern serverseitig aus dem Inhalt entstehen: **zweimal geschickt wirkt
einmal.** Ein Mischauftrag steht bewusst nicht auf der Liste — der braucht
eine Antwort.

## Wenn ein Rezept nicht auf 100 kg aufgeht

Drei Wege, und die Ausgabe sagt immer, welcher gegangen wurde:

| Weg | was passiert | Ponte auf 1000 kg |
|---|---|---|
| `AUSGLEICH` (Vorgabe) | Überhang aus **einem** benannten Posten, dem Energieträger | Mais 500 → **433 kg**, Rest unberührt, 1000 kg im Mischer |
| `VERBATIM` | gerechnet wie das Blatt | 1067 kg im Mischer — nicht buchbar |
| `ANTEILIG` | alles gleichmäßig skaliert | 1000 kg, aber auch Kalk und Methionin sinken |

Warum ein Posten und nicht alle: Kalk, Aminosäuren und Konzentrat stehen für
eine **Funktion**; ihre Menge ist die Aussage des Rezepts, nicht sein Puffer.
Mais ist der Füller und trägt den Abschreibfehler. Gesperrt wird nur noch,
was kein Abschreibfehler mehr sein kann — über 15 kg je 100 kg, oder wenn
der Ausgleichsposten gar nicht reicht.

Jeder Ausgleich hinterlegt einen **Prüfvermerk** mit Vorher-Nachher-Wert und
Quelle. Er bleibt offen, bis ihn jemand mit `LEITUNG`-Rolle abhakt, und kommt
danach nicht zurück. `elevage pruefliste` endet mit Code 2, solange etwas
offen ist — damit lässt sich ein Wächter daranhängen.

## Mengen und Dosen sind anpassbar

Das Blatt bleibt im Code stehen und wird **nie** überschrieben. Was der
Betrieb ändert, liegt als Anpassung daneben; jeder Posten trägt danach seine
Herkunft und den Blattwert:

```
MAIS               43.30 kg/100kg  Betrieb Mais  (Blatt: 50.00)
SOJA_TOURFIE       14.00 kg/100kg  Blatt   Soja torréfié
SUMME             100.00 kg/100kg  (+0.00)
```

0 kg heißt: der Posten entfällt. Ebenso ist die **Desinfektionsdosis im
Gumboro-Schema** eine Einstellung — Vorgabe bleibt der Wert des eigenen
Blattes, und der Befund sagt, ob die Zahl vom Blatt oder vom Betrieb kommt.
Unbekannte Einstellungsschlüssel werden abgewiesen, nicht abgelegt.

## Zwei Sprachen

Die Quellblätter sind französisch, die Leute im Stall vermutlich auch. Die
Oberfläche lässt sich im Kopf umschalten (Deutsch / Français).

**Französisch ist die Vorgabe** (`sprache.VORGABE = "fr"`). Die Blätter sind
französisch, der Stall ist es auch — Deutsch wäre die Sprache des
Werkzeugbauers, nicht die der Arbeit. Deutsch bleibt wählbar, bleibt die
Sprache im Quelltext und bleibt der Rückfall, wenn etwas fehlt.

Fünf Entscheidungen:

* **Die Termine sprechen den Wortlaut ihres Blattes, nicht eine
  Rückübersetzung.** Die Blätter *sind* französisch; der deutsche Titel im
  Code ist die Übersetzung. Also trägt jeder Schritt sein Original
  (`Schritt.titel_fr`), gesammelt in `WORTLAUT_*` — so kann jemand mit dem
  Papier in der Hand Zeile für Zeile gegenlesen. Ein Wörterbuch hätte aus
  „2ème Vaccin GUMBORO“ eine glatte Übersetzung gemacht und den
  Widerspruch des Blattes dabei weggebügelt.
* **Befunde sprechen beide Sprachen** (`models.Befund`: `text` +
  `text_fr`). Sie erklären, warum etwas nicht stimmt — wer sie nicht lesen
  kann, kann nichts mit ihnen anfangen. Ein Wörterbuch half hier nicht: die
  meisten tragen Zahlen („46,50 → 45,40 kg“), und ein Musterabgleich auf
  zusammengesetzte Sätze wäre genau die Sorte Magie, die dieses Haus
  vermeidet. Also schreibt die erzeugende Stelle beide Fassungen. Dasselbe
  gilt für die Merksätze der Blätter (`models.Satz`) und für den
  Prüfvermerk, der gespeichert wird (Migration 9).
* **Präparatnamen und Rezeptposten bleiben, wie sie sind.** Ein Feld
  `praeparate_fr` gibt es nicht; ein Test hält das fest.
* **Fehlt eine Vokabel oder ein Wortlaut, steht der deutsche Text da** —
  kein leeres Feld, kein Schlüsselname.
* **Die Wahl lebt im Browser**, nicht in der Datenbank: die Sprache gehört
  dem Menschen vor dem Gerät, nicht dem Konto.

Zwei Tests bewachen das von beiden Seiten: `test_sprache.py` prüft, dass
kein Text im Markup ohne Vokabel ist, `test_wortlaut.py`, dass kein Termin,
kein Befund und kein Merksatz ohne französische Fassung ausgeliefert wird.
Das zweite fehlte — und genau da blieb die Ansicht halb deutsch.

## Betriebsalltag

```bash
elevage benutzer --betrieb hof --passwort kofi   # Passwort neu setzen
tools/backup-probe.sh                            # Sicherung + Rückspielprobe
curl -s localhost:8791/api/health                # für den Uptime-Wächter
```

`/api/health` braucht keine Anmeldung (ein Wächter hat keine) und verrät
keine Betriebszahl — nur `status`, `version`, `commit`. Geprüft wird die
Datenbank mit, nicht nur der Prozess. Der Versionsstempel steht auch im
Fuß der Seite: *welcher Stand lief, als es passierte?*

Ein **Passwortwechsel beendet alle offenen Sitzungen** dieses Kontos. Wer
sein Passwort ändert, tut das oft, weil er vermutet, dass es jemand kennt.

`tools/backup-probe.sh` legt eine Sicherung an, **spielt sie in eine
Wegwerf-Datei zurück** und prüft sie dort. Ein Backup, das nie
zurückgespielt wurde, ist nur eine Hoffnung.

**Zeitzone:** `date.today()` liest die Uhr des Servers. Läuft der in UTC
und der Betrieb in Europa, ist abends ab 22 Uhr schon der Folgetag.
`ELEVAGE_ZEITZONE=Europe/Berlin` stellt den Betriebstag gerade; Togo liegt
auf UTC und braucht nichts.

## Zwei Tierärzte, zwei Blätter — die Wahl gehört der Herde

Für Legehennen liegen **zwei vollständige Prophylaxe-Programme** vor, und
sie widersprechen sich an fast jedem Datum:

| | IVOGRAIN | VETO-NEGOCES |
|---|---|---|
| Gumboro | J7 · J12 · J17 | J7 · **J14** · **J21** |
| ND + IB lebend | J1 · J10 · J21 | **J5** · **J25** |
| Pocken | J29–35, Auffr. J64–70 | **J42**, ohne Auffrischung |
| Entwurmung | J57–63 · J85–91 | **J50 · J88 · J124** |
| Coryza | J71–77, Auffr. J106–112 | **J84 · J120** |
| Débecquage | J43–49 | **fehlt** |
| ND/IB-Auffrischung danach | **alle 30 Tage** | **alle 6 Monate** |

Zusammenlegen wäre eine Entscheidung — und zwar eine tierärztliche. Deshalb
steht jedes Blatt vollständig da, die Wahl hängt an der Herde
(`Herde.programm_id`, `NULL` = Vorgabe der Tierart), und
`elevage programm --vergleich` rechnet die Gegenüberstellung aus den Daten
statt sie zu behaupten. Welches gilt, entscheidet der Betrieb.

Drei Eigenheiten des VETO-Blattes haben eigene Begriffe bekommen:

- **Pause** (`Kategorie.PAUSE`): „EAU SIMPLE" heißt *ausdrücklich nichts
  geben*. Das steht im Stand und ist nichts zum Abhaken — sonst quittiert
  jemand fünfzig Tage lang einfaches Wasser. Als Termin existiert es
  trotzdem, sonst sähe niemand, dass die Lücke gewollt ist.
- **Anti-Stress** und **Leberschutz** sind eigene Kategorien, keine
  Vitamine. Das Blatt taktet sie systematisch um jeden Eingriff herum.
- **Offenes Ende** (`OFFENES_ENDE`): „J128 à la Réforme" nennt kein Datum.
  Eine Zahl statt `None`, damit die Planrechnung keine Sonderfälle bekommt.

Der **Tierarzt** hängt am Betrieb, nicht am Blatt (`elevage tierarzt`) — der
Betrieb wechselt den Arzt, nicht das Programm.

## Regeln, die nicht gebrochen werden

1. **Der Stichtag kommt herein, nie aus der Uhr.** Sonst ist kein Lauf
   reproduzierbar und kein Test aussagekräftig.
2. **Vorlage und Termin sind getrennt.** Ein geändertes Programm darf die
   Historie einer laufenden Herde nicht rückwirkend verfälschen.
3. **Abhaken ist ein Ereignis, kein überschriebenes Feld.** Damit gibt es
   beim Offline-Sync keinen Konflikt, nur zwei Einträge und eine sichtbare
   Frage — und mehrfach gesendete Quittungen sind harmlos.
4. **Widersprüche der Blätter werden gemeldet, nicht geglättet.** Die
   Rezepte summieren sich nicht auf 100 kg; der Mischauftrag rechnet
   verbatim und sagt, was tatsächlich in den Mischer geht. Normiert wird
   nur auf ausdrückliche Anweisung.
5. **Lücken werden benannt, nicht als Null verbucht.** Für Masthühner gibt
   es kein Futterblatt; ohne Verzehrkurve gibt es keine Reichweite.
6. **Tenant-ID in jedem Datensatz**, Trennung schon im Kern — nicht erst in
   der Query. `test_jede_fachtabelle_hat_eine_tenant_id` bewacht das als
   Fitness-Function: eine neue Tabelle ohne Mandanten fällt sofort auf.
7. **Ausstallen löscht nicht**, es setzt inaktiv — die Historie bleibt.
8. **Ein gesperrter Mischauftrag wird nicht protokolliert.** Was nicht
   freigegeben ist, wurde nicht gemischt.
9. **Tuning steht als Konstante am Modulanfang**, keine Magic Numbers.
10. **Migrationen sind nummeriert** und laufen vorwärts gegen eine
    Versionstabelle — kein ad-hoc `ALTER` im Code.
11. **Das Blatt wird nie überschrieben.** Betriebswerte liegen daneben, und
    jeder Posten trägt seine Herkunft.
12. **Kein Ausgleich ohne Prüfvermerk.** Eine geglättete Zahl, die niemand
    mehr nachsieht, ist schlimmer als eine, die anhält.
13. **Zwei Blätter werden nie zu einem.** Widersprechen sich zwei
    Prophylaxe-Programme, stehen beide vollständig da und die Herde wählt.
    Eine gerechnete Mischform wäre eine tierärztliche Entscheidung durch
    Software.
14. **Ein Programmwechsel fasst die Historie nicht an.** Abgehakt bleibt
    abgehakt; was das neue Blatt nicht kennt, verschwindet aus der Liste.
    Und wechseln darf nur die Leitung — es verschiebt Impftermine.

## Befunde aus den Quellblättern

| Befund | Wo |
|---|---|
| Rezept *Ponte* summiert auf **106,7 kg** je 100 kg (+6,7) | `rezepte.py` |
| *Démarrage* und *Poulette* summieren auf 101,1 kg (+1,1) | `rezepte.py` |
| Binder steht als **ALFABIND** und **AFABIND** — ein Artikel | `ARTIKEL_ALIAS` |
| J12 und J17 heißen beide „2ème Vaccin GUMBORO" | `programme.py` |
| ND-Auffrischung Tag 57–60 steht in der Woche-7-Zeile **und** als Woche 9 | `programme.py` |
| Woche-6-Zeile ist auf Tag 35–40 datiert, Woche 6 ist Tag 36–42 | `programme.py` |
| Futterphasen überlappen an den Rändern (0–8/8–21, 8–21/ab 21) | `rezepte.py` |
| Für Masthühner liegt **kein** Futterblatt vor | `rezepte.py` |
| Notfall-Dosis: 0,5 g/l (Masthuhn) vs. 1 g/l (Junghenne) — zwei Zahlen für dasselbe Mittel | `notfall.py` |
| VETO-Blatt J17–J19: Überschrift „ANTI-STRESS", Präparat ein Antikokzidium | `programme.py` |
| VETO-Blatt J120 schreibt „CORYMINE", J84 „CORYMUNE" | `programme.py` |
| VETO-Blatt J125–J127 nennt Anti-Stress **und** „EAU SIMPLE" in einer Zeile | `programme.py` |
| VETO-Blatt endet „à la Réforme" — kein Datum | `programme.py` |

Quellen der Prophylaxe-Blätter: **IVOGRAIN** und **VETO-NEGOCES / TCHA AGGRO
CENTER (Dr. BANGUE)**. Quelle der Rezepturen: handschriftliche Betriebsblätter.

## Nach jeder Änderung

```bash
python3 -m ruff format . && python3 -m ruff check . && python3 -m mypy && python3 -m pytest -q
```

Dieselben vier laufen in CI auf jeden Push und Pull Request, gegen Python
3.10 und 3.12 (`.github/workflows/tests.yml`). Ein zweiter Job baut das
Docker-Bild und prüft, ob `/api/health` darin antwortet — ein Dockerfile,
das nie gebaut wurde, ist eine Behauptung.
