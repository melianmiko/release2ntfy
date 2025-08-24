FROM python:3.13.4-slim AS python-base

# Latest releases available at https://github.com/aptible/supercronic/releases
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.34/supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=e8631edc1775000d119b70fd40339a7238eece14 \
    SUPERCRONIC=supercronic-linux-amd64

ENV PYTHONUNBUFFERED=1 \
    PDM_CHECK_UPDATE=false

WORKDIR /app

RUN apt update && apt install -y curl python-is-python3

RUN curl -fsSLO "$SUPERCRONIC_URL" \
 && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
 && chmod +x "$SUPERCRONIC" \
 && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
 && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

FROM python-base AS builder-base

RUN pip install -U pdm

COPY pyproject.toml pdm.lock ./
RUN --mount=type=cache,target=/root/.cache/pdm \
    pdm install --without dev


FROM python-base

ENV PYTHONPATH=/app

COPY --from=builder-base /app/.venv /app/.venv/
COPY . /app/

WORKDIR /app

CMD ["/app/docker-entrypoint.sh"]
