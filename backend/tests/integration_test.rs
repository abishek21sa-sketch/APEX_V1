//! Integration tests exercising the real route table via tower::ServiceExt::oneshot
//! (no bound TCP listener needed). Deliberately point python_base_url at a closed
//! port rather than mocking Python's HTTP responses -- these tests are about
//! verifying Rust's own error handling when the thing it orchestrates is
//! unreachable, not about re-testing Python's endpoint logic (that's
//! tests/test_service.py's job). The happy path against a real running Python
//! service was verified manually end to end during development; see the phase 8
//! section of README.md.

use apex_backend::build_router;
use apex_backend::state::AppState;
use axum::body::Body;
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use tower::ServiceExt;

fn unreachable_state() -> AppState {
    AppState {
        // Short connect timeout: an unassigned high port should refuse the
        // connection almost immediately, but bound it explicitly rather than
        // relying on that so these tests fail fast instead of hanging if the
        // environment's networking behaves differently.
        http_client: reqwest::Client::builder()
            .connect_timeout(std::time::Duration::from_secs(2))
            .build()
            .unwrap(),
        python_base_url: "http://127.0.0.1:59999".to_string(),
        jobs: apex_backend::jobs::new_job_store(),
    }
}

async fn body_json(response: axum::response::Response) -> serde_json::Value {
    let bytes = response.into_body().collect().await.unwrap().to_bytes();
    serde_json::from_slice(&bytes).unwrap()
}

#[tokio::test]
async fn health_reports_unreachable_python_without_erroring() {
    let app = build_router(unreachable_state());
    let response = app
        .oneshot(Request::builder().uri("/api/health").body(Body::empty()).unwrap())
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body = body_json(response).await;
    assert_eq!(body["status"], "ok");
    assert_eq!(body["python_service"], "unreachable");
}

#[tokio::test]
async fn evaluate_returns_bad_gateway_when_python_is_unreachable() {
    let app = build_router(unreachable_state());
    let request = Request::builder()
        .method("POST")
        .uri("/api/evaluate")
        .header("content-type", "application/json")
        .body(Body::from("{}"))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();
    assert_eq!(response.status(), StatusCode::BAD_GATEWAY);
}

#[tokio::test]
async fn benchmark_vehicles_returns_bad_gateway_when_python_is_unreachable() {
    let app = build_router(unreachable_state());
    let response = app
        .oneshot(Request::builder().uri("/api/benchmark-vehicles").body(Body::empty()).unwrap())
        .await
        .unwrap();
    assert_eq!(response.status(), StatusCode::BAD_GATEWAY);
}

#[tokio::test]
async fn robust_check_returns_bad_gateway_when_python_is_unreachable() {
    let app = build_router(unreachable_state());
    let request = Request::builder()
        .method("POST")
        .uri("/api/robust-check")
        .header("content-type", "application/json")
        .body(Body::from("{}"))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();
    assert_eq!(response.status(), StatusCode::BAD_GATEWAY);
}

#[tokio::test]
async fn agent_chat_returns_bad_gateway_when_python_is_unreachable() {
    let app = build_router(unreachable_state());
    let request = Request::builder()
        .method("POST")
        .uri("/api/agent/chat")
        .header("content-type", "application/json")
        .body(Body::from(r#"{"message": "hi"}"#))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();
    assert_eq!(response.status(), StatusCode::BAD_GATEWAY);
}

#[tokio::test]
async fn get_unknown_pareto_job_returns_not_found() {
    let app = build_router(unreachable_state());
    let unknown_id = uuid::Uuid::new_v4();
    let response = app
        .oneshot(
            Request::builder()
                .uri(format!("/api/pareto/{unknown_id}"))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn pareto_job_transitions_from_running_to_error_when_python_is_unreachable() {
    let app = build_router(unreachable_state());
    let start_request = Request::builder()
        .method("POST")
        .uri("/api/pareto")
        .header("content-type", "application/json")
        .body(Body::from("{}"))
        .unwrap();

    let start_response = app.clone().oneshot(start_request).await.unwrap();
    assert_eq!(start_response.status(), StatusCode::ACCEPTED);
    let start_body = body_json(start_response).await;
    let job_id = start_body["job_id"].as_str().unwrap();

    // The background task needs a moment to attempt the (failing) request and
    // update job state; poll briefly rather than sleeping a fixed guess.
    let mut final_status = String::new();
    for _ in 0..150 {
        let poll_response = app
            .clone()
            .oneshot(
                Request::builder()
                    .uri(format!("/api/pareto/{job_id}"))
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        let poll_body = body_json(poll_response).await;
        final_status = poll_body["status"].as_str().unwrap().to_string();
        if final_status != "running" {
            assert_eq!(final_status, "error");
            return;
        }
        tokio::time::sleep(std::time::Duration::from_millis(20)).await;
    }
    panic!("pareto job never left the running state (last status: {final_status})");
}
