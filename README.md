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
    --tierart LEGEHENNE --einstall 2026-03-02 --tiere 1200
python3 -m elevage.cli herden --betrieb hof
python3 -m elevage.cli tagesbild --betrieb hof --herde H1 --stichtag 2026-03-06 --mischen 500 --vorrat 400
python3 -m elevage.cli quittieren --betrieb hof --herde H1 \
    --schritt PONDEUSE_J7_GUMBORO_1 --am 2026-03-08 --durch Kofi --lot LOT-4711
python3 -m elevage.cli gemischt --betrieb hof --herde H1 --kg 500 --am 2026-03-09
python3 -m elevage.cli verzehr --betrieb hof --herde H1
python3 -m elevage.cli vorfall --betrieb hof --herde H1 --art GUMBORO --am 2026-03-24
python3 -m elevage.cli ausstallen --betrieb hof --herde H1   # Historie bleibt

python3 -m elevage.cli mischung --rezept PONTE_AB_21 --kg 1000 [--normieren]
```

Die Datenbank liegt unter `~/.elevage/elevage.db`; `--db` oder die
Umgebungsvariable `ELEVAGE_DB` legen sie woandershin.

`tagesbild` beendet sich mit Code 2, wenn etwas überfällig ist — damit kann
ein Wächter-Job daran hängen, ohne die Ausgabe zu lesen.

## Aufbau

| Modul | Aufgabe |
|---|---|
| `models.py` | Der Vertrag (Pydantic, JSON bleibt camelCase) — Änderungen hier zuerst |
| `programme.py` | Die beiden Prophylaxe-Programme als Daten, verbatim von den Blättern |
| `rezepte.py` | Die drei Futter-Rezepturen + Artikelstamm |
| `plan.py` | Vorlage + Herde = Termine mit echten Daten, Ampel, Quittungen |
| `mischung.py` | Rezept × Chargengröße, mit Summenprobe und Sperre |
| `takt.py` | `rechne(herde, stichtag)` — das ganze Tagesbild |
| `notfall.py` | Gumboro-Schema und Leberschutz beim Futterwechsel (NB-Kasten) |
| `verzehr.py` | Verzehrkurve: gemessen aus dem Mischprotokoll, sonst Richtwert |
| `archiv.py` | SQLite (Stdlib): Herden, Quittungen, Mischprotokoll, Vorfälle |
| `betrieb.py` | Die Naht: Archiv rein, Tagesbild raus |
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

## Befunde aus den Quellblättern

| Befund | Wo |
|---|---|
| Rezept *Ponte* summiert auf **106,7 kg** je 100 kg (+6,7) | `rezepte.py` |
| *Démarrage* und *Poulette* summieren auf 101,1 kg (+1,1) | `rezepte.py` |
| Binder steht als **ALFABIND** und **AFABIND** — ein Artikel | `ARTIKEL_ALIAS` |
| „Soja tourfié": *torréfié* oder *tourteau*? Lesung offen | `ARTIKELSTAMM` |
| „Lecenan": Zusatz für die Eientwicklung, Schreibweise offen | `ARTIKELSTAMM` |
| J12 und J17 heißen beide „2ème Vaccin GUMBORO" | `programme.py` |
| ND-Auffrischung Tag 57–60 steht in der Woche-7-Zeile **und** als Woche 9 | `programme.py` |
| Woche-6-Zeile ist auf Tag 35–40 datiert, Woche 6 ist Tag 36–42 | `programme.py` |
| Futterphasen überlappen an den Rändern (0–8/8–21, 8–21/ab 21) | `rezepte.py` |
| Für Masthühner liegt **kein** Futterblatt vor | `rezepte.py` |
| Notfall-Dosis: 0,5 g/l (Masthuhn) vs. 1 g/l (Junghenne) — zwei Zahlen für dasselbe Mittel | `notfall.py` |

Quelle der Prophylaxe-Programme: IVOGRAIN. Quelle der Rezepturen:
handschriftliche Betriebsblätter.

## Nach jeder Änderung

```bash
python3 -m ruff format . && python3 -m ruff check . && python3 -m mypy && python3 -m pytest -q
```
