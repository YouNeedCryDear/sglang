# python/sglang/srt/grpc_server.py
import argparse
import asyncio
import json
import logging
from concurrent import futures

import grpc

from sglang.srt.entrypoints.engine import Engine

# Assuming grpc_generated is in the same directory or accessible via PYTHONPATH
from sglang.srt.entrypoints.grpc_generated import (
    sglang_engine_pb2,
    sglang_engine_pb2_grpc,
)
from sglang.srt.server_args import ServerArgs
from sglang.srt.utils import configure_logger

logger = logging.getLogger(__name__)


class SglangEngineServicerImpl(sglang_engine_pb2_grpc.SglangEngineServiceServicer):
    def __init__(self, engine: Engine):
        self.engine = engine
        self.loop = asyncio.get_event_loop()

    async def Generate(self, request: sglang_engine_pb2.GenerateRequest, context):
        try:
            request_dict = json.loads(request.request_json_body)
            # Ensure stream is False for non-streaming endpoint
            request_dict["stream"] = False

            # Extract arguments for async_generate, filtering out None
            generate_args = {k: v for k, v in request_dict.items() if v is not None}

            response_data = await self.engine.async_generate(**generate_args)
            response_json_body = json.dumps(response_data)
            return sglang_engine_pb2.GenerateResponse(
                response_json_body=response_json_body, status_code=200
            )
        except Exception as e:
            logger.error(f"Error in Generate RPC: {e}", exc_info=True)
            # Consider mapping specific exceptions to gRPC status codes
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

    async def GenerateStream(self, request: sglang_engine_pb2.GenerateRequest, context):
        try:
            request_dict = json.loads(request.request_json_body)
            # Ensure stream is True for streaming endpoint
            request_dict["stream"] = True

            # Extract arguments for async_generate, filtering out None
            generate_args = {k: v for k, v in request_dict.items() if v is not None}

            async for chunk in self.engine.async_generate(**generate_args):
                json_chunk = json.dumps(chunk)
                yield sglang_engine_pb2.TokenUpdate(json_chunk=json_chunk)

        except Exception as e:
            logger.error(f"Error in GenerateStream RPC: {e}", exc_info=True)
            # Inform the client about the error before closing the stream
            # gRPC stream errors are typically handled by the client seeing the stream end prematurely
            # or by sending a final message with error info if the protocol supports it.
            # For now, we log and the client will see the stream terminate.
            # Alternatively, context.abort can be used if an error occurs before streaming starts.
            # if not context.is_active():
            #    return
            # If error happens before any yield, we can abort
            # Consider how to signal errors during an active stream if needed by client.
            # For now, relying on stream termination and logs.
            pass  # Error logged, stream will terminate


async def serve(args):
    # Initialize ServerArgs for the SGLang Engine
    # We need to map cmd line args to ServerArgs fields
    server_args_dict = {
        key: getattr(args, key)
        for key in ServerArgs.__dataclass_fields__.keys()
        if hasattr(args, key) and getattr(args, key) is not None
    }

    # For AsyncServerArgs, if not provided, use defaults from ServerArgs
    async_server_args_dict = {
        key: getattr(args, key)
        for key in AsyncServerArgs.__dataclass_fields__.keys()
        if hasattr(args, key) and getattr(args, key) is not None
    }
    if not async_server_args_dict:
        async_server_args_dict = ServerArgs().async_server_args  # Use defaults
    else:
        async_server_args_dict = AsyncServerArgs(**async_server_args_dict)

    server_args = ServerArgs(
        async_server_args=async_server_args_dict, **server_args_dict
    )

    # Configure logging for the engine
    configure_logger(
        server_args.log_level, server_args.log_file, server_args.log_level_http
    )

    engine = Engine(server_args=server_args)

    grpc_server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=args.grpc_max_workers)
    )
    sglang_engine_pb2_grpc.add_SglangEngineServiceServicer_to_server(
        SglangEngineServicerImpl(engine), grpc_server
    )

    listen_addr = f"{args.host}:{args.port}"
    grpc_server.add_insecure_port(listen_addr)

    logger.info(f"Starting SGLang gRPC server on {listen_addr}")
    await grpc_server.start()

    try:
        await grpc_server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("SGLang gRPC server shutting down...")
        await grpc_server.stop(0)
    finally:
        engine.shutdown()  # Ensure engine subprocesses are cleaned up


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SGLang gRPC Engine Server")

    # gRPC server specific arguments
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to bind the gRPC server to"
    )
    parser.add_argument(
        "--port", type=int, default=30000, help="Port for the gRPC server"
    )  # Default gRPC port for sglang worker
    parser.add_argument(
        "--grpc-max-workers",
        type=int,
        default=10,
        help="Max workers for gRPC thread pool",
    )

    # SGLang Engine arguments (subset, add more as needed or find a way to pass them all)
    # These should align with ServerArgs fields
    parser.add_argument(
        "--model-path", type=str, required=True, help="Path to the model weights"
    )
    parser.add_argument(
        "--tokenizer-path",
        type=str,
        default=None,
        help="Path to the tokenizer, defaults to model_path",
    )
    parser.add_argument(
        "--model-mode",
        type=str,
        default="default",
        choices=["default", "longlora", "longchat"],
        help="Model mode",
    )
    parser.add_argument(
        "--mem-fraction-static",
        type=float,
        default=None,
        help="Static memory fraction for the model",
    )
    parser.add_argument(
        "--tp-size", type=int, default=1, help="Tensor parallelism size"
    )
    parser.add_argument("--log-level", type=str, default="info", help="Logging level")
    parser.add_argument("--log-file", type=str, default=None, help="Log file path")
    parser.add_argument(
        "--log-level-http", type=str, default="warning", help="HTTP server log level"
    )
    # Add other ServerArgs fields as needed, e.g.:
    # parser.add_argument("--tokenizer-mode", type=str, default="auto", help="Tokenizer mode")
    # parser.add_argument("--chat-template", type=str, default=None, help="Chat template file")
    # ... and so on for all relevant ServerArgs

    args = parser.parse_args()

    asyncio.run(serve(args))
