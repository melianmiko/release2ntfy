#!/usr/bin/env bash

mkdir -p /app/data

if [ ! -f /app/data/config.yaml ]
then
  cp /app/config_example.yaml /app/data/config.yaml
fi

if [ ! -f /app/data/state.yaml ]
then
  touch /app/data/state.yaml
fi

/app/.venv/bin/python -m release2ntfy -c
exec /usr/local/bin/supercronic -passthrough-logs /app/crontab
