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

SERVICE_USER="${
    HSM_USER:-${SUDO_USER:-$USER}
}"

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
        "$source_file" \
        > "$output_file"
}


render_service \
    "$TEMPLATE_DIR/hobby-server-monitor-api.service" \
    "$TMP_DIR/hobby-server-monitor-api.service"

render_service \
    "$TEMPLATE_DIR/hobby-server-monitor-collector.service" \
    "$TMP_DIR/hobby-server-monitor-collector.service"


sudo install \
    -m 0644 \
    "$TMP_DIR/hobby-server-monitor-api.service" \
    /etc/systemd/system/hobby-server-monitor-api.service

sudo install \
    -m 0644 \
    "$TMP_DIR/hobby-server-monitor-collector.service" \
    /etc/systemd/system/hobby-server-monitor-collector.service

sudo systemctl daemon-reload

sudo systemctl enable \
    hobby-server-monitor-api.service \
    hobby-server-monitor-collector.service

echo
echo "Systemd services installed."
echo
echo "Start or restart them with:"
echo "  sudo systemctl restart hobby-server-monitor-api.service"
echo "  sudo systemctl restart hobby-server-monitor-collector.service"
