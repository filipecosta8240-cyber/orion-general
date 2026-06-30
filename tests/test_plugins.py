"""Tests for plugin system"""
import pytest
from orion.plugin_system import PluginBase, PluginManifest, PluginManager, PluginState


class TestPluginBase:
    def test_plugin_manifest(self):
        manifest = PluginManifest(
            id="test", name="Test Plugin", version="1.0",
            description="A test plugin"
        )
        assert manifest.id == "test"
        assert manifest.name == "Test Plugin"


class TestPluginManager:
    def test_list_plugins_no_plugins(self):
        manager = PluginManager()
        plugins = manager.list_plugins()
        assert isinstance(plugins, list)

    def test_stop_all_empty(self):
        manager = PluginManager()
        count = manager.stop_all()
        assert count == 0
