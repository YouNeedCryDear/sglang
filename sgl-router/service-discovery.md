Here's a plan based on an **integrated approach with optional compilation via Cargo features**:

## Overall Approach:

We will create a new Rust module responsible for interacting with the Kubernetes API. This module, along with its dependencies, will be conditionally compiled based on a Cargo feature flag (e.g., `k8s`). When the feature is enabled, the module runs as a background task, watching for Kubernetes Endpoints resources that match specific labels identifying the LLM worker deployments. When workers are added or removed, this task will extract their URLs and communicate with the main Router instance via internal channels to call the existing `add_worker` and `remove_worker` methods.

## Kubernetes Discovery Method:

Tool: We'll use the `kube-rs` Rust crate to interact with the Kubernetes API. This is the standard and most robust library for this purpose in Rust.

Mechanism: We will watch Kubernetes Endpoints resources. Endpoints directly list the IP addresses and ports of ready pods backing a Service.

Identification: Worker deployments (or rather, their corresponding Service objects) will need a specific label (e.g., `sgl-role: llm-worker`) so the router can identify them. The Endpoints resource automatically inherits the labels of its corresponding Service.

## Implementation Details:

Cargo Feature: Define a new feature, e.g., `k8s`, in `sgl-router/Cargo.toml`.

Optional Dependencies: Add `kube-rs`, `k8s-openapi`, `futures`, `thiserror`, and `anyhow` to `sgl-router/Cargo.toml` as *optional* dependencies, enabling them only when the `k8s` feature is active.

Conditional Compilation: Use `#[cfg(feature = "k8s")]` annotations to conditionally compile:

- The new module `src/k8s_discovery.rs`.
- The `mod k8s_discovery;` declaration in `src/lib.rs`.
- Any code sections in `src/server.rs` and `src/lib.rs` that initialize, configure, or interact with the Kubernetes discovery task and its configuration.

New Module (`src/k8s_discovery.rs`): Create this file containing the discovery logic (only compiled if `k8s` feature is enabled).

- Define an asynchronous function (e.g., `run_k8s_discovery_task`) that sets up the watcher and returns a channel receiver.
- Initialize a `kube::Client` within the task.
- Use `kube::Api<Endpoints>` to interact with Endpoints resources.
- Create a watcher filtering by the label selector.
- Loop through events (Applied, Deleted, Modified) and send `DiscoveryCommand` messages via a channel.
- Include robust error handling and logging.

Router Integration (`src/server.rs`, `src/lib.rs`): Conditionally compiled `#[cfg(feature = "k8s")]`:

- Communication: Use `tokio::sync::mpsc` channels. The discovery task holds the `Sender`, and the main server setup holds the `Receiver`.
- Spawning: In `server::startup`, conditionally spawn the `run_k8s_discovery_task` function as a separate Tokio task if the feature is enabled *and* runtime configuration requests it (e.g., via `enable_k8s_discovery` flag).
- Receiving: The spawned task receives `DiscoveryCommand`s and calls the Router's `add_worker` and `remove_worker` methods.

Configuration: Add runtime configuration options (e.g., `enable_k8s_discovery`, `k8s_label_selector`, `k8s_port_name`) to the Python `Router` class constructor. These are only relevant/used if the `k8s` feature was enabled during compilation.

## Kubernetes Setup (Required only if using the `k8s` feature):

Router Deployment:

- Needs a ServiceAccount.
- Requires a Role (or ClusterRole) granting `get`, `list`, and `watch` permissions on `endpoints` resources in the namespace(s) where workers reside.
- A RoleBinding (or ClusterRoleBinding) to bind the Role to the ServiceAccount.

Worker Deployments:
- Must have a Service pointing to them.
- This Service must have the label that the router uses for discovery (e.g., `sgl-role: llm-worker`).
- Ensure the Service correctly specifies the port name or number that the router expects.

## Actions:

1. Define the `k8s` feature and add optional dependencies in `Cargo.toml`.
2. Create the `src/k8s_discovery.rs` file with the watcher logic, wrapped in `#[cfg(feature = "k8s")]` where necessary internally or applied to the whole module.
3. Add the conditional module declaration `#[cfg(feature = "k8s")] mod k8s_discovery;` to `src/lib.rs`.
4. Integrate the channel communication, conditional task spawning, and configuration handling into `src/server.rs` and `src/lib.rs` using `#[cfg(feature = "k8s")]`.
5. Build with `cargo build --features k8s` to include the discovery functionality, or `cargo build` to exclude it.