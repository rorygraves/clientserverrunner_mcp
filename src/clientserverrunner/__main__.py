"""Entry point for ClientServerRunner MCP server."""

import argparse
import sys

from .server import initialize_managers, mcp
from .utils.logging import setup_logger

logger = setup_logger(__name__)


def main() -> None:
    """Main entry point for the MCP server."""
    parser = argparse.ArgumentParser(
        description="ClientServerRunner MCP Server - Manage multi-application configurations"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Data directory for configurations and logs (default: ~/.clientserverrunner)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Set log level
    import logging

    log_level = getattr(logging, args.log_level)
    logger.setLevel(log_level)

    # Initialize managers
    try:
        initialize_managers(args.data_dir)
    except Exception as e:
        logger.error(f"Failed to initialize server: {e}")
        sys.exit(1)

    # Start MCP server
    logger.info("Starting ClientServerRunner MCP server...")
    logger.info("Use with Claude Code or other MCP clients. " "Add to MCP settings configuration.")

    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
