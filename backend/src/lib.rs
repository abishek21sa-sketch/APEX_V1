//! APEX orchestration backend library: exposes build_router() so integration
//! tests can exercise the real route table (via tower::ServiceExt::oneshot)
//! without needing a bound TCP listener or a running Python service for every
//! test -- see tests/integration_test.rs.

pub mod handlers;
pub mod jobs;
pub mod state;

use axum::routing::{get, post};
use axum::Router;
use tower_http::cors::{Any, CorsLayer};
use tower_http::trace::TraceLayer;

use state::AppState;

pub fn build_router(state: AppState) -> Router {
    // Permissive CORS: this is a local dev/demo orchestration layer, not a
    // public-facing deployment -- a real deployment would scope this to the
    // frontend's actual origin.
    let cors = CorsLayer::new().allow_origin(Any).allow_methods(Any).allow_headers(Any);

    Router::new()
        .route("/api/health", get(handlers::health))
        .route("/api/design-space", get(handlers::design_space))
        .route("/api/requirement-kinds", get(handlers::requirement_kinds))
        .route("/api/benchmark-vehicles", get(handlers::benchmark_vehicles))
        .route("/api/surrogate-comparison", get(handlers::surrogate_comparison))
        .route("/api/robust-requirement-kinds", get(handlers::robust_requirement_kinds))
        .route("/api/robust-check", post(handlers::robust_check))
        .route("/api/evaluate", post(handlers::evaluate))
        .route("/api/pareto", post(handlers::start_pareto_job))
        .route("/api/pareto/:job_id", get(handlers::get_pareto_job))
        .route("/api/agent/chat", post(handlers::agent_chat))
        .layer(cors)
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}
