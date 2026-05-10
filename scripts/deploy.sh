#!/usr/bin/env bash
# scripts/deploy.sh
#
# Idempotent on-droplet deploy script. Invoked over SSH by the GitHub
# Actions deploy workflow after the new images have been pushed to GHCR.
#
# Inputs (read from the environment):
#   APP_ENV    Full content of the production-ish dev ``.env`` file.
#              Provided verbatim by the workflow from the repo variable
#              of the same name. The script writes it to
#              /srv/sitdown-rest/config/.env on each invocation.
#   IMAGE_TAG  Optional override for the image tag pulled from GHCR.
#              Defaults to ``latest``. Set to ``sha-<short>`` to roll
#              back without re-running the workflow.
#
# Side effects:
#   - Writes /srv/sitdown-rest/config/.env (overwrites previous content).
#   - Pulls the latest images from GHCR.
#   - Reconciles services via ``docker compose up -d --remove-orphans``.
#   - Prunes images older than 72h to keep the droplet's disk in check.

set -euo pipefail

LOG_PREFIX="[deploy]"
log() { printf '%s %s\n' "$LOG_PREFIX" "$*"; }

DEPLOY_DIR="/srv/sitdown-rest"
COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.deploy.yml"

log "starting deploy on $(hostname) at $(date -u --iso-8601=seconds)"

if [[ -z "${APP_ENV:-}" ]]; then
  log "ERROR: APP_ENV is empty. Configure the GH Actions repo variable."
  exit 1
fi

if [[ ! -d "${DEPLOY_DIR}" ]]; then
  log "ERROR: ${DEPLOY_DIR} does not exist. Run scripts/bootstrap-droplet.sh first."
  exit 1
fi

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  log "ERROR: ${COMPOSE_FILE} missing. The workflow must SCP it before invoking this script."
  exit 1
fi

cd "${DEPLOY_DIR}"

mkdir -p config
log "writing config/.env from APP_ENV (${#APP_ENV} bytes)"
# ``printf`` (not echo) preserves the literal value without interpreting
# backslash escapes; ``%s`` ensures we don't double-format.
printf '%s' "${APP_ENV}" > config/.env
chmod 600 config/.env

# Make the Caddyfile available at the bind-mount path the compose file
# expects (./docker/caddy/Caddyfile relative to DEPLOY_DIR). The
# workflow SCPs this directory alongside docker-compose.deploy.yml.
if [[ ! -f docker/caddy/Caddyfile ]]; then
  log "ERROR: docker/caddy/Caddyfile not present. The workflow should SCP the docker/caddy directory."
  exit 1
fi

log "pulling images (IMAGE_TAG=${IMAGE_TAG:-latest})"
IMAGE_TAG="${IMAGE_TAG:-latest}" docker compose -f "${COMPOSE_FILE}" pull

log "reconciling services"
IMAGE_TAG="${IMAGE_TAG:-latest}" docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans

log "current state:"
IMAGE_TAG="${IMAGE_TAG:-latest}" docker compose -f "${COMPOSE_FILE}" ps

log "pruning dangling images older than 72h"
docker image prune -af --filter "until=72h" >/dev/null

log "deploy finished at $(date -u --iso-8601=seconds)"
