"""Tests for port manager."""

import pytest

from clientserverrunner.port_manager import PortManager


class TestPortManager:
    """Tests for PortManager."""

    def test_allocate_fixed_port(self, port_manager: PortManager):
        """Test allocating a fixed port."""
        port = port_manager.allocate_port("app1", 8888)
        assert port == 8888
        assert port_manager.get_allocated_port("app1") == 8888

        port_manager.release_port("app1")

    def test_allocate_dynamic_port(self, port_manager: PortManager):
        """Test allocating a dynamic port."""
        port = port_manager.allocate_port("app1", None)
        assert port > 0
        assert port <= 65535
        assert port_manager.get_allocated_port("app1") == port

        port_manager.release_port("app1")

    def test_duplicate_port_allocation(self, port_manager: PortManager):
        """Test that allocating same port twice fails."""
        port_manager.allocate_port("app1", 8888)

        with pytest.raises(ValueError, match="already allocated"):
            port_manager.allocate_port("app2", 8888)

        port_manager.release_port("app1")

    def test_release_port(self, port_manager: PortManager):
        """Test releasing a port."""
        port = port_manager.allocate_port("app1", 8888)
        assert port_manager.is_port_allocated(8888)

        port_manager.release_port("app1")
        assert not port_manager.is_port_allocated(8888)
        assert port_manager.get_allocated_port("app1") is None

    def test_multiple_dynamic_ports(self, port_manager: PortManager):
        """Test allocating multiple dynamic ports."""
        port1 = port_manager.allocate_port("app1", None)
        port2 = port_manager.allocate_port("app2", None)
        port3 = port_manager.allocate_port("app3", None)

        # All ports should be different
        assert port1 != port2
        assert port1 != port3
        assert port2 != port3

        # All should be allocated
        assert port_manager.is_port_allocated(port1)
        assert port_manager.is_port_allocated(port2)
        assert port_manager.is_port_allocated(port3)

        # Clean up
        port_manager.release_port("app1")
        port_manager.release_port("app2")
        port_manager.release_port("app3")
