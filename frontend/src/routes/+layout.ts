// Every route only ever talks to a locally-running Rust backend (see
// src/lib/api.ts); there's nothing meaningful to server-render, and SSR
// would try to reach it at build/prerender time when it's very likely not
// running. Applies site-wide rather than per-page.
export const ssr = false;
