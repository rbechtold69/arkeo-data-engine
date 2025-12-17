# ---------- Stage 1: build arkeod, api, indexer, sentinel, tools ----------
FROM golang:1.22 AS builder

RUN apt-get update && apt-get install -y git make build-essential curl jq && rm -rf /var/lib/apt/lists/*

WORKDIR /src

# Clone latest Arkeo source (public repo)
RUN git clone --branch Upgrade-for-v1.0.16 --single-branch https://github.com/arkeonetwork/arkeo.git

WORKDIR /src/arkeo

# Build: arkeod, api, indexer, sentinel
RUN make install

# Build: extra tools (signing utilities, helpers, etc.)
RUN make tools

# Install Foundry (cast/anvil/forge) for signing; we only copy cast into runtime
RUN curl -L https://foundry.paradigm.xyz | bash \
    && /root/.foundry/bin/foundryup -i nightly

# Fetch osmosisd release binary (v25.0.0) for key mgmt/signing
RUN curl -L https://github.com/osmosis-labs/osmosis/releases/download/v25.0.0/osmosisd-25.0.0-linux-amd64 -o /go/bin/osmosisd \
    && chmod +x /go/bin/osmosisd

# Show all compiled/downloaded binaries
RUN ls -al $(go env GOPATH)/bin/

# ---------- Stage 2: build admin UI bundle ----------
FROM node:20-bullseye AS ui-builder
WORKDIR /app/admin

COPY admin/package*.json ./
RUN npm install
COPY admin/src ./src
RUN mkdir -p vendor && npm run build


# ---------- Stage 3: Runtime container ----------
FROM debian:12-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    supervisor \
    python3 \
    python3-venv \
    python3-flask \
    jq \
    python3-yaml \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all binaries produced by make install + make tools
COPY --from=builder /go/bin/* /usr/local/bin/
# Copy cast (Foundry) and osmosisd (built from source)
COPY --from=builder /go/bin/osmosisd /usr/local/bin/
COPY --from=builder /root/.foundry/bin/cast /usr/local/bin/

# Copy configs (genesis.json, config.toml, sentinel-config.yaml)
COPY config/ /app/config/

# Copy simple admin UI
COPY admin/ /app/admin/
COPY --from=ui-builder /app/admin/vendor/cosmos.bundle.js /app/admin/vendor/cosmos.bundle.js
COPY admin_api.py /app/admin_api.py
COPY cache_fetcher.py /app/cache_fetcher.py

# Supervisor + entrypoint
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose the admin UI (8079) and admin API (9998).
EXPOSE 8079 9998

ENTRYPOINT ["/app/entrypoint.sh"]
