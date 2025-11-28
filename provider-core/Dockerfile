# ---------- Stage 1: build arkeod ----------
FROM golang:1.22 AS arkeod-builder

RUN apt-get update && apt-get install -y git make && rm -rf /var/lib/apt/lists/*

WORKDIR /src
# TODO: adjust repo path if needed
RUN git clone https://github.com/arkeonetwork/arkeo.git
WORKDIR /src/arkeo
RUN make build || go build -o /out/arkeod ./cmd/arkeod


# ---------- Stage 2: build sentinel ----------
FROM golang:1.22 AS sentinel-builder

RUN apt-get update && apt-get install -y git make && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git clone https://github.com/arkeonetwork/sentinel.git
WORKDIR /src/sentinel
RUN make build || go build -o /out/sentinel ./cmd/sentinel


# ---------- Final stage: provider runtime ----------
FROM debian:12-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    supervisor \
    python3 \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy the binaries
COPY --from=arkeod-builder /out/arkeod /usr/local/bin/arkeod
COPY --from=sentinel-builder /out/sentinel /usr/local/bin/sentinel

# configs (your .toml, genesis, sentinel config)
COPY config/ /app/config/

# simple web admin
COPY admin/ /app/admin/

# supervisor + entrypoint
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 26657 1317 8080

ENTRYPOINT ["/app/entrypoint.sh"]