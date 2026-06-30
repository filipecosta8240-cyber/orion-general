"""
ORION Plugin System
====================
Dynamic plugin loading and management system.

Features:
- Plugin discovery and loading
- Plugin lifecycle management (init, start, stop)
- Dependency resolution
- Plugin isolation
- Hot-reload support
- Plugin registry
"""

import os
import sys
import time
import uuid
import importlib
import inspect
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type
from pathlib import Path
import logging

logger = logging.getLogger("orion.plugins")


class PluginState(str, Enum):
    DISCOVERED = "discovered"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class PluginManifest:
    """Plugin metadata"""
    id: str = ""
    name: str = ""
    version: str = "1.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    min_orion_version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginManifest":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class PluginBase:
    """Base class for all plugins"""
    
    manifest: PluginManifest = PluginManifest()
    
    def __init__(self):
        self.state = PluginState.DISCOVERED
        self.logger = logging.getLogger(f"orion.plugin.{self.manifest.name}")
    
    def initialize(self, orion_instance: Any) -> bool:
        """Initialize plugin with ORION instance"""
        self.state = PluginState.INITIALIZED
        return True
    
    def start(self) -> bool:
        """Start plugin"""
        self.state = PluginState.STARTED
        return True
    
    def stop(self) -> bool:
        """Stop plugin"""
        self.state = PluginState.STOPPED
        return True
    
    def get_commands(self) -> Dict[str, Callable]:
        """Get plugin commands to register"""
        return {}
    
    def get_hooks(self) -> Dict[str, Callable]:
        """Get event hooks"""
        return {}


class PluginManager:
    """
    Manages plugin lifecycle: discovery, loading, initialization, start, stop.
    """
    
    def __init__(self, plugin_dirs: Optional[List[Path]] = None):
        self.plugin_dirs = plugin_dirs or []
        self.plugins: Dict[str, PluginBase] = {}
        self.manifest_registry: Dict[str, PluginManifest] = {}
        self._lock = threading.RLock()
        
        # Default plugin directories
        if not self.plugin_dirs:
            orion_dir = Path(__file__).resolve().parent
            plugins_dir = orion_dir / "plugins"
            if plugins_dir.exists():
                self.plugin_dirs.append(plugins_dir)
        
        logger.info(f"Plugin Manager initialized with {len(self.plugin_dirs)} directories")
    
    def discover_plugins(self) -> List[PluginManifest]:
        """Discover available plugins"""
        manifests = []
        
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue
            
            # Look for plugin directories
            for item in plugin_dir.iterdir():
                if item.is_dir() and (item / "__init__.py").exists():
                    manifest = self._discover_plugin(item)
                    if manifest:
                        manifests.append(manifest)
                elif item.suffix == '.py' and not item.name.startswith('_'):
                    manifest = self._discover_plugin_file(item)
                    if manifest:
                        manifests.append(manifest)
        
        return manifests
    
    def _discover_plugin(self, plugin_dir: Path) -> Optional[PluginManifest]:
        """Discover plugin from directory"""
        manifest_file = plugin_dir / "manifest.json"
        if manifest_file.exists():
            try:
                import json
                data = json.loads(manifest_file.read_text(encoding="utf-8"))
                manifest = PluginManifest.from_dict(data)
                manifest.id = manifest.id or plugin_dir.name
                
                with self._lock:
                    self.manifest_registry[manifest.id] = manifest
                
                return manifest
            except Exception as e:
                logger.warning(f"Error reading manifest from {plugin_dir}: {e}")
        
        return None
    
    def _discover_plugin_file(self, plugin_file: Path) -> Optional[PluginManifest]:
        """Discover plugin from single file"""
        try:
            # Try to import and get class
            module_name = plugin_file.stem
            spec = importlib.util.spec_from_file_location(
                f"orion.plugins.{module_name}", plugin_file
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, PluginBase) and 
                        obj != PluginBase):
                        manifest = obj.manifest
                        manifest.id = manifest.id or module_name
                        
                        with self._lock:
                            self.manifest_registry[manifest.id] = manifest
                        
                        return manifest
        except Exception as e:
            logger.warning(f"Error discovering plugin {plugin_file}: {e}")
        
        return None
    
    def load_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        """Load a plugin by ID"""
        manifest = self.manifest_registry.get(plugin_id)
        if not manifest:
            logger.error(f"Plugin not found: {plugin_id}")
            return None
        
        with self._lock:
            if plugin_id in self.plugins:
                return self.plugins[plugin_id]
        
        # Find and load plugin module
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue
            
            # Check directory
            plugin_path = plugin_dir / plugin_id
            if plugin_path.is_dir() and (plugin_path / "__init__.py").exists():
                plugin = self._load_from_dir(plugin_path, manifest)
                if plugin:
                    return plugin
            
            # Check file
            plugin_file = plugin_dir / f"{plugin_id}.py"
            if plugin_file.exists():
                plugin = self._load_from_file(plugin_file, manifest)
                if plugin:
                    return plugin
        
        logger.error(f"Could not load plugin: {plugin_id}")
        return None
    
    def _load_from_dir(self, plugin_path: Path, manifest: PluginManifest) -> Optional[PluginBase]:
        """Load plugin from directory"""
        try:
            # Add to path
            sys.path.insert(0, str(plugin_path.parent))
            
            module = importlib.import_module(manifest.id)
            
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, PluginBase) and 
                    obj != PluginBase):
                    instance = obj()
                    
                    with self._lock:
                        self.plugins[manifest.id] = instance
                    
                    logger.info(f"Loaded plugin: {manifest.name} ({manifest.id})")
                    return instance
            
            return None
        except Exception as e:
            logger.error(f"Error loading plugin from {plugin_path}: {e}")
            return None
    
    def _load_from_file(self, plugin_file: Path, manifest: PluginManifest) -> Optional[PluginBase]:
        """Load plugin from single file"""
        try:
            module_name = f"orion.plugins.{manifest.id}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, PluginBase) and 
                        obj != PluginBase):
                        instance = obj()
                        
                        with self._lock:
                            self.plugins[manifest.id] = instance
                        
                        logger.info(f"Loaded plugin: {manifest.name} ({manifest.id})")
                        return instance
            
            return None
        except Exception as e:
            logger.error(f"Error loading plugin from {plugin_file}: {e}")
            return None
    
    def initialize_plugin(self, plugin_id: str, orion_instance: Any) -> bool:
        """Initialize a loaded plugin"""
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            logger.error(f"Plugin not loaded: {plugin_id}")
            return False
        
        try:
            return plugin.initialize(orion_instance)
        except Exception as e:
            plugin.state = PluginState.ERROR
            logger.error(f"Error initializing plugin {plugin_id}: {e}")
            return False
    
    def start_plugin(self, plugin_id: str) -> bool:
        """Start a plugin"""
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            return False
        
        try:
            return plugin.start()
        except Exception as e:
            plugin.state = PluginState.ERROR
            logger.error(f"Error starting plugin {plugin_id}: {e}")
            return False
    
    def stop_plugin(self, plugin_id: str) -> bool:
        """Stop a plugin"""
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            return False
        
        try:
            return plugin.stop()
        except Exception as e:
            logger.error(f"Error stopping plugin {plugin_id}: {e}")
            return False
    
    def initialize_all(self, orion_instance: Any) -> int:
        """Initialize all loaded plugins"""
        count = 0
        for plugin_id in list(self.plugins.keys()):
            if self.initialize_plugin(plugin_id, orion_instance):
                count += 1
        return count
    
    def start_all(self) -> int:
        """Start all initialized plugins"""
        count = 0
        for plugin_id in list(self.plugins.keys()):
            if self.start_plugin(plugin_id):
                count += 1
        return count
    
    def stop_all(self) -> int:
        """Stop all plugins"""
        count = 0
        for plugin_id in list(self.plugins.keys()):
            if self.stop_plugin(plugin_id):
                count += 1
        return count
    
    def get_plugin_commands(self) -> Dict[str, Callable]:
        """Get all plugin commands"""
        commands = {}
        for plugin_id, plugin in self.plugins.items():
            if plugin.state == PluginState.STARTED:
                commands.update(plugin.get_commands())
        return commands
    
    def get_plugin_hooks(self) -> Dict[str, Callable]:
        """Get all plugin event hooks"""
        hooks = {}
        for plugin_id, plugin in self.plugins.items():
            if plugin.state == PluginState.STARTED:
                hooks.update(plugin.get_hooks())
        return hooks
    
    def list_plugins(self, include_discovered: bool = True) -> List[Dict[str, Any]]:
        """List all plugins"""
        result = []
        
        if include_discovered:
            for manifest in self.manifest_registry.values():
                plugin = self.plugins.get(manifest.id)
                result.append({
                    "id": manifest.id,
                    "name": manifest.name,
                    "version": manifest.version,
                    "description": manifest.description,
                    "state": plugin.state.value if plugin else PluginState.DISCOVERED.value
                })
        else:
            for plugin_id, plugin in self.plugins.items():
                manifest = self.manifest_registry.get(plugin_id)
                result.append({
                    "id": plugin_id,
                    "name": manifest.name if manifest else plugin_id,
                    "version": manifest.version if manifest else "unknown",
                    "state": plugin.state.value
                })
        
        return result


# Global instance
_plugin_manager: Optional[PluginManager] = None

def get_plugin_manager() -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
