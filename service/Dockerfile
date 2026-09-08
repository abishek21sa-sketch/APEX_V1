# APEX scientific service (Python/FastAPI). Build from the repo root:
#   docker build -f service/Dockerfile -t apex-service .
#
# Verified: `docker compose up --build` builds and runs this image; real
# /evaluate and /pareto requests proxied from the browser through the Rust
# backend container land here and return real physics-sim results.

FROM python:3.11-slim

WORKDIR /app

# numpy/scipy/scikit-learn/pymoo mostly ship manylinux wheels for linux/amd64,
# but a compiler is kept here defensively in case any transitive dependency
# needs to build from source on whatever platform this actually gets built on.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src
COPY service ./service
COPY agent ./agent

# [service] gets the FastAPI app running; [agent] is included so /agent/chat
# (Phase 9) works out of the box. It degrades gracefully rather than crashing
# either way it can be misconfigured: a 501 if the agent extra itself isn't
# installed (not the case here -- it's installed), a 401 with a clear message
# if it's installed but ANTHROPIC_API_KEY isn't set at runtime.
RUN pip install --no-cache-dir -e ".[service,agent]"

EXPOSE 8001

# uvicorn's CLI inserts the current working directory onto sys.path so
# `service.main:app` resolves without `service/` needing to be its own
# installed package (only `apex`, under src/, goes through the pyproject.toml
# package-discovery/install path) -- this matches how the service is run
# locally (`uvicorn service.main:app` from the repo root), not a Docker-only
# workaround.
CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8001"]
