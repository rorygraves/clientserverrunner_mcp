"""Log management for ClientServerRunner."""

import re
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import TextIO

from .models import LogEntry, LogRunInfo, SearchResult, ServerConfig
from .utils.logging import setup_logger

logger = setup_logger(__name__)


class LogManager:
    """Manages application log capture, storage, and search."""

    def __init__(self, server_config: ServerConfig) -> None:
        """Initialize the log manager.

        Args:
            server_config: Server configuration
        """
        self.server_config = server_config
        self.log_dir = server_config.data_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._active_files: dict[str, TextIO] = {}
        self._line_counts: dict[str, int] = {}

    def get_log_path(self, config_id: str, app_id: str, run_id: str = "current") -> Path:
        """Get the path for a log file.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier
            run_id: Run identifier (default "current")

        Returns:
            Path to log file
        """
        app_log_dir = self.log_dir / config_id / app_id
        return app_log_dir / f"{run_id}.log"

    def start_logging(self, config_id: str, app_id: str) -> TextIO:
        """Start logging for an application.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier

        Returns:
            File handle for logging
        """
        log_key = f"{config_id}/{app_id}"

        # Close existing log if any
        if log_key in self._active_files:
            self.stop_logging(config_id, app_id)

        # Archive previous current.log if it exists
        self._archive_current_log(config_id, app_id)

        # Create log directory
        log_path = self.get_log_path(config_id, app_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Open new log file
        log_file = open(log_path, "w", encoding="utf-8", buffering=1)  # Line buffered
        self._active_files[log_key] = log_file
        self._line_counts[log_key] = 0

        logger.info(f"Started logging for {config_id}/{app_id}")
        return log_file

    def stop_logging(self, config_id: str, app_id: str) -> None:
        """Stop logging for an application.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier
        """
        log_key = f"{config_id}/{app_id}"

        if log_key in self._active_files:
            self._active_files[log_key].close()
            del self._active_files[log_key]
            del self._line_counts[log_key]
            logger.info(f"Stopped logging for {config_id}/{app_id}")

    def write_log(
        self,
        config_id: str,
        app_id: str,
        content: str,
        stream: str = "stdout",
    ) -> None:
        """Write a log entry.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier
            content: Log content
            stream: Stream name (stdout or stderr)
        """
        log_key = f"{config_id}/{app_id}"

        if log_key not in self._active_files:
            # Log file not started, start it now
            self.start_logging(config_id, app_id)

        timestamp = datetime.now().isoformat(timespec="milliseconds")
        stream_prefix = "[stderr]" if stream == "stderr" else "[stdout]"
        line = f"{timestamp} {stream_prefix} {content}\n"

        self._active_files[log_key].write(line)
        self._line_counts[log_key] += 1

        # Check if log rotation needed
        self._check_log_rotation(config_id, app_id)

    def get_logs(
        self,
        config_id: str,
        app_id: str,
        lines: int = 100,
        run_id: str = "current",
    ) -> list[LogEntry]:
        """Get recent log entries.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier
            lines: Number of lines to retrieve
            run_id: Run identifier (default "current")

        Returns:
            List of log entries
        """
        log_path = self.get_log_path(config_id, app_id, run_id)

        if not log_path.exists():
            return []

        entries: deque[LogEntry] = deque(maxlen=lines)

        try:
            with open(log_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    entry = self._parse_log_line(line, line_num)
                    if entry:
                        entries.append(entry)
        except Exception as e:
            logger.error(f"Failed to read logs from {log_path}: {e}")

        return list(entries)

    def search_logs(
        self,
        config_id: str,
        app_id: str,
        query: str,
        max_results: int = 100,
        case_sensitive: bool = False,
        run_id: str = "current",
    ) -> list[SearchResult]:
        """Search logs for a pattern.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier
            query: Search query (regex pattern)
            max_results: Maximum number of results
            case_sensitive: Whether search is case sensitive
            run_id: Run identifier (default "current")

        Returns:
            List of search results
        """
        log_path = self.get_log_path(config_id, app_id, run_id)

        if not log_path.exists():
            return []

        results: list[SearchResult] = []
        flags = 0 if case_sensitive else re.IGNORECASE

        try:
            pattern = re.compile(query, flags)
        except re.error as e:
            logger.error(f"Invalid regex pattern '{query}': {e}")
            # Treat as literal string
            pattern = re.compile(re.escape(query), flags)

        try:
            with open(log_path, encoding="utf-8") as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                if pattern.search(line):
                    # Parse timestamp from line
                    timestamp = self._extract_timestamp(line)

                    # Get context
                    context_before = [lines[j].rstrip() for j in range(max(0, i - 2), i)]
                    context_after = [
                        lines[j].rstrip() for j in range(i + 1, min(len(lines), i + 3))
                    ]

                    result = SearchResult(
                        line_number=i + 1,
                        timestamp=timestamp,
                        content=line.rstrip(),
                        context_before=context_before,
                        context_after=context_after,
                        run_id=run_id,
                    )
                    results.append(result)

                    if len(results) >= max_results:
                        break

        except Exception as e:
            logger.error(f"Failed to search logs in {log_path}: {e}")

        return results

    def list_runs(self, config_id: str, app_id: str) -> list[LogRunInfo]:
        """List available log runs for an application.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier

        Returns:
            List of log run information
        """
        app_log_dir = self.log_dir / config_id / app_id

        if not app_log_dir.exists():
            return []

        runs: list[LogRunInfo] = []

        for log_file in app_log_dir.glob("*.log"):
            if log_file.stem == "current":
                continue

            try:
                # Parse timestamp from filename (YYYY-MM-DD-HH-MM-SS.log)
                timestamp_str = log_file.stem
                started_at = datetime.strptime(timestamp_str, "%Y-%m-%d-%H-%M-%S")

                run_info = LogRunInfo(
                    run_id=log_file.stem,
                    started_at=started_at,
                    ended_at=None,  # Could parse from last line
                    file_path=log_file,
                    file_size=log_file.stat().st_size,
                )
                runs.append(run_info)
            except Exception as e:
                logger.warning(f"Failed to parse log run info from {log_file}: {e}")
                continue

        # Sort by started_at (most recent first)
        runs.sort(key=lambda r: r.started_at, reverse=True)

        return runs

    def cleanup_old_runs(self, config_id: str, app_id: str) -> None:
        """Clean up old log runs based on retention policy.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier
        """
        runs = self.list_runs(config_id, app_id)

        # Keep only the most recent N runs
        if len(runs) > self.server_config.log_retention_runs:
            for run in runs[self.server_config.log_retention_runs :]:
                try:
                    run.file_path.unlink()
                    logger.info(f"Deleted old log run: {run.file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete old log run {run.file_path}: {e}")

    def _archive_current_log(self, config_id: str, app_id: str) -> None:
        """Archive the current log file.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier
        """
        current_log = self.get_log_path(config_id, app_id)

        if not current_log.exists() or current_log.stat().st_size == 0:
            return

        # Generate archive filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        archive_log = current_log.with_name(f"{timestamp}.log")

        try:
            current_log.rename(archive_log)
            logger.info(f"Archived log to {archive_log}")

            # Clean up old runs
            self.cleanup_old_runs(config_id, app_id)
        except Exception as e:
            logger.error(f"Failed to archive log {current_log}: {e}")

    def _check_log_rotation(self, config_id: str, app_id: str) -> None:
        """Check if log rotation is needed based on file size.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier
        """
        log_path = self.get_log_path(config_id, app_id)

        if not log_path.exists():
            return

        # Check file size
        size_mb = log_path.stat().st_size / (1024 * 1024)
        if size_mb >= self.server_config.log_max_size_mb:
            logger.warning(
                f"Log file {log_path} exceeds max size "
                f"({size_mb:.1f} MB), rotating..."
            )
            # Close current file
            log_key = f"{config_id}/{app_id}"
            if log_key in self._active_files:
                self._active_files[log_key].close()
                del self._active_files[log_key]

            # Archive and start new
            self._archive_current_log(config_id, app_id)
            self.start_logging(config_id, app_id)

    def _parse_log_line(self, line: str, line_number: int) -> LogEntry | None:
        """Parse a log line into a LogEntry.

        Args:
            line: Log line to parse
            line_number: Line number in file

        Returns:
            LogEntry or None if parsing fails
        """
        # Expected format: TIMESTAMP [stdout/stderr] CONTENT
        match = re.match(
            r"^(\S+)\s+\[(stdout|stderr)\]\s+(.*)$",
            line.rstrip(),
        )

        if not match:
            # Fallback for malformed lines
            return LogEntry(
                timestamp=datetime.now(),
                line_number=line_number,
                content=line.rstrip(),
                stream="stdout",
            )

        timestamp_str, stream, content = match.groups()

        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except ValueError:
            timestamp = datetime.now()

        return LogEntry(
            timestamp=timestamp,
            line_number=line_number,
            content=content,
            stream=stream,
        )

    def _extract_timestamp(self, line: str) -> datetime | None:
        """Extract timestamp from a log line.

        Args:
            line: Log line

        Returns:
            Timestamp or None if not found
        """
        match = re.match(r"^(\S+)", line)
        if match:
            try:
                return datetime.fromisoformat(match.group(1))
            except ValueError:
                pass
        return None
