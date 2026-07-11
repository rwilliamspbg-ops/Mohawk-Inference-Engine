#!/usr/bin/env bash
set -euo pipefail

echo "[devcontainer] Running post-create setup"

run_as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "[WARN] Need root privileges for: $*"
    return 1
  fi
}

install_system_deps() {
  if command -v apt-get >/dev/null 2>&1; then
    run_as_root apt-get update
    run_as_root apt-get install -y \
      build-essential cmake git python3-dev python3-pip python3-venv pkg-config \
      libgl1 libegl1 libxkbcommon-x11-0 libdbus-1-3 lsof net-tools
  elif command -v apk >/dev/null 2>&1; then
    run_as_root apk add --no-cache \
      build-base cmake git python3 python3-dev py3-pip py3-virtualenv pkgconfig \
      mesa-gl libxkbcommon dbus-libs lsof net-tools
  else
    echo "[WARN] Unsupported package manager; skipping system package install"
  fi
}

ensure_liboqs() {
  if [ "${MOHAWK_SKIP_LIBOQS_BUILD:-0}" = "1" ]; then
    echo "[devcontainer] Skipping liboqs build (MOHAWK_SKIP_LIBOQS_BUILD=1)"
    return
  fi

  if pkg-config --exists liboqs 2>/dev/null || [ -f /usr/local/lib/liboqs.so ] || [ -f /usr/local/lib64/liboqs.so ]; then
    echo "[devcontainer] liboqs already installed"
    return
  fi

  echo "[devcontainer] liboqs not found; building from source"
  local cache_dir="$HOME/.cache/liboqs"
  mkdir -p "$cache_dir"

  if [ ! -d "$cache_dir/liboqs/.git" ]; then
    rm -rf "$cache_dir/liboqs"
    git clone --depth 1 https://github.com/open-quantum-safe/liboqs.git "$cache_dir/liboqs"
  fi

  pushd "$cache_dir/liboqs" >/dev/null
  mkdir -p build
  cd build
  cmake -DCMAKE_BUILD_TYPE=Release ..
  make -j"$(nproc)"
  run_as_root make install
  run_as_root ldconfig || true
  popd >/dev/null
}

install_python_deps() {
  if [ "${MOHAWK_SKIP_PY_DEPS:-0}" = "1" ]; then
    echo "[devcontainer] Skipping Python dependency install (MOHAWK_SKIP_PY_DEPS=1)"
    return
  fi

  cd "${WORKSPACE_FOLDER:-$PWD}"
  if [ ! -f requirements.txt ]; then
    echo "[WARN] requirements.txt not found; skipping Python dependency install"
    return
  fi

  if [ ! -d .venv ]; then
    python3 -m venv .venv
  fi

  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install --upgrade pip setuptools wheel
  python -m pip install -r requirements.txt

  # Optional OQS wrapper used by secure flows.
  python -m pip install oqs || echo "[WARN] oqs Python wrapper installation failed; continuing"

  python - <<'PY'
import fastapi, uvicorn, requests, psutil  # noqa: F401
print("[devcontainer] Core Python dependencies imported successfully")
PY
}

install_system_deps
ensure_liboqs
install_python_deps

echo "[devcontainer] post-create complete"
