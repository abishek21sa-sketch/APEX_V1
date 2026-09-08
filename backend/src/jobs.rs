//! In-memory job store for long-running requests (Pareto searches) proxied to the
//! Python scientific service. Rust's whole reason to sit in front of Python here:
//! the platform proposal splits it as "Rust... manage[s] simulations and
//! orchestrate[s] jobs while Python runs the scientific workers" -- a synchronous
//! call to Python would block the HTTP response for as long as NSGA2 takes to
//! converge (tens of seconds), so this wraps it in a background task the client
//! polls instead of waiting on.
//!
//! No TTL/eviction: jobs live for the process's lifetime. Fine for a dev/demo
//! server: a real deployment would need to expire old job results.

use std::collections::HashMap;
use std::sync::Arc;

use serde::Serialize;
use tokio::sync::Mutex;
use uuid::Uuid;

#[derive(Clone)]
pub enum JobStatus {
    Running,
    Done(serde_json::Value),
    Error(String),
}

pub type JobStore = Arc<Mutex<HashMap<Uuid, JobStatus>>>;

pub fn new_job_store() -> JobStore {
    Arc::new(Mutex::new(HashMap::new()))
}

#[derive(Serialize)]
#[serde(tag = "status", rename_all = "snake_case")]
pub enum JobStatusResponse {
    Running,
    Done { result: serde_json::Value },
    Error { message: String },
    NotFound,
}

impl From<&JobStatus> for JobStatusResponse {
    fn from(status: &JobStatus) -> Self {
        match status {
            JobStatus::Running => JobStatusResponse::Running,
            JobStatus::Done(result) => JobStatusResponse::Done { result: result.clone() },
            JobStatus::Error(message) => JobStatusResponse::Error { message: message.clone() },
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn running_status_serializes_with_tag_only() {
        let response = JobStatusResponse::from(&JobStatus::Running);
        let json = serde_json::to_value(&response).unwrap();
        assert_eq!(json, serde_json::json!({ "status": "running" }));
    }

    #[test]
    fn done_status_serializes_with_result_payload() {
        let result = serde_json::json!({ "n_points": 3 });
        let response = JobStatusResponse::from(&JobStatus::Done(result.clone()));
        let json = serde_json::to_value(&response).unwrap();
        assert_eq!(json, serde_json::json!({ "status": "done", "result": result }));
    }

    #[test]
    fn error_status_serializes_with_message() {
        let response = JobStatusResponse::from(&JobStatus::Error("boom".to_string()));
        let json = serde_json::to_value(&response).unwrap();
        assert_eq!(json, serde_json::json!({ "status": "error", "message": "boom" }));
    }

    #[tokio::test]
    async fn new_job_store_starts_empty() {
        let store = new_job_store();
        assert!(store.lock().await.is_empty());
    }
}
