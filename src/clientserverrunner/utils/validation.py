"""Validation utilities for ClientServerRunner."""

import shutil
from pathlib import Path


def validate_working_dir(path: Path) -> tuple[bool, str | None]:
    """Validate that a working directory exists and is accessible.

    Args:
        path: Path to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path.exists():
        return False, f"Directory does not exist: {path}"

    if not path.is_dir():
        return False, f"Path is not a directory: {path}"

    if not path.is_absolute():
        return False, f"Path must be absolute: {path}"

    # Check if we can access the directory
    try:
        list(path.iterdir())
    except PermissionError:
        return False, f"Permission denied accessing directory: {path}"
    except Exception as e:
        return False, f"Error accessing directory {path}: {e}"

    return True, None


def validate_command_available(command: str) -> tuple[bool, str | None]:
    """Validate that a command is available in PATH.

    Args:
        command: Command to check (e.g., 'python', 'npm', 'sbt')

    Returns:
        Tuple of (is_available, error_message)
    """
    # Get the base command (first word)
    base_command = command.split()[0] if command else ""

    if not base_command:
        return False, "Empty command"

    # Check if command is available
    if shutil.which(base_command) is None:
        return (
            False,
            f"Command '{base_command}' not found in PATH. Please install it first.",
        )

    return True, None


def validate_port_available(port: int, host: str = "127.0.0.1") -> tuple[bool, str | None]:
    """Validate that a port is available for binding.

    Args:
        port: Port number to check
        host: Host to check on (default localhost)

    Returns:
        Tuple of (is_available, error_message)
    """
    import socket

    if port == 0:
        # Port 0 means dynamic allocation, always valid
        return True, None

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
        return True, None
    except OSError as e:
        return False, f"Port {port} is not available: {e}"
