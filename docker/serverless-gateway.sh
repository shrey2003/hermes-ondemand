#!/bin/sh
# Serverless entry command for OnDemand and similar HTTP platforms.
#
# Those platforms route traffic only to the port in $PORT (usually 3000),
# while Hermes' API server otherwise defaults to 8642.  Keep an explicitly
# supplied API_SERVER_PORT authoritative for non-serverless deployments.
set -eu

: "${API_SERVER_ENABLED:=true}"
: "${API_SERVER_HOST:=0.0.0.0}"
: "${API_SERVER_PORT:=${PORT:-3000}}"

if [ -z "${API_SERVER_KEY:-}" ]; then
    echo "[hermes] API_SERVER_KEY is required for the public API server" >&2
    exit 64
fi

export API_SERVER_ENABLED API_SERVER_HOST API_SERVER_PORT

# OnDemand injects deployment settings as environment variables.  Keep the
# model selection alongside the OpenRouter credential so a fresh, ephemeral
# Serverless instance does not depend on an interactive `hermes model` setup.
if [ -n "${OPENROUTER_MODEL:-}" ]; then
    hermes config set model.provider openrouter >/dev/null
    hermes config set model.default "$OPENROUTER_MODEL" >/dev/null
fi

# Enable the bundled Internet Agent web provider for API-server runs.  This
# exposes Hermes's existing web_search tool (rather than adding a bespoke core
# tool) and routes searches to the service described by
# hermes_cli/internet_plugin_schema.yaml.
hermes config set web.backend internet-agent >/dev/null

exec hermes gateway run
