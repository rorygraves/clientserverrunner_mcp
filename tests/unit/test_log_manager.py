"""Tests for log manager."""

from clientserverrunner.log_manager import LogManager


class TestLogManager:
    """Tests for LogManager."""

    def test_start_logging(self, log_manager: LogManager):
        """Test starting log capture."""
        log_file = log_manager.start_logging("config1", "app1")
        assert log_file is not None
        assert not log_file.closed

        log_manager.stop_logging("config1", "app1")

    def test_write_log(self, log_manager: LogManager):
        """Test writing log entries."""
        log_manager.start_logging("config1", "app1")
        log_manager.write_log("config1", "app1", "Test log entry", "stdout")
        log_manager.write_log("config1", "app1", "Error log entry", "stderr")
        log_manager.stop_logging("config1", "app1")

        # Verify logs were written
        logs = log_manager.get_logs("config1", "app1", lines=10)
        assert len(logs) == 2
        assert "Test log entry" in logs[0].content
        assert "Error log entry" in logs[1].content

    def test_get_logs(self, log_manager: LogManager):
        """Test retrieving logs."""
        log_manager.start_logging("config1", "app1")

        # Write multiple log entries
        for i in range(10):
            log_manager.write_log("config1", "app1", f"Log entry {i}", "stdout")

        log_manager.stop_logging("config1", "app1")

        # Get last 5 logs
        logs = log_manager.get_logs("config1", "app1", lines=5)
        assert len(logs) == 5
        assert "Log entry 9" in logs[4].content

    def test_search_logs(self, log_manager: LogManager):
        """Test searching logs."""
        log_manager.start_logging("config1", "app1")

        # Write logs with some matching pattern
        log_manager.write_log("config1", "app1", "Normal log entry", "stdout")
        log_manager.write_log("config1", "app1", "ERROR: Something failed", "stderr")
        log_manager.write_log("config1", "app1", "Another normal entry", "stdout")
        log_manager.write_log("config1", "app1", "ERROR: Another error", "stderr")

        log_manager.stop_logging("config1", "app1")

        # Search for errors
        results = log_manager.search_logs("config1", "app1", "ERROR", case_sensitive=True)
        assert len(results) == 2
        assert "ERROR" in results[0].content
        assert "ERROR" in results[1].content

    def test_list_runs(self, log_manager: LogManager):
        """Test listing log runs."""
        # Create and archive logs
        log_manager.start_logging("config1", "app1")
        log_manager.write_log("config1", "app1", "First run", "stdout")
        log_manager.stop_logging("config1", "app1")

        # Start again (should archive previous)
        log_manager.start_logging("config1", "app1")
        log_manager.write_log("config1", "app1", "Second run", "stdout")
        log_manager.stop_logging("config1", "app1")

        # List runs
        runs = log_manager.list_runs("config1", "app1")
        assert len(runs) >= 1  # At least one archived run

    def test_get_nonexistent_logs(self, log_manager: LogManager):
        """Test getting logs for non-existent app."""
        logs = log_manager.get_logs("nonexistent", "app1")
        assert len(logs) == 0
