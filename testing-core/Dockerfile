# Arkeo Testing Core - static test container (no sentinel, no APIs)
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /app/config

# Static admin page
COPY admin/ /app/admin/
COPY entrypoint.sh /app/entrypoint.sh
COPY server.py /app/server.py
RUN chmod +x /app/entrypoint.sh

# Serve the static page on the admin port; expose the optional API port for parity with run scripts
EXPOSE 8078 9997

ENTRYPOINT ["/app/entrypoint.sh"]
