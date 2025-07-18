#!/usr/bin/env python3
"""
Configuration manager for Wanderer Linux Updater.
Handles loading and validation of YAML configuration files.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    from rich import print as rprint
except ImportError:
    rprint = print

try:
    from updater import DEBUG_MODE
except ImportError:
    DEBUG_MODE = False


@dataclass
class DeviceConfig:
    """Configuration for a single device."""
    name: str
    avr_device: str
    programmer: str
    baud_rate: int
    handshake_string: str


@dataclass
class FirmwareConfig:
    """Configuration for firmware sync."""
    source_url: str
    github_repo: Optional[str]
    sync_interval_hours: int
    firmware_dir: str
    index_file: str


@dataclass
class DeviceDetectionConfig:
    """Configuration for device detection."""
    handshake_timeout: int
    port_detection_timeout: int
    baud_rates: List[int]
    handshake_commands: List[str]


@dataclass
class UpdateConfig:
    """Configuration for update operations."""
    avrdude_timeout: int
    dry_run: bool
    confirm_update: bool


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str
    log_file: Optional[str]
    show_progress: bool


class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_file: str = "config.yml"):
        self.config_file = Path(config_file)
        self.config_data = {}
        self.devices: Dict[str, DeviceConfig] = {}
        self.firmware_config: Optional[FirmwareConfig] = None
        self.device_detection_config: Optional[DeviceDetectionConfig] = None
        self.update_config: Optional[UpdateConfig] = None
        self.logging_config: Optional[LoggingConfig] = None
        
        self.load_config()
    
    def load_config(self):
        """Load configuration from YAML file."""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][ConfigManager] Loading config file: {self.config_file}[/yellow]")
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f)
            if DEBUG_MODE:
                rprint(f"[yellow][DEBUG][ConfigManager] Raw config data: {self.config_data}[/yellow]")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")
        self._validate_and_parse_config()
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][ConfigManager] Config parsed: {self.get_config_summary()}[/yellow]")
    
    def _validate_and_parse_config(self):
        """Validate and parse configuration sections."""
        # Parse firmware configuration
        firmware_data = self.config_data.get('firmware', {})
        self.firmware_config = FirmwareConfig(
            source_url=firmware_data.get('source_url', ''),
            github_repo=firmware_data.get('github_repo'),
            sync_interval_hours=firmware_data.get('sync_interval_hours', 6),
            firmware_dir=firmware_data.get('firmware_dir', 'firmwares'),
            index_file=firmware_data.get('index_file', 'firmware_index.json')
        )
        
        # Parse device detection configuration
        detection_data = self.config_data.get('device_detection', {})
        self.device_detection_config = DeviceDetectionConfig(
            handshake_timeout=detection_data.get('handshake_timeout', 5),
            port_detection_timeout=detection_data.get('port_detection_timeout', 3),
            baud_rates=detection_data.get('baud_rates', [115200, 57600, 9600]),
            handshake_commands=detection_data.get('handshake_commands', ['VERSION', 'DEVICE', 'ID'])
        )
        
        # Parse devices
        devices_data = self.config_data.get('devices', {})
        for device_name, device_data in devices_data.items():
            self.devices[device_name] = DeviceConfig(
                name=device_name,
                avr_device=device_data.get('avr_device', ''),
                programmer=device_data.get('programmer', ''),
                baud_rate=device_data.get('baud_rate', 115200),
                handshake_string=device_data.get('handshake_string', '')
            )
        
        # Parse update configuration
        update_data = self.config_data.get('update', {})
        self.update_config = UpdateConfig(
            avrdude_timeout=update_data.get('avrdude_timeout', 60),
            dry_run=update_data.get('dry_run', False),
            confirm_update=update_data.get('confirm_update', True)
        )
        
        # Parse logging configuration
        logging_data = self.config_data.get('logging', {})
        self.logging_config = LoggingConfig(
            level=logging_data.get('level', 'INFO'),
            log_file=logging_data.get('log_file'),
            show_progress=logging_data.get('show_progress', True)
        )
    
    def get_device(self, device_name: str) -> Optional[DeviceConfig]:
        """Get device configuration by name."""
        return self.devices.get(device_name)
    
    def get_all_devices(self) -> List[DeviceConfig]:
        """Get all device configurations."""
        return list(self.devices.values())
    
    def get_device_names(self) -> List[str]:
        """Get all device names."""
        return list(self.devices.keys())
    
    def find_device_by_handshake(self, handshake_response: str) -> Optional[DeviceConfig]:
        """Find device by handshake response (model name before first 'A')."""
        # Extract model name before first 'A'
        model_name = handshake_response.split('A', 1)[0].strip()
        if model_name in self.devices:
            return self.devices[model_name]
        # Fallback: try handshake_string
        for device_name, device_config in self.devices.items():
            if device_config.handshake_string.lower() in handshake_response.lower():
                return device_config
        return None
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate firmware configuration
        if not self.firmware_config.source_url:
            errors.append("Firmware source URL is required")
        
        # Validate devices
        if not self.devices:
            errors.append("At least one device must be configured")
        
        for device_name, device_config in self.devices.items():
            if not device_config.avr_device:
                errors.append(f"Device {device_name}: avr_device is required")
            if not device_config.programmer:
                errors.append(f"Device {device_name}: programmer is required")
            if not device_config.handshake_string:
                errors.append(f"Device {device_name}: handshake_string is required")
        
        return errors
    
    def reload_config(self):
        """Reload configuration from file."""
        self.load_config()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration."""
        return {
            'firmware': {
                'source_url': self.firmware_config.source_url,
                'github_repo': self.firmware_config.github_repo,
                'sync_interval_hours': self.firmware_config.sync_interval_hours
            },
            'devices_count': len(self.devices),
            'device_names': list(self.devices.keys()),
            'dry_run': self.update_config.dry_run
        } 