# APEX SvelteKit workstation, built with @sveltejs/adapter-node into a
# standalone Node server. Build from the repo root:
#   docker build -f frontend/Dockerfile -t apex-frontend .
#
# Verified: `docker compose up --build` builds and runs this image, serving
# the real workstation UI against the containerized backend/scientific-service.
# This Dockerfile follows adapter-node's standard documented Docker pattern
# (build with full deps, `npm prune --production`, copy the pruned
# node_modules alongside build/ into the runtime stage) rather than a
# simplified guess, since adapter-node's output is NOT fully self-contained --
# unlike a purely static build, it still needs a pruned node_modules at runtime.

FROM node:22-slim AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
RUN npm prune --production

FROM node:22-slim
WORKDIR /app
COPY --from=builder /app/build build/
COPY --from=builder /app/node_modules node_modules/
COPY --from=builder /app/package.json .

EXPOSE 3000
ENV PORT=3000
ENV NODE_ENV=production
# The frontend calls the Rust backend directly from the BROWSER (src/lib/api.ts
# hardcodes http://127.0.0.1:8080/api), not from this server process -- so as
# long as docker-compose.yml port-maps the backend to the host, this works
# unchanged for a docker-compose deployment. A real multi-host deployment would
# need that hardcoded API_BASE turned into a build-time or runtime config
# value; not done here (see README.md's Phase 10 known-simplifications entry).

CMD ["node", "build/index.js"]
