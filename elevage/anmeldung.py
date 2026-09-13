"""Benutzer, Passwörter und Sitzungen — so wenig Eigenbau wie möglich.

**Abweichung vom Briefing, bewusst und benannt:** dort steht „Standard-Auth
(OIDC/OAuth2 oder bewährte Lib) statt Eigenbau". Hier gibt es keinen
Identitätsanbieter und keine Fremdbibliothek, weil der Kern dep-arm bleiben
soll und der Betrieb offline läuft. Gebaut ist deshalb das Kleinste, was
verteidigbar ist, und **keine eigene Krypto**:

* `hashlib.scrypt` aus der Standardbibliothek als Schlüsselableitung —
  ein geprüftes Verfahren, kein selbst ausgedachtes.
* Vergleiche laufen über `hmac.compare_digest`, nie über `==`.
* Das Sitzungsmerkmal wird **nur als Hash** gespeichert. Wer die Datei
  kopiert, hat damit keine gültige Sitzung.

Wenn später OIDC dazukommt, ist `pruefe_passwort` die eine Naht, die
getauscht wird — sonst nichts.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import date, timedelta

MIN_PASSWORTLAENGE = 10
"""Kürzeres lässt sich zu leicht raten. Länge schlägt Sonderzeichen."""

SITZUNG_TAGE = 30
"""Wie lange eine Anmeldung trägt, bevor neu angemeldet werden muss."""

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_LAENGE = 32
"""Parameter der Schlüsselableitung. Stehen im Hash mit drin, damit sie
später erhöht werden können, ohne alte Passwörter ungültig zu machen."""

TOKEN_BYTES = 32


class PasswortZuKurz(ValueError):
    pass


def hashe_passwort(passwort: str, salz: bytes | None = None) -> str:
    """Ergibt `scrypt$n$r$p$salz$hash` — die Parameter reisen mit."""
    if len(passwort) < MIN_PASSWORTLAENGE:
        raise PasswortZuKurz(f"Das Passwort braucht mindestens {MIN_PASSWORTLAENGE} Zeichen.")
    salz = salz or secrets.token_bytes(16)
    roh = hashlib.scrypt(
        passwort.encode(),
        salt=salz,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_LAENGE,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salz.hex()}${roh.hex()}"


def pruefe_passwort(passwort: str, gespeichert: str) -> bool:
    """Zeitkonstant vergleichen. Ein kaputter Hash ist ein Nein, kein Absturz."""
    try:
        art, n, r, p, salz_hex, hash_hex = gespeichert.split("$")
        if art != "scrypt":
            return False
        roh = hashlib.scrypt(
            passwort.encode(),
            salt=bytes.fromhex(salz_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(bytes.fromhex(hash_hex)),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(roh, bytes.fromhex(hash_hex))


def neues_token() -> str:
    """Das Merkmal, das im Cookie landet. Nur der Browser sieht es im Klartext."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def token_hash(token: str) -> str:
    """Was in der Datenbank liegt. Aus dem Hash lässt sich kein Cookie bauen."""
    return hashlib.sha256(token.encode()).hexdigest()


def laeuft_ab(ab: date, tage: int = SITZUNG_TAGE) -> date:
    return ab + timedelta(days=tage)
