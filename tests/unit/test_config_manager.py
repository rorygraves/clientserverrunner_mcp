"""Tests for configuration manager."""

from pathlib import Path

import pytest

from clientserverrunner.config_manager import ConfigManager


class TestConfigManager:
    """Tests for ConfigManager."""

    def test_create_configuration(self, config_manager: ConfigManager, temp_dir: Path):
        """Test creating a configuration."""
        config = config_manager.create_configuration(
            name="Test Config",
            description="A test configuration",
            applications=[
                {
                    "id": "app1",
                    "name": "App 1",
                    "app_type": "python",
                    "working_dir": str(temp_dir),
                    "command": "python server.py",
                }
            ],
        )

        assert config.name == "Test Config"
        assert config.description == "A test configuration"
        assert len(config.applications) == 1
        assert config.applications[0].id == "app1"

        # Verify file was created
        config_file = config_manager.config_dir / f"{config.id}.json"
        assert config_file.exists()

    def test_get_configuration(self, config_manager: ConfigManager, temp_dir: Path):
        """Test retrieving a configuration."""
        # Create a config
        created = config_manager.create_configuration(
            name="Test Config",
            applications=[
                {
                    "id": "app1",
                    "name": "App 1",
                    "app_type": "python",
                    "working_dir": str(temp_dir),
                    "command": "python server.py",
                }
            ],
        )

        # Retrieve it
        retrieved = config_manager.get_configuration(created.id)
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    def test_get_nonexistent_configuration(self, config_manager: ConfigManager):
        """Test retrieving a non-existent configuration raises error."""
        with pytest.raises(KeyError, match="not found"):
            config_manager.get_configuration("nonexistent")

    def test_list_configurations(self, config_manager: ConfigManager, temp_dir: Path):
        """Test listing configurations."""
        # Create multiple configs
        config1 = config_manager.create_configuration(
            name="Config 1",
            applications=[
                {
                    "id": "app1",
                    "name": "App 1",
                    "app_type": "python",
                    "working_dir": str(temp_dir),
                    "command": "python server.py",
                }
            ],
        )

        config2 = config_manager.create_configuration(
            name="Config 2",
            applications=[
                {
                    "id": "app1",
                    "name": "App 1",
                    "app_type": "npm",
                    "working_dir": str(temp_dir),
                    "command": "npm start",
                }
            ],
        )

        # List them
        summaries = config_manager.list_configurations()
        assert len(summaries) == 2
        ids = [s.id for s in summaries]
        assert config1.id in ids
        assert config2.id in ids

    def test_update_configuration(self, config_manager: ConfigManager, temp_dir: Path):
        """Test updating a configuration."""
        # Create a config
        config = config_manager.create_configuration(
            name="Original Name",
            applications=[
                {
                    "id": "app1",
                    "name": "App 1",
                    "app_type": "python",
                    "working_dir": str(temp_dir),
                    "command": "python server.py",
                }
            ],
        )

        # Update it
        updated = config_manager.update_configuration(
            config.id, {"name": "Updated Name", "description": "New description"}
        )

        assert updated.name == "Updated Name"
        assert updated.description == "New description"
        assert updated.updated_at > config.updated_at

    def test_delete_configuration(self, config_manager: ConfigManager, temp_dir: Path):
        """Test deleting a configuration."""
        # Create a config
        config = config_manager.create_configuration(
            name="Test Config",
            applications=[
                {
                    "id": "app1",
                    "name": "App 1",
                    "app_type": "python",
                    "working_dir": str(temp_dir),
                    "command": "python server.py",
                }
            ],
        )

        config_file = config_manager.config_dir / f"{config.id}.json"
        assert config_file.exists()

        # Delete it
        config_manager.delete_configuration(config.id)

        # Verify it's gone
        assert not config_file.exists()
        with pytest.raises(KeyError):
            config_manager.get_configuration(config.id)

    def test_invalid_configuration(self, config_manager: ConfigManager, temp_dir: Path):
        """Test that invalid configurations are rejected."""
        with pytest.raises(ValueError):
            config_manager.create_configuration(
                name="Invalid Config",
                applications=[
                    {
                        "id": "app1",
                        "name": "App 1",
                        "app_type": "invalid_type",
                        "working_dir": str(temp_dir),
                        "command": "python server.py",
                    }
                ],
            )
