"""Configuration management for ClientServerRunner."""

import json
import uuid
from datetime import datetime
from typing import Any

from .models import Configuration, ConfigurationSummary, ServerConfig
from .utils.logging import setup_logger

logger = setup_logger(__name__)


class ConfigManager:
    """Manages configuration storage and retrieval."""

    def __init__(self, server_config: ServerConfig) -> None:
        """Initialize the configuration manager.

        Args:
            server_config: Server configuration
        """
        self.server_config = server_config
        self.config_dir = server_config.data_dir / "configurations"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Configuration] = {}

    def create_configuration(
        self,
        name: str,
        applications: list[dict[str, Any]],
        description: str | None = None,
    ) -> Configuration:
        """Create a new configuration.

        Args:
            name: Configuration name
            applications: List of application definitions
            description: Optional description

        Returns:
            Created configuration

        Raises:
            ValueError: If configuration is invalid
        """
        config_id = str(uuid.uuid4())

        try:
            config = Configuration(
                id=config_id,
                name=name,
                description=description,
                applications=applications,  # type: ignore[arg-type]
            )
        except Exception as e:
            logger.error(f"Failed to create configuration: {e}")
            raise ValueError(f"Invalid configuration: {e}") from e

        # Save to disk
        self._save_configuration(config)

        # Cache it
        self._cache[config_id] = config

        logger.info(f"Created configuration '{name}' with ID {config_id}")
        return config

    def get_configuration(self, config_id: str) -> Configuration:
        """Get a configuration by ID.

        Args:
            config_id: Configuration identifier

        Returns:
            Configuration instance

        Raises:
            KeyError: If configuration not found
        """
        # Check cache first
        if config_id in self._cache:
            return self._cache[config_id]

        # Load from disk
        config_file = self.config_dir / f"{config_id}.json"
        if not config_file.exists():
            raise KeyError(f"Configuration '{config_id}' not found")

        try:
            with open(config_file, encoding="utf-8") as f:
                data = json.load(f)
            config = Configuration(**data)
            self._cache[config_id] = config
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration {config_id}: {e}")
            raise KeyError(f"Failed to load configuration '{config_id}': {e}") from e

    def list_configurations(self) -> list[ConfigurationSummary]:
        """List all configurations.

        Returns:
            List of configuration summaries
        """
        summaries = []

        for config_file in self.config_dir.glob("*.json"):
            try:
                with open(config_file, encoding="utf-8") as f:
                    data = json.load(f)

                summary = ConfigurationSummary(
                    id=data["id"],
                    name=data["name"],
                    description=data.get("description"),
                    app_count=len(data.get("applications", [])),
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                )
                summaries.append(summary)
            except Exception as e:
                logger.warning(f"Failed to load configuration from {config_file}: {e}")
                continue

        # Sort by updated_at (most recent first)
        summaries.sort(key=lambda s: s.updated_at, reverse=True)
        return summaries

    def update_configuration(
        self,
        config_id: str,
        updates: dict[str, Any],
    ) -> Configuration:
        """Update a configuration.

        Args:
            config_id: Configuration identifier
            updates: Dictionary of updates to apply

        Returns:
            Updated configuration

        Raises:
            KeyError: If configuration not found
            ValueError: If update is invalid
        """
        config = self.get_configuration(config_id)

        # Create a dict from the current config
        config_dict = config.model_dump()

        # Apply updates
        for key, value in updates.items():
            if key in ["id", "created_at"]:
                # Don't allow updating these fields
                continue
            config_dict[key] = value

        # Update the updated_at timestamp
        config_dict["updated_at"] = datetime.now()

        # Validate the updated configuration
        try:
            updated_config = Configuration(**config_dict)
        except Exception as e:
            logger.error(f"Invalid configuration update: {e}")
            raise ValueError(f"Invalid configuration update: {e}") from e

        # Save to disk
        self._save_configuration(updated_config)

        # Update cache
        self._cache[config_id] = updated_config

        logger.info(f"Updated configuration {config_id}")
        return updated_config

    def delete_configuration(self, config_id: str) -> None:
        """Delete a configuration.

        Args:
            config_id: Configuration identifier

        Raises:
            KeyError: If configuration not found
        """
        config_file = self.config_dir / f"{config_id}.json"
        if not config_file.exists():
            raise KeyError(f"Configuration '{config_id}' not found")

        # Remove from cache
        self._cache.pop(config_id, None)

        # Delete file
        config_file.unlink()

        logger.info(f"Deleted configuration {config_id}")

    def _save_configuration(self, config: Configuration) -> None:
        """Save configuration to disk using atomic write.

        Args:
            config: Configuration to save
        """
        config_file = self.config_dir / f"{config.id}.json"
        temp_file = config_file.with_suffix(".tmp")

        try:
            # Write to temp file
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(
                    config.model_dump(mode="json"),
                    f,
                    indent=2,
                    default=str,
                )

            # Atomic rename
            temp_file.replace(config_file)
        except Exception as e:
            # Clean up temp file on error
            if temp_file.exists():
                temp_file.unlink()
            raise RuntimeError(f"Failed to save configuration: {e}") from e
