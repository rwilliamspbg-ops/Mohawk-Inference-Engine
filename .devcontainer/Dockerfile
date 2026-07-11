FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ca-certificates wget curl pkg-config \
    python3 python3-pip python3-venv python3-dev python-is-python3 \
    sudo lsof net-tools \
    libssl-dev libffi-dev \
    libgl1 libegl1 libxkbcommon-x11-0 libdbus-1-3 xauth && \
    rm -rf /var/lib/apt/lists/*

# Install liboqs from source
WORKDIR /opt
RUN git clone --depth 1 https://github.com/open-quantum-safe/liboqs.git && \
    mkdir -p liboqs/build && cd liboqs/build && \
    cmake -DCMAKE_BUILD_TYPE=Release .. && \
    make -j"$(nproc)" && make install && ldconfig

# Ensure pip is upgraded and install Python oqs wrapper
RUN python3 -m pip install --upgrade pip setuptools wheel && \
    python3 -m pip install oqs

WORKDIR /workspace
