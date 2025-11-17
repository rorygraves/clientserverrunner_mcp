"""Port management for ClientServerRunner."""

import socket

from .utils.logging import setup_logger

logger = setup_logger(__name__)


class PortManager:
    """Manages port allocation and tracking for applications."""

    def __init__(self) -> None:
        """Initialize the port manager."""
        self._allocated_ports: dict[str, int] = {}

    def allocate_port(self, app_id: str, requested_port: int | None = None) -> int:
        """Allocate a port for an application.

        Args:
            app_id: Application identifier
            requested_port: Specific port requested, or None for dynamic

        Returns:
            Allocated port number

        Raises:
            ValueError: If requested port is already allocated
            OSError: If port cannot be allocated
        """
        if requested_port is not None and requested_port != 0:
            # Check if port is already allocated
            if requested_port in self._allocated_ports.values():
                raise ValueError(
                    f"Port {requested_port} is already allocated to another application"
                )

            # Validate port is available
            if not self._is_port_available(requested_port):
                raise OSError(f"Port {requested_port} is already in use")

            self._allocated_ports[app_id] = requested_port
            logger.info(f"Allocated fixed port {requested_port} to app '{app_id}'")
            return requested_port

        # Dynamic port allocation
        port = self._find_available_port()
        self._allocated_ports[app_id] = port
        logger.info(f"Allocated dynamic port {port} to app '{app_id}'")
        return port

    def release_port(self, app_id: str) -> None:
        """Release a port allocation.

        Args:
            app_id: Application identifier
        """
        if app_id in self._allocated_ports:
            port = self._allocated_ports.pop(app_id)
            logger.info(f"Released port {port} from app '{app_id}'")

    def get_allocated_port(self, app_id: str) -> int | None:
        """Get the port allocated to an application.

        Args:
            app_id: Application identifier

        Returns:
            Allocated port or None if not allocated
        """
        return self._allocated_ports.get(app_id)

    def is_port_allocated(self, port: int) -> bool:
        """Check if a port is currently allocated.

        Args:
            port: Port number to check

        Returns:
            True if port is allocated
        """
        return port in self._allocated_ports.values()

    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available for binding.

        Args:
            port: Port number to check

        Returns:
            True if port is available
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False

    def _find_available_port(self) -> int:
        """Find an available port using OS allocation.

        Returns:
            Available port number

        Raises:
            OSError: If no port can be allocated
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("127.0.0.1", 0))
                _, port = sock.getsockname()
            return int(port)
        except OSError as e:
            raise OSError(f"Failed to allocate dynamic port: {e}") from e
