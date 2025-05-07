use pyo3::prelude::*;
pub mod router;
pub mod server;
pub mod tree;
#[cfg(feature = "k8s")]
pub mod k8s_discovery;

// Add a stub for K8sDiscoveryConfig when feature is off to satisfy the ServerConfig struct
#[cfg(not(feature = "k8s"))]
mod k8s_discovery {
    #[derive(Debug, Clone, Default)] 
    pub struct K8sDiscoveryConfig {}
}

#[pyclass(eq)]
#[derive(Clone, PartialEq)]
pub enum PolicyType {
    Random,
    RoundRobin,
    CacheAware,
}

#[pyclass]
struct Router {
    host: String,
    port: u16,
    worker_urls: Vec<String>,
    policy: PolicyType,
    worker_startup_timeout_secs: u64,
    worker_startup_check_interval: u64,
    cache_threshold: f32,
    balance_abs_threshold: usize,
    balance_rel_threshold: f32,
    eviction_interval_secs: u64,
    max_tree_size: usize,
    max_payload_size: usize,
    verbose: bool,
    #[cfg(feature = "k8s")]
    enable_k8s_discovery: bool,
    #[cfg(feature = "k8s")]
    k8s_label_selector: String,
    #[cfg(feature = "k8s")]
    k8s_port_name: Option<String>,
    #[cfg(feature = "k8s")]
    k8s_protocol: String,
    #[cfg(feature = "k8s")]
    k8s_worker_path: String,
}

#[pymethods]
impl Router {
    #[new]
    #[cfg(not(feature = "k8s"))]
    #[pyo3(signature = (
        worker_urls,
        policy = PolicyType::RoundRobin,
        host = String::from("127.0.0.1"),
        port = 3001,
        worker_startup_timeout_secs = 300,
        worker_startup_check_interval = 10,
        cache_threshold = 0.50,
        balance_abs_threshold = 32,
        balance_rel_threshold = 1.0001,
        eviction_interval_secs = 60,
        max_tree_size = 2usize.pow(24),
        max_payload_size = 4 * 1024 * 1024,
        verbose = false
    ))]
    fn new(
        worker_urls: Vec<String>,
        policy: PolicyType,
        host: String,
        port: u16,
        worker_startup_timeout_secs: u64,
        worker_startup_check_interval: u64,
        cache_threshold: f32,
        balance_abs_threshold: usize,
        balance_rel_threshold: f32,
        eviction_interval_secs: u64,
        max_tree_size: usize,
        max_payload_size: usize,
        verbose: bool,
    ) -> PyResult<Self> {
        Ok(Router {
            host,
            port,
            worker_urls,
            policy,
            worker_startup_timeout_secs,
            worker_startup_check_interval,
            cache_threshold,
            balance_abs_threshold,
            balance_rel_threshold,
            eviction_interval_secs,
            max_tree_size,
            max_payload_size,
            verbose,
        })
    }
    
    #[new]
    #[cfg(feature = "k8s")]
    #[pyo3(signature = (
        worker_urls,
        policy = PolicyType::RoundRobin,
        host = String::from("127.0.0.1"),
        port = 3001,
        worker_startup_timeout_secs = 300,
        worker_startup_check_interval = 10,
        cache_threshold = 0.50,
        balance_abs_threshold = 32,
        balance_rel_threshold = 1.0001,
        eviction_interval_secs = 60,
        max_tree_size = 2usize.pow(24),
        max_payload_size = 4 * 1024 * 1024,
        verbose = false,
        enable_k8s_discovery = false,
        k8s_label_selector = String::from("sgl-role=llm-worker"),
        k8s_port_name = None,
        k8s_protocol = String::from("http"),
        k8s_worker_path = String::from("")
    ))]
    fn new_with_k8s(
        worker_urls: Vec<String>,
        policy: PolicyType,
        host: String,
        port: u16,
        worker_startup_timeout_secs: u64,
        worker_startup_check_interval: u64,
        cache_threshold: f32,
        balance_abs_threshold: usize,
        balance_rel_threshold: f32,
        eviction_interval_secs: u64,
        max_tree_size: usize,
        max_payload_size: usize,
        verbose: bool,
        enable_k8s_discovery: bool,
        k8s_label_selector: String,
        k8s_port_name: Option<String>,
        k8s_protocol: String,
        k8s_worker_path: String,
    ) -> PyResult<Self> {
        Ok(Router {
            host,
            port,
            worker_urls,
            policy,
            worker_startup_timeout_secs,
            worker_startup_check_interval,
            cache_threshold,
            balance_abs_threshold,
            balance_rel_threshold,
            eviction_interval_secs,
            max_tree_size,
            max_payload_size,
            verbose,
            enable_k8s_discovery,
            k8s_label_selector,
            k8s_port_name,
            k8s_protocol,
            k8s_worker_path,
        })
    }

    fn start(&self) -> PyResult<()> {
        let policy_config = match &self.policy {
            PolicyType::Random => router::PolicyConfig::RandomConfig {
                timeout_secs: self.worker_startup_timeout_secs,
                interval_secs: self.worker_startup_check_interval,
            },
            PolicyType::RoundRobin => router::PolicyConfig::RoundRobinConfig {
                timeout_secs: self.worker_startup_timeout_secs,
                interval_secs: self.worker_startup_check_interval,
            },
            PolicyType::CacheAware => router::PolicyConfig::CacheAwareConfig {
                timeout_secs: self.worker_startup_timeout_secs,
                interval_secs: self.worker_startup_check_interval,
                cache_threshold: self.cache_threshold,
                balance_abs_threshold: self.balance_abs_threshold,
                balance_rel_threshold: self.balance_rel_threshold,
                eviction_interval_secs: self.eviction_interval_secs,
                max_tree_size: self.max_tree_size,
            },
        };

        // Construct ServerConfig conditionally
        #[cfg(not(feature = "k8s"))]
        let server_config = server::ServerConfig {
            host: self.host.clone(),
            port: self.port,
            worker_urls: self.worker_urls.clone(),
            policy_config,
            verbose: self.verbose,
            max_payload_size: self.max_payload_size,
            enable_k8s_discovery: false, // Always false if feature not enabled
            k8s_discovery_config: None, // Always None if feature not enabled
        };
        #[cfg(feature = "k8s")]
        let server_config = server::ServerConfig {
            host: self.host.clone(),
            port: self.port,
            worker_urls: self.worker_urls.clone(),
            policy_config,
            verbose: self.verbose,
            max_payload_size: self.max_payload_size,
            enable_k8s_discovery: self.enable_k8s_discovery,
            k8s_discovery_config: if self.enable_k8s_discovery {
                Some(crate::k8s_discovery::K8sDiscoveryConfig {
                    label_selector: self.k8s_label_selector.clone(),
                    port_name: self.k8s_port_name.clone(),
                    protocol: self.k8s_protocol.clone(),
                    worker_path: self.k8s_worker_path.clone(),
                })
            } else {
                None
            },
        };

        actix_web::rt::System::new().block_on(async move {
            server::startup(server_config)
            .await
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
            Ok(())
        })
    }
}

#[pymodule]
fn sglang_router_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PolicyType>()?;
    m.add_class::<Router>()?;
    Ok(())
}
