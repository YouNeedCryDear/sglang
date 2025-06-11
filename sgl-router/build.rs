// /home/archeng/sglang/sgl-router/build.rs
fn main() -> Result<(), Box<dyn std::error::Error>> {
    std::fs::create_dir_all("src/grpc_generated")?;
    tonic_build::configure()
        .build_server(false) // We only need the client in the router
        .out_dir("src/grpc_generated") // Output directory for generated Rust files
        .compile(
            &["../protos/sglang_engine.proto"], // Path to .proto file
            &["../protos"],                     // Include path for proto imports
        )?;
    Ok(())
}
