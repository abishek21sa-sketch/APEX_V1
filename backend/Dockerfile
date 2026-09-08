# APEX orchestration backend (Rust/Axum). Build from the repo root:
#   docker build -f backend/Dockerfile -t apex-backend .
#
# Verified: `docker compose up --build` builds and runs this image, proxying
# real requests through to a real containerized scientific-service. First
# attempt failed here -- reqwest's default TLS backend (native-tls) needs
# system OpenSSL + pkg-config, neither present in rust:1-slim-bookworm, and
# this service never actually needs TLS (see Cargo.toml: it only ever talks
# plain HTTP to scientific-service, in-container or in dev). Fixed by
# switching reqwest to rustls-tls (default-features = false), which needs no
# system OpenSSL at all -- not by installing pkg-config/libssl-dev, which
# would have "fixed" the build while leaving unused TLS machinery in the
# image.

FROM rust:1-slim-bookworm AS builder
WORKDIR /app

# Cache the dependency build separately from source changes: compile a dummy
# main.rs against the real Cargo.toml/Cargo.lock first, so `cargo build` only
# recompiles apex_backend's own code (not its whole dependency tree) on a
# source-only change.
COPY backend/Cargo.toml backend/Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs \
    && cargo build --release \
    && rm -rf src

COPY backend/src ./src
COPY backend/tests ./tests
RUN cargo build --release

FROM debian:bookworm-slim
# reqwest's default TLS backend expects a CA bundle even though this service
# only talks to the Python scientific service over plain HTTP inside the
# compose network -- cheap to include, avoids a surprise if that ever changes.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/apex_backend /usr/local/bin/apex_backend

EXPOSE 8080
ENV APEX_BACKEND_PORT=8080
# APEX_PYTHON_SERVICE_URL defaults to http://127.0.0.1:8001 (main.rs) -- set it
# via docker-compose.yml to the scientific-service container's name instead.

CMD ["apex_backend"]
