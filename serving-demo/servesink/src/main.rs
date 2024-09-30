use numaflow::sink;
use numaflow::sink::{Response, SinkRequest};
use reqwest::Client;
use tracing::{error, warn};

const NUMAFLOW_CALLBACK_URL_HEADER: &str = "X-Numaflow-Callback-Url";
const NUMAFLOW_ID_HEADER: &str = "X-Numaflow-Id";

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    sink::Server::new(ServeSink::new()).start().await
}

struct ServeSink {
    callback_url_key: String,
    message_id_key: String,
    client: Client,
}

impl ServeSink {
    fn new() -> Self {
        // extract the callback url key from the environment
        let callback_url_key = std::env::var("NUMAFLOW_CALLBACK_URL_KEY")
            .unwrap_or_else(|_| NUMAFLOW_CALLBACK_URL_HEADER.to_string());

        // extract the message id key from the environment
        let message_id_key = std::env::var("NUMAFLOW_MESSAGE_ID_KEY")
            .unwrap_or_else(|_| NUMAFLOW_ID_HEADER.to_string());

        Self {
            callback_url_key,
            message_id_key,
            client: Client::builder()
                .danger_accept_invalid_certs(true)
                .build()
                .unwrap(),
        }
    }
}

#[tonic::async_trait]
impl sink::Sinker for ServeSink {
    async fn sink(&self, mut input: tokio::sync::mpsc::Receiver<SinkRequest>) -> Vec<Response> {
        let mut responses: Vec<Response> = Vec::new();

        while let Some(datum) = input.recv().await {
            // if the callback url is absent, ignore the request
            let url = match datum.headers.get(self.callback_url_key.as_str()) {
                Some(url) => url,
                None => {
                    warn!(
                        "Missing {} header, Ignoring the request",
                        self.callback_url_key
                    );
                    responses.push(Response::ok(datum.id));
                    continue;
                }
            };

            // if the numaflow id is absent, ignore the request
            let numaflow_id = match datum.headers.get(self.message_id_key.as_str()) {
                Some(id) => id,
                None => {
                    warn!(
                        "Missing {} header, Ignoring the request",
                        self.message_id_key
                    );
                    responses.push(Response::ok(datum.id));
                    continue;
                }
            };

            let resp = self
                .client
                .post(format!("{}_{}", url, "save"))
                .header(self.message_id_key.as_str(), numaflow_id)
                .header("id", numaflow_id)
                .body(datum.value)
                .send()
                .await;

            let response = match resp {
                Ok(_) => Response::ok(datum.id),
                Err(e) => {
                    error!("Sending result to serving URL {:?}", e);
                    Response::failure(datum.id, format!("Failed to send: {}", e))
                }
            };

            responses.push(response);
        }
        responses
    }
}
