# Ein Deployable: Server und Oberfläche in einem Bild.
# Kein Build-Schritt für das Frontend — die Seite ist ein String im Paket.
FROM python:3.12-slim

# Nicht als root laufen. Der Volume-Punkt gehört dem Dienstbenutzer.
RUN useradd --create-home --uid 10001 elevage \
 && mkdir -p /data && chown elevage:elevage /data

WORKDIR /app
COPY pyproject.toml README.md ./
COPY elevage ./elevage
RUN pip install --no-cache-dir .

USER elevage
ENV ELEVAGE_DB=/data/elevage.db \
    ELEVAGE_ALLOW_REMOTE=1 \
    ELEVAGE_SECURE_COOKIE=1 \
    PYTHONUNBUFFERED=1
EXPOSE 8080

# --host 0.0.0.0 ist hier richtig: der Proxy davor terminiert TLS, und das
# Secure-Cookie oben sorgt dafür, dass die Sitzung nur über TLS reist.
CMD ["python", "-m", "elevage.cli", "ui", "--host", "0.0.0.0", "--port", "8080"]
