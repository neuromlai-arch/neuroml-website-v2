#!/usr/bin/env bash
# One-time server setup for an Ubuntu 24.04 EC2 instance that will run the
# neuroml.ai site. Safe to run alongside an existing, currently-serving old
# site on the same box: everything here is additive (installs, a new user, a
# new directory tree, a *staged but not enabled* nginx site) — nothing here
# stops nginx, touches /etc/nginx/sites-enabled, or removes/upgrades packages
# the old site might depend on. The actual cutover (enabling the new nginx
# site so it starts answering neuroml.ai/www.neuroml.ai) is a separate,
# deliberate step — see DEPLOY.md's cutover checklist. Don't do it here.
#
# Usage (as root, or via sudo):
#   sudo ./deploy/setup.sh
#
# Idempotent — re-running after a partial or repeat run is safe; each step
# checks whether it already did its job before doing it again.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run this as root: sudo $0" >&2
  exit 1
fi

PROJECT_DIR="/opt/neuroml"
DEPLOY_USER="deploy"
REPO_URL="${REPO_URL:-}"  # optional: set REPO_URL=git@github.com:org/repo.git to auto-clone

log() { echo -e "\n\033[1;32m==> $*\033[0m"; }

# ---------------------------------------------------------------- packages
log "apt-get update (no blanket upgrade — the old site is still running on this box)"
apt-get update -qq

log "Installing base prerequisites"
apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg git ufw

# ------------------------------------------------------------------ Docker
if ! command -v docker >/dev/null 2>&1; then
  log "Installing Docker Engine + Compose plugin (official apt repo, not a piped install script)"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  # shellcheck disable=SC1091
  . /etc/os-release
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y --no-install-recommends \
    docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
else
  log "Docker already installed ($(docker --version)) — skipping"
fi

# ------------------------------------------------------------ Nginx/Certbot
if ! command -v nginx >/dev/null 2>&1; then
  log "Installing Nginx"
  apt-get install -y --no-install-recommends nginx
else
  log "Nginx already installed — leaving its running config untouched (old site is live on it)"
fi

if ! command -v certbot >/dev/null 2>&1; then
  log "Installing Certbot (nginx plugin)"
  apt-get install -y --no-install-recommends certbot python3-certbot-nginx
else
  log "Certbot already installed — skipping"
fi

# --------------------------------------------------------------- deploy user
if ! id -u "$DEPLOY_USER" >/dev/null 2>&1; then
  log "Creating $DEPLOY_USER user"
  useradd --create-home --shell /bin/bash "$DEPLOY_USER"
else
  log "$DEPLOY_USER user already exists — skipping"
fi

log "Adding $DEPLOY_USER to the docker group (docker commands without sudo)"
usermod -aG docker "$DEPLOY_USER"

install -d -m 700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
if [[ ! -f "/home/$DEPLOY_USER/.ssh/authorized_keys" ]]; then
  install -m 600 -o "$DEPLOY_USER" -g "$DEPLOY_USER" /dev/null "/home/$DEPLOY_USER/.ssh/authorized_keys"
  echo "    Created an empty /home/$DEPLOY_USER/.ssh/authorized_keys."
  echo "    Add the deploy public key (e.g. the CI SSH key) to it manually before"
  echo "    relying on it — nothing is added automatically."
fi

# ------------------------------------------------------------- project tree
log "Setting up $PROJECT_DIR"
install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$PROJECT_DIR"
install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$PROJECT_DIR/staticfiles"

if [[ -n "$REPO_URL" && ! -d "$PROJECT_DIR/app/.git" ]]; then
  log "Cloning $REPO_URL into $PROJECT_DIR/app"
  sudo -u "$DEPLOY_USER" git clone "$REPO_URL" "$PROJECT_DIR/app"
elif [[ ! -d "$PROJECT_DIR/app" ]]; then
  log "No REPO_URL given and $PROJECT_DIR/app doesn't exist yet"
  echo "    Clone it yourself as $DEPLOY_USER, e.g.:"
  echo "      sudo -u $DEPLOY_USER git clone <repo-url> $PROJECT_DIR/app"
  install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$PROJECT_DIR/app"
else
  log "$PROJECT_DIR/app already exists — leaving it alone (deploy.sh will git pull)"
fi

# ----------------------------------------------------- env file structure
# Two separate env files, deliberately not one:
#   .env.prod        — read by the Django app itself (web + worker containers),
#                       see .env.prod.example in the repo for the full list.
#   deploy/.env       — read only by `docker compose` itself, to interpolate
#                       ${POSTGRES_*} into deploy/docker-compose.prod.yml's db
#                       service. Compose auto-loads a file literally named
#                       .env next to the compose file; it never reaches the
#                       app containers unless also listed in an env_file:.
# Values in both are filled in manually — never generated or guessed here.
if [[ ! -f "$PROJECT_DIR/.env.prod" ]]; then
  log "Creating $PROJECT_DIR/.env.prod (empty template — fill in manually)"
  if [[ -f "$PROJECT_DIR/app/.env.prod.example" ]]; then
    install -m 600 -o "$DEPLOY_USER" -g "$DEPLOY_USER" \
      "$PROJECT_DIR/app/.env.prod.example" "$PROJECT_DIR/.env.prod"
  else
    install -m 600 -o "$DEPLOY_USER" -g "$DEPLOY_USER" /dev/null "$PROJECT_DIR/.env.prod"
    echo "    app repo not cloned yet, so this is empty — copy .env.prod.example"
    echo "    from the repo into $PROJECT_DIR/.env.prod once it is, then fill it in."
  fi
else
  log "$PROJECT_DIR/.env.prod already exists — leaving it as-is"
fi

if [[ ! -f "$PROJECT_DIR/app/deploy/.env" ]]; then
  log "Staging $PROJECT_DIR/app/deploy/.env (Postgres credentials for docker compose)"
  install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$PROJECT_DIR/app/deploy" 2>/dev/null || true
  if [[ -d "$PROJECT_DIR/app/deploy" ]]; then
    cat > "$PROJECT_DIR/app/deploy/.env" <<'EOF'
# Read only by `docker compose`, to fill in ${POSTGRES_*} below in
# docker-compose.prod.yml's db service. Pick a real password and make sure
# .env.prod's DATABASE_URL matches exactly:
#   postgres://<POSTGRES_USER>:<POSTGRES_PASSWORD>@db:5432/<POSTGRES_DB>
POSTGRES_DB=neuroml
POSTGRES_USER=neuroml
POSTGRES_PASSWORD=
EOF
    chown "$DEPLOY_USER:$DEPLOY_USER" "$PROJECT_DIR/app/deploy/.env"
    chmod 600 "$PROJECT_DIR/app/deploy/.env"
  fi
else
  log "$PROJECT_DIR/app/deploy/.env already exists — leaving it as-is"
fi

# --------------------------------------------------------------- new nginx
# Staged, not enabled — this only copies neuroml.conf into sites-available
# so it exists ready to go. It is deliberately NOT symlinked into
# sites-enabled and nginx is NOT reloaded here: doing that would start
# routing neuroml.ai traffic at a site that hasn't been verified yet, and
# is a decision DEPLOY.md's cutover checklist calls out as a separate,
# manual step for exactly that reason.
if [[ -f "$PROJECT_DIR/app/deploy/nginx.conf" ]]; then
  log "Staging nginx config at /etc/nginx/sites-available/neuroml.conf (NOT enabled yet)"
  cp "$PROJECT_DIR/app/deploy/nginx.conf" /etc/nginx/sites-available/neuroml.conf
  nginx -t
  echo "    Staged. Enable it only after verifying the new site on :8000 — see"
  echo "    DEPLOY.md's cutover checklist for the exact ln -s + certbot + reload steps."
else
  log "deploy/nginx.conf not found yet (app repo not cloned) — re-run setup.sh after cloning to stage it"
fi

# ---------------------------------------------------------------- firewall
log "Firewall: ensure OpenSSH, HTTP and HTTPS are allowed (ufw, only if already active)"
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  ufw allow OpenSSH
  ufw allow "Nginx Full"
else
  echo "    ufw is not active — not touching firewall state on an already-live box."
  echo "    If you use security groups instead (typical on EC2), confirm 80/443/22"
  echo "    are open there; nothing to do here."
fi

log "Done."
cat <<EOF

Next steps (all manual, on purpose):
  1. Add the deploy/CI public key to /home/$DEPLOY_USER/.ssh/authorized_keys
  2. Clone the app repo to $PROJECT_DIR/app if it isn't there yet
  3. Fill in $PROJECT_DIR/.env.prod with real values (see .env.prod.example)
  4. Fill in $PROJECT_DIR/app/deploy/.env with a real POSTGRES_PASSWORD, and
     make sure .env.prod's DATABASE_URL matches it
  5. Run deploy/deploy.sh as $DEPLOY_USER to bring the site up on :8000
  6. Verify it (see DEPLOY.md), THEN enable+reload nginx and run certbot —
     never before verification.
EOF
