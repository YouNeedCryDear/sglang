use crate::router::PolicyConfig;
use crate::router::Router;
#[cfg(feature = "k8s")]
use crate::k8s_discovery::{DiscoveryCommand, K8sDiscoveryConfig, run_k8s_discovery_task};
#[cfg(not(feature = "k8s"))]
use crate::k8s_discovery::K8sDiscoveryConfig;

use actix_web::{
    error, get, post, web, App, Error, HttpRequest, HttpResponse, HttpServer, Responder,
};
use bytes::Bytes;
use env_logger::Builder;
use futures_util::StreamExt;
use log::{info, LevelFilter, warn};
use std::collections::HashMap;
use std::io::Write;
use std::time::Duration;

#[derive(Debug)]
pub struct AppState {
    router: Router,
    client: reqwest::Client,
}

impl AppState {
    pub fn new(
        worker_urls: Vec<String>,
        client: reqwest::Client,
        policy_config: PolicyConfig,
    ) -> Result<Self, String> {
        // Create router based on policy
        let router = Router::new(worker_urls, policy_config)?;
        Ok(Self { router, client })
    }
}

async fn sink_handler(_req: HttpRequest, mut payload: web::Payload) -> Result<HttpResponse, Error> {
    // Drain the payload
    while let Some(chunk) = payload.next().await {
        if let Err(err) = chunk {
            println!("Error while draining payload: {:?}", err);
            break;
        }
    }
    Ok(HttpResponse::NotFound().finish())
}

// Custom error handler for JSON payload errors.
fn json_error_handler(_err: error::JsonPayloadError, _req: &HttpRequest) -> Error {
    error::ErrorPayloadTooLarge("Payload too large")
}

#[get("/health")]
async fn health(req: HttpRequest, data: web::Data<AppState>) -> impl Responder {
    data.router
        .route_to_first(&data.client, "/health", &req)
        .await
}

#[get("/health_generate")]
async fn health_generate(req: HttpRequest, data: web::Data<AppState>) -> impl Responder {
    data.router
        .route_to_first(&data.client, "/health_generate", &req)
        .await
}

#[get("/get_server_info")]
async fn get_server_info(req: HttpRequest, data: web::Data<AppState>) -> impl Responder {
    data.router
        .route_to_first(&data.client, "/get_server_info", &req)
        .await
}

#[get("/v1/models")]
async fn v1_models(req: HttpRequest, data: web::Data<AppState>) -> impl Responder {
    data.router
        .route_to_first(&data.client, "/v1/models", &req)
        .await
}

#[get("/get_model_info")]
async fn get_model_info(req: HttpRequest, data: web::Data<AppState>) -> impl Responder {
    data.router
        .route_to_first(&data.client, "/get_model_info", &req)
        .await
}

#[post("/generate")]
async fn generate(req: HttpRequest, body: Bytes, data: web::Data<AppState>) -> impl Responder {
    data.router
        .route_generate_request(&data.client, &req, &body, "/generate")
        .await
}

#[post("/v1/chat/completions")]
async fn v1_chat_completions(
    req: HttpRequest,
    body: Bytes,
    data: web::Data<AppState>,
) -> impl Responder {
    data.router
        .route_generate_request(&data.client, &req, &body, "/v1/chat/completions")
        .await
}

#[post("/v1/completions")]
async fn v1_completions(
    req: HttpRequest,
    body: Bytes,
    data: web::Data<AppState>,
) -> impl Responder {
    data.router
        .route_generate_request(&data.client, &req, &body, "/v1/completions")
        .await
}

#[post("/add_worker")]
async fn add_worker(
    query: web::Query<HashMap<String, String>>,
    data: web::Data<AppState>,
) -> impl Responder {
    let worker_url = match query.get("url") {
        Some(url) => url.to_string(),
        None => {
            return HttpResponse::BadRequest()
                .body("Worker URL required. Provide 'url' query parameter")
        }
    };

    match data.router.add_worker(&worker_url).await {
        Ok(message) => HttpResponse::Ok().body(message),
        Err(error) => HttpResponse::BadRequest().body(error),
    }
}

#[post("/remove_worker")]
async fn remove_worker(
    query: web::Query<HashMap<String, String>>,
    data: web::Data<AppState>,
) -> impl Responder {
    let worker_url = match query.get("url") {
        Some(url) => url.to_string(),
        None => return HttpResponse::BadRequest().finish(),
    };
    data.router.remove_worker(&worker_url);
    HttpResponse::Ok().body(format!("Successfully removed worker: {}", worker_url))
}

pub struct ServerConfig {
    pub host: String,
    pub port: u16,
    pub worker_urls: Vec<String>,
    pub policy_config: PolicyConfig,
    pub verbose: bool,
    pub max_payload_size: usize,
    pub enable_k8s_discovery: bool,
    pub k8s_discovery_config: Option<K8sDiscoveryConfig>,
}

pub async fn startup(config: ServerConfig) -> std::io::Result<()> {
    // Initialize logger
    Builder::new()
        .format(|buf, record| {
            use chrono::Local;
            writeln!(
                buf,
                "[Router (Rust)] {} - {} - {}",
                Local::now().format("%Y-%m-%d %H:%M:%S"),
                record.level(),
                record.args()
            )
        })
        .filter(
            None,
            if config.verbose {
                LevelFilter::Debug
            } else {
                LevelFilter::Info
            },
        )
        .init();

    info!("🚧 Initializing router on {}:{}", config.host, config.port);
    info!("🚧 Initializing workers on {:?}", config.worker_urls);
    info!("🚧 Policy Config: {:?}", config.policy_config);
    info!(
        "🚧 Max payload size: {} MB",
        config.max_payload_size / (1024 * 1024)
    );
    
    #[cfg(feature = "k8s")]
    if config.enable_k8s_discovery {
        info!("🚧 Kubernetes service discovery is enabled (feature 'k8s' active)");
        if let Some(k8s_config) = &config.k8s_discovery_config {
            info!("🚧 Kubernetes service discovery config: {:?}", k8s_config);
        } else {
            // This case shouldn't happen if enable_k8s_discovery is true due to lib.rs logic
            info!("🚧 Using default Kubernetes service discovery configuration (Warning: config was None)");
        }
    }
    #[cfg(not(feature = "k8s"))]
    if config.enable_k8s_discovery {
        // Log a warning if the user tries to enable k8s discovery without the feature compiled in
        warn!("Kubernetes service discovery requested but 'k8s' feature is not compiled. Ignoring.");
    }

    let client = reqwest::Client::builder()
        .pool_idle_timeout(Some(Duration::from_secs(50)))
        .build()
        .expect("Failed to create HTTP client");

    let app_state = web::Data::new(
        AppState::new(
            config.worker_urls.clone(),
            client,
            config.policy_config.clone(),
        )
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?,
    );
    
    // Start Kubernetes service discovery only if feature is enabled AND config flag is true
    #[cfg(feature = "k8s")]
    if config.enable_k8s_discovery {
        if let Some(k8s_config) = config.k8s_discovery_config {
             info!("🚧 Starting Kubernetes service discovery task...");
            // Start the discovery task and get the receiver
            match run_k8s_discovery_task(k8s_config).await {
                Ok(mut receiver) => {
                    let router_ref = app_state.router.clone();
                    
                    // Process discovery commands in a background task
                    tokio::spawn(async move {
                        info!("✅ Kubernetes service discovery background task is running");
                        while let Some(cmd) = receiver.recv().await {
                            match cmd {
                                DiscoveryCommand::AddWorker(url) => {
                                    match router_ref.add_worker(&url).await {
                                        Ok(msg) => info!("K8s discovery: {}", msg),
                                        Err(err) => info!("K8s discovery error: {}", err),
                                    }
                                },
                                DiscoveryCommand::RemoveWorker(url) => {
                                    router_ref.remove_worker(&url);
                                    info!("K8s discovery: Removed worker {}", url);
                                },
                            }
                        }
                        info!("Kubernetes service discovery background task finished.");
                    });
                },
                Err(e) => {
                    log::error!("❌ Failed to start Kubernetes service discovery task: {:?}", e);
                }
            }
        } else {
             log::error!("❌ Tried to start k8s discovery but config was missing!");
        }
    }

    info!("✅ Serving router on {}:{}", config.host, config.port);
    info!("✅ Initial workers: {:?}", app_state.router.get_worker_urls()); // Add a helper to get current workers

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .app_data(
                web::JsonConfig::default()
                    .limit(config.max_payload_size)
                    .error_handler(json_error_handler),
            )
            .app_data(web::PayloadConfig::default().limit(config.max_payload_size))
            .service(generate)
            .service(v1_chat_completions)
            .service(v1_completions)
            .service(v1_models)
            .service(get_model_info)
            .service(health)
            .service(health_generate)
            .service(get_server_info)
            .service(add_worker)
            .service(remove_worker)
            // Default handler for unmatched routes.
            .default_service(web::route().to(sink_handler))
    })
    .bind((config.host, config.port))?
    .run()
    .await
}
