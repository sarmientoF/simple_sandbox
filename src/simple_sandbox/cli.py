"""CLI entry point for simple-sandbox server."""

import argparse


def main():
    """Main entry point for the sandbox-server command."""
    parser = argparse.ArgumentParser(
        description="LLM Python Code Sandbox Server",
        prog="sandbox-server"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)"
    )

    args = parser.parse_args()

    # Import here to avoid circular imports and speed up --help
    from .server import run_server
    run_server(args.host, args.port)


if __name__ == "__main__":
    main()
