#!/bin/sh
# Ein Backup, das nie zurückgespielt wurde, ist nur eine Hoffnung.
#
# Legt eine Sicherung an, spielt sie in eine WEGWERF-Datei zurück und prüft
# sie dort: Integrität, Schemastand, und ob die Fachtabellen Zeilen haben.
# Die laufende Datenbank wird dabei nie angefasst.
#
#   tools/backup-probe.sh [quelle.db] [zielordner]
set -eu

QUELLE="${1:-${ELEVAGE_DB:-$HOME/.elevage/elevage.db}}"
ZIEL="${2:-$(dirname "$QUELLE")/sicherung}"
STEMPEL="$(date +%Y-%m-%d-%H%M)"
SICHERUNG="$ZIEL/elevage-$STEMPEL.db"

[ -f "$QUELLE" ] || { echo "Keine Datenbank unter $QUELLE"; exit 1; }
mkdir -p "$ZIEL"

# .backup statt cp: kopiert konsistent, auch wenn gerade geschrieben wird.
sqlite3 "$QUELLE" ".backup '$SICHERUNG'"
echo "Sicherung: $SICHERUNG ($(wc -c < "$SICHERUNG") Bytes)"

PROBE="$(mktemp -d)/rueckspielprobe.db"
sqlite3 "$SICHERUNG" ".backup '$PROBE'"

ERGEBNIS="$(sqlite3 "$PROBE" 'PRAGMA integrity_check;')"
[ "$ERGEBNIS" = "ok" ] || { echo "Integritätsprüfung: $ERGEBNIS"; exit 2; }

STAND="$(sqlite3 "$PROBE" 'SELECT MAX(version) FROM schema_version;')"
[ -n "$STAND" ] || { echo "Kein Schemastand in der Sicherung"; exit 3; }

HERDEN="$(sqlite3 "$PROBE" 'SELECT COUNT(*) FROM herde;')"
BENUTZER="$(sqlite3 "$PROBE" 'SELECT COUNT(*) FROM benutzer;')"

echo "Rückspielprobe bestanden: Schema $STAND, $HERDEN Herde(n), $BENUTZER Benutzer"
rm -rf "$(dirname "$PROBE")"

# Alte Sicherungen aufräumen: die letzten 14 bleiben.
ls -1t "$ZIEL"/elevage-*.db 2>/dev/null | tail -n +15 | while read -r alt; do
  rm -f "$alt"
  echo "verworfen: $alt"
done
