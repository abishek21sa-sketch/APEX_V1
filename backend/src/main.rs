//! APEX orchestration backend: routes the SvelteKit engineering workstation's
//! requests to the Python scientific service (service/main.py), wrapping the
//! slow /pareto search in a background job the frontend polls instead of
//! blocking on. See handlers.rs for why request/response bodies are passed
//! through as opaque JSON rather than duplicated as typed Rust structs, and
//! lib.rs for the route table (kept separate from main() so integration tests
//! can build the same router without a bound TCP listener).

use apex_backend::state::AppState;
use apex_backend::{build_router, jobs};

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let python_base_url =
        std::env::var("APEX_PYTHON_SERVICE_URL").unwrap_or_else(|_| "http://127.0.0.1:8001".to_string());
    let port: u16 = std::env::var("APEX_BACKEND_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8080);

    let state = AppState {
        http_client: reqwest::Client::new(),
        python_base_url,
        jobs: jobs::new_job_store(),
    };

    let app = build_router(state);

    let listener = tokio::net::TcpListener::bind(("0.0.0.0", port)).await.unwrap();
    tracing::info!("apex_backend listening on port {port}");
    axum::serve(listener, app).await.unwrap();
}
