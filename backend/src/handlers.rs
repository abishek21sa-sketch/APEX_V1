//! HTTP handlers. Vehicle/candidate/mission/objective payloads are treated as
//! opaque JSON here rather than typed Rust structs mirroring Python's Pydantic
//! schemas -- domain modeling of the physics/design space is Python's job (see
//! service/schemas.py), not Rust's; duplicating it here would mean two sources of
//! truth for what a "candidate" or "mission" is. Rust's job is orchestration:
//! routing, job management for the slow endpoint, and translating Python's
//! responses/errors into HTTP responses the frontend can react to.

use axum::extract::{Path, State};
use axum::http::StatusCode;
use axum::response::{IntoResponse, Json};
use serde_json::json;
use uuid::Uuid;

use crate::jobs::{JobStatus, JobStatusResponse};
use crate::state::AppState;

pub async fn health(State(state): State<AppState>) -> impl IntoResponse {
    let python_url = format!("{}/health", state.python_base_url);
    let python_ok = state
        .http_client
        .get(&python_url)
        .send()
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false);
    Json(json!({
        "status": "ok",
        "python_service": if python_ok { "ok" } else { "unreachable" },
    }))
}

async fn proxy_get(state: &AppState, path: &str) -> (StatusCode, Json<serde_json::Value>) {
    let url = format!("{}{}", state.python_base_url, path);
    match state.http_client.get(&url).send().await {
        Ok(resp) => {
            let status = StatusCode::from_u16(resp.status().as_u16()).unwrap_or(StatusCode::BAD_GATEWAY);
            let body = resp
                .json::<serde_json::Value>()
                .await
                .unwrap_or_else(|e| json!({ "detail": format!("invalid response from python service: {e}") }));
            (status, Json(body))
        }
        Err(e) => (
            StatusCode::BAD_GATEWAY,
            Json(json!({ "detail": format!("failed to reach python service: {e}") })),
        ),
    }
}

async fn proxy_post(state: &AppState, path: &str, body: &serde_json::Value) -> (StatusCode, Json<serde_json::Value>) {
    let url = format!("{}{}", state.python_base_url, path);
    match state.http_client.post(&url).json(body).send().await {
        Ok(resp) => {
            let status = StatusCode::from_u16(resp.status().as_u16()).unwrap_or(StatusCode::BAD_GATEWAY);
            let response_body = resp
                .json::<serde_json::Value>()
                .await
                .unwrap_or_else(|e| json!({ "detail": format!("invalid response from python service: {e}") }));
            (status, Json(response_body))
        }
        Err(e) => (
            StatusCode::BAD_GATEWAY,
            Json(json!({ "detail": format!("failed to reach python service: {e}") })),
        ),
    }
}

pub async fn design_space(State(state): State<AppState>) -> impl IntoResponse {
    proxy_get(&state, "/design-space").await
}

pub async fn requirement_kinds(State(state): State<AppState>) -> impl IntoResponse {
    proxy_get(&state, "/requirement-kinds").await
}

pub async fn benchmark_vehicles(State(state): State<AppState>) -> impl IntoResponse {
    proxy_get(&state, "/benchmark-vehicles").await
}

pub async fn surrogate_comparison(State(state): State<AppState>, uri: axum::http::Uri) -> impl IntoResponse {
    let path = format!("/surrogate-comparison{}", uri.query().map(|query| format!("?{query}")).unwrap_or_default());
    proxy_get(&state, &path).await
}

pub async fn robust_requirement_kinds(State(state): State<AppState>) -> impl IntoResponse {
    proxy_get(&state, "/robust-requirement-kinds").await
}

pub async fn robust_check(State(state): State<AppState>, Json(body): Json<serde_json::Value>) -> impl IntoResponse {
    proxy_post(&state, "/robust-check", &body).await
}

pub async fn evaluate(State(state): State<AppState>, Json(body): Json<serde_json::Value>) -> impl IntoResponse {
    proxy_post(&state, "/evaluate", &body).await
}

/// Plain proxy, not a job -- a single agent turn (a few tool-calling hops) is
/// slow but bounded, unlike /pareto's NSGA2 search, so it doesn't need the
/// spawn-and-poll treatment start_pareto_job gets.
pub async fn agent_chat(State(state): State<AppState>, Json(body): Json<serde_json::Value>) -> impl IntoResponse {
    proxy_post(&state, "/agent/chat", &body).await
}

/// Returns immediately with a job_id; the actual NSGA2 search (tens of seconds)
/// runs in a spawned background task, polled via get_pareto_job.
pub async fn start_pareto_job(State(state): State<AppState>, Json(body): Json<serde_json::Value>) -> impl IntoResponse {
    let job_id = Uuid::new_v4();
    state.jobs.lock().await.insert(job_id, JobStatus::Running);

    let client = state.http_client.clone();
    let url = format!("{}/pareto", state.python_base_url);
    let jobs = state.jobs.clone();

    tokio::spawn(async move {
        let status = match client.post(&url).json(&body).send().await {
            Ok(resp) if resp.status().is_success() => match resp.json::<serde_json::Value>().await {
                Ok(json_body) => JobStatus::Done(json_body),
                Err(e) => JobStatus::Error(format!("failed to parse python response: {e}")),
            },
            Ok(resp) => {
                let status_code = resp.status();
                let text = resp.text().await.unwrap_or_default();
                JobStatus::Error(format!("python service returned {status_code}: {text}"))
            }
            Err(e) => JobStatus::Error(format!("failed to reach python service: {e}")),
        };
        jobs.lock().await.insert(job_id, status);
    });

    (StatusCode::ACCEPTED, Json(json!({ "job_id": job_id })))
}

pub async fn get_pareto_job(State(state): State<AppState>, Path(job_id): Path<Uuid>) -> impl IntoResponse {
    let jobs = state.jobs.lock().await;
    match jobs.get(&job_id) {
        Some(status) => (StatusCode::OK, Json(JobStatusResponse::from(status))).into_response(),
        None => (StatusCode::NOT_FOUND, Json(JobStatusResponse::NotFound)).into_response(),
    }
}
