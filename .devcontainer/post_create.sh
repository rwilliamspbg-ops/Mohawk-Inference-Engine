#!/usr/bin/env bash
set -euo pipefail

echo "Running devcontainer post-create: install build deps and liboqs"
# install system deps (attempt apt, then apk)
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y build-essential cmake git python3-dev python3-pip pkg-config
elif command -v apk >/dev/null 2>&1; then
  sudo apk add --no-cache build-base cmake git python3 python3-dev py3-pip pkgconfig
else
  echo "Unknown package manager; please install build tools (cmake, make, git, python3-dev) manually"
fi

CACHE_DIR="$HOME/.cache/liboqs"
mkdir -p "$CACHE_DIR"
if [ ! -d "$CACHE_DIR/liboqs" ]; then
  git clone --depth 1 https://github.com/open-quantum-safe/liboqs.git "$CACHE_DIR/liboqs"
fi

pushd "$CACHE_DIR/liboqs"
mkdir -p build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j"$(nproc)"
if command -v sudo >/dev/null 2>&1; then
  sudo make install
else
  make install
fi
popd

# ensure pip and install oqs python package
python3 -m pip install --upgrade pip || true
python3 -m pip install oqs || true

echo "post-create complete"
