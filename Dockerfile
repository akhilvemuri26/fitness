FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY app ./app
COPY alembic ./alembic
COPY scripts ./scripts

RUN pip install --upgrade pip && \
    pip install .

RUN chmod +x /app/scripts/start_server.sh

ENV PORT=8000

EXPOSE 8000

CMD ["/app/scripts/start_server.sh"]
