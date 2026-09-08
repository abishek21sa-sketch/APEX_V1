use crate::jobs::JobStore;

#[derive(Clone)]
pub struct AppState {
    pub http_client: reqwest::Client,
    pub python_base_url: String,
    pub jobs: JobStore,
}
