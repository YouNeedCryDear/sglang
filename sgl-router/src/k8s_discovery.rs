use anyhow::Result;
use futures::{StreamExt, TryStreamExt};
use k8s_openapi::api::core::v1::Endpoints;
use kube::{
    api::{Api, ListParams, ResourceExt, WatchEvent},
    Client,
};
use log::{debug, error, info, warn};
use std::collections::{HashMap, HashSet};
use std::env;
use std::sync::Arc;
use thiserror::Error;
use tokio::sync::mpsc;

#[derive(Debug, Clone)]
pub enum DiscoveryCommand {
    AddWorker(String),
    RemoveWorker(String),
}

#[derive(Error, Debug)]
pub enum K8sDiscoveryError {
    #[error("Kubernetes client error: {0}")]
    KubeError(#[from] kube::Error),
    
    #[error("Failed to watch Kubernetes endpoints: {0}")]
    WatchError(String),
    
    #[error("Configuration error: {0}")]
    ConfigError(String),
}

struct EndpointState {
    urls: HashSet<String>,
}

// Configuration for the Kubernetes service discovery
#[derive(Debug, Clone)]
pub struct K8sDiscoveryConfig {
    // Label selector for finding LLM worker services (e.g., "sgl-role=llm-worker")
    pub label_selector: String,
    
    // Port name to use from the endpoint (if None, will use the first available port)
    pub port_name: Option<String>,
    
    // Protocol to use (http/https)
    pub protocol: String,
    
    // Path to append to the worker URL
    pub worker_path: String,
}

impl Default for K8sDiscoveryConfig {
    fn default() -> Self {
        Self {
            label_selector: env::var("SGL_K8S_LABEL_SELECTOR").unwrap_or_else(|_| "sgl-role=llm-worker".to_string()),
            port_name: env::var("SGL_K8S_PORT_NAME").ok(),
            protocol: env::var("SGL_K8S_PROTOCOL").unwrap_or_else(|_| "http".to_string()),
            worker_path: env::var("SGL_K8S_WORKER_PATH").unwrap_or_else(|_| "".to_string()),
        }
    }
}

// Starts the Kubernetes service discovery task
pub async fn start_k8s_discovery(
    config: K8sDiscoveryConfig,
    sender: mpsc::Sender<DiscoveryCommand>,
) -> Result<(), K8sDiscoveryError> {
    // Initialize the Kubernetes client
    let client = Client::try_default().await.map_err(K8sDiscoveryError::KubeError)?;
    
    // Create API for Endpoints
    let endpoints: Api<Endpoints> = Api::all(client);
    
    // Create a label selector from our config
    let lp = ListParams::default().labels(&config.label_selector);
    
    // Track the known endpoints state
    let mut known_endpoints: HashMap<String, EndpointState> = HashMap::new();
    
    info!("Starting Kubernetes service discovery with label selector: {}", config.label_selector);
    
    // Stream of watch events
    let mut stream = endpoints.watch(&lp, "0").await?.boxed();
    
    // Process watch events
    while let Some(event) = stream.try_next().await.map_err(|e| K8sDiscoveryError::WatchError(e.to_string()))? {
        match event {
            WatchEvent::Added(endpoints) | WatchEvent::Modified(endpoints) => {
                // Extract relevant information from the endpoints
                process_endpoints_change(&endpoints, &config, &mut known_endpoints, &sender).await?;
            }
            WatchEvent::Deleted(endpoints) => {
                // Handle deletion of endpoints
                let name = endpoints.name_any();
                
                if let Some(state) = known_endpoints.remove(&name) {
                    for url in state.urls {
                        info!("Removing worker: {}", url);
                        if let Err(e) = sender.send(DiscoveryCommand::RemoveWorker(url.clone())).await {
                            error!("Failed to send remove worker command: {}", e);
                        }
                    }
                }
            }
            WatchEvent::Bookmark(_) => {
                // Just a bookmark, nothing to do
            }
            WatchEvent::Error(e) => {
                error!("Watch error: {:?}", e);
            }
        }
    }
    
    Ok(())
}

// Process changes to an Endpoints resource
async fn process_endpoints_change(
    endpoints: &Endpoints,
    config: &K8sDiscoveryConfig,
    known_endpoints: &mut HashMap<String, EndpointState>,
    sender: &mpsc::Sender<DiscoveryCommand>,
) -> Result<(), K8sDiscoveryError> {
    let name = endpoints.name_any();
    let mut new_urls = HashSet::new();
    
    // Extract all endpoint addresses
    if let Some(subsets) = &endpoints.subsets {
        for subset in subsets {
            if let Some(addresses) = &subset.addresses {
                for address in addresses {
                    if let Some(ip) = &address.ip {
                        // Find the target port
                        if let Some(ports) = &subset.ports {
                            for port in ports {
                                // If port_name is specified, only use ports with matching name
                                if let Some(port_name) = &config.port_name {
                                    if let Some(name) = &port.name {
                                        if name != port_name {
                                            continue;
                                        }
                                    } else {
                                        continue;
                                    }
                                }
                                
                                if let Some(port_num) = port.port {
                                    // Construct worker URL
                                    let worker_url = format!(
                                        "{}://{}:{}{}",
                                        config.protocol,
                                        ip,
                                        port_num,
                                        if config.worker_path.is_empty() || config.worker_path.starts_with('/') {
                                            config.worker_path.clone()
                                        } else {
                                            format!("/{}", config.worker_path)
                                        }
                                    );
                                    new_urls.insert(worker_url);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    // Get or create endpoint state
    let state = known_endpoints.entry(name.clone()).or_insert_with(|| EndpointState {
        urls: HashSet::new(),
    });
    
    // Find URLs to add (present in new_urls but not in state.urls)
    let urls_to_add: Vec<String> = new_urls.difference(&state.urls).cloned().collect();
    
    // Find URLs to remove (present in state.urls but not in new_urls)
    let urls_to_remove: Vec<String> = state.urls.difference(&new_urls).cloned().collect();
    
    // Update known state
    state.urls = new_urls;
    
    // Send commands to add new workers
    for url in urls_to_add {
        info!("Adding worker: {}", url);
        if let Err(e) = sender.send(DiscoveryCommand::AddWorker(url.clone())).await {
            error!("Failed to send add worker command: {}", e);
        }
    }
    
    // Send commands to remove old workers
    for url in urls_to_remove {
        info!("Removing worker: {}", url);
        if let Err(e) = sender.send(DiscoveryCommand::RemoveWorker(url.clone())).await {
            error!("Failed to send remove worker command: {}", e);
        }
    }
    
    Ok(())
}

// Runs a background task that watches for Kubernetes endpoints and keeps the router updated
pub async fn run_k8s_discovery_task(config: K8sDiscoveryConfig) -> Result<mpsc::Receiver<DiscoveryCommand>, K8sDiscoveryError> {
    // Create a channel for communication
    let (sender, receiver) = mpsc::channel(100);
    
    // Spawn background task
    let sender_clone = sender.clone();
    tokio::spawn(async move {
        loop {
            if let Err(e) = start_k8s_discovery(config.clone(), sender_clone.clone()).await {
                error!("Kubernetes discovery error: {:?}. Retrying in 10 seconds...", e);
                tokio::time::sleep(tokio::time::Duration::from_secs(10)).await;
            }
        }
    });
    
    Ok(receiver)
}
