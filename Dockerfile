FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY core/ core/
COPY server/ server/
COPY widget/ widget/

RUN pip install --no-cache-dir .

# Presets live in a single SQLite file — mount /data to persist them.
ENV PRESETS_DB=/data/presets.db
VOLUME ["/data"]

ENV PORT=8080
EXPOSE 8080

CMD ["python", "-m", "server.app"]
