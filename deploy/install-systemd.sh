#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")"
    pwd
)"

ROOT_DIR="${HSM_ROOT:-$(
    cd "$SCRIPT_DIR/.."
    pwd
)}"

SERVICE_USER="${HSM_USER:-${SUDO_USER:-$USER}}"

TEMPLATE_DIR="$ROOT_DIR/deploy/systemd"

if [[ "$ROOT_DIR" =~ [[:space:]] ]]; then
    echo "ERROR: repository path cannot contain spaces."
    exit 1
fi

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    echo "ERROR: user '$SERVICE_USER' does not exist."
    exit 1
fi

if ! id -nG "$SERVICE_USER" \
    | tr ' ' '\n' \
    | grep -qx "lxd"
then
    echo "ERROR: user '$SERVICE_USER' is not in the lxd group."
    exit 1
fi

if [[ ! -x "$ROOT_DIR/backend/.venv/bin/python" ]]; then
    echo "ERROR: backend virtual environment is missing."
    exit 1
fi

if [[ ! -f "$ROOT_DIR/.env" ]]; then
    echo "ERROR: $ROOT_DIR/.env is missing."
    exit 1
fi

if [[ ! -f "$ROOT_DIR/dashboard/package.json" ]]; then
    echo "ERROR: dashboard/package.json is missing."
    exit 1
fi

NODE_BIN="${HSM_NODE:-$(command -v node || true)}"
NPM_BIN="${HSM_NPM:-$(command -v npm || true)}"

if [[ -z "$NODE_BIN" || ! -x "$NODE_BIN" ]]; then
    echo "ERROR: Node.js executable was not found."
    echo "Load nvm first or set HSM_NODE explicitly."
    exit 1
fi

if [[ -z "$NPM_BIN" || ! -x "$NPM_BIN" ]]; then
    echo "ERROR: npm executable was not found."
    echo "Load nvm first or set HSM_NPM explicitly."
    exit 1
fi

if ! "$NODE_BIN" -e '
const [major, minor] =
  process.versions.node
    .split(".")
    .map(Number);

process.exit(
  major > 22 ||
  (major === 22 && minor >= 12)
    ? 0
    : 1
);
'
then
    echo "ERROR: Node.js >= 22.12.0 is required."
    echo "Detected: $("$NODE_BIN" --version)"
    exit 1
fi

TMP_DIR="$(mktemp -d)"

cleanup() {
    rm -rf "$TMP_DIR"
}

trap cleanup EXIT

render_service() {
    local source_file="$1"
    local output_file="$2"

    sed \
        -e "s|__HSM_USER__|$SERVICE_USER|g" \
        -e "s|__HSM_ROOT__|$ROOT_DIR|g" \
        -e "s|__HSM_NODE__|$NODE_BIN|g" \
        "$source_file" \
        > "$output_file"
}

echo "Building production dashboard..."

if [[ "$(id -un)" == "$SERVICE_USER" ]]; then
    (
        cd "$ROOT_DIR/dashboard"
        "$NPM_BIN" run build
    )
else
    sudo -u "$SERVICE_USER" \
        env PATH="$(dirname "$NODE_BIN"):/usr/bin:/bin" \
        "$NPM_BIN" \
        --prefix "$ROOT_DIR/dashboard" \
        run build
fi

if [[ ! -f "$ROOT_DIR/dashboard/dist/server/entry.mjs" ]]; then
    echo "ERROR: Astro production server was not generated."
    exit 1
fi

render_service \
    "$TEMPLATE_DIR/hobby-server-monitor-api.service" \
    "$TMP_DIR/hobby-server-monitor-api.service"

render_service \
    "$TEMPLATE_DIR/hobby-server-monitor-collector.service" \
    "$TMP_DIR/hobby-server-monitor-collector.service"

render_service \
    "$TEMPLATE_DIR/hobby-server-monitor-dashboard.service" \
    "$TMP_DIR/hobby-server-monitor-dashboard.service"

sudo install \
    -m 0644 \
    "$TMP_DIR/hobby-server-monitor-api.service" \
    /etc/systemd/system/hobby-server-monitor-api.service

sudo install \
    -m 0644 \
    "$TMP_DIR/hobby-server-monitor-collector.service" \
    /etc/systemd/system/hobby-server-monitor-collector.service

sudo install \
    -m 0644 \
    "$TMP_DIR/hobby-server-monitor-dashboard.service" \
    /etc/systemd/system/hobby-server-monitor-dashboard.service

sudo systemctl daemon-reload

sudo systemctl enable \
    hobby-server-monitor-api.service \
    hobby-server-monitor-collector.service \
    hobby-server-monitor-dashboard.service

echo
echo "Systemd services installed."
echo
echo "Node:"
echo "  $NODE_BIN"
echo
echo "Restart services with:"
echo "  sudo systemctl restart hobby-server-monitor-api.service"
echo "  sudo systemctl restart hobby-server-monitor-collector.service"
echo "  sudo systemctl restart hobby-server-monitor-dashboard.service"
