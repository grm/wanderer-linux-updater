#!/usr/bin/env python3
"""
Device detection module for Wanderer Linux Updater.
Handles automatic detection of connected devices through handshake.
"""

import serial
import time
from typing import List, Optional, Dict
from dataclasses import dataclass

try:
    from rich import print as rprint
except ImportError:
    rprint = print

from config_manager import ConfigManager, DeviceConfig

# Global debug mode
DEBUG_MODE = False

def set_debug_mode(enabled: bool):
    """Set debug mode for this module."""
    global DEBUG_MODE
    DEBUG_MODE = enabled


@dataclass
class DetectedDevice:
    """Information about a detected device."""
    port: str
    device_config: DeviceConfig
    handshake_response: str
    baud_rate: int


class DeviceDetector:
    """Handles automatic device detection through handshake."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
    
    def get_available_ports(self) -> List[str]:
        """Get list of available serial ports."""
        import serial.tools.list_ports
        
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(port.device)
        
        result = sorted(ports)
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][DeviceDetector] Available ports: {result}")
        return result
    
    def try_handshake(self, port: str, baud_rate: int, device_config: DeviceConfig, timeout: int = None) -> Optional[str]:
        """Try to perform handshake with device on given port."""
        if timeout is None:
            timeout = self.config.device_detection_config.handshake_timeout if self.config.device_detection_config else 5
        
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][DeviceDetector] Trying handshake on port {port} at {baud_rate} baud with timeout {timeout}s")
        
        try:
            ser = serial.Serial(port, baud_rate, timeout=timeout)
            if DEBUG_MODE:
                rprint(f"[yellow][DEBUG][DeviceDetector] Serial port opened successfully")
            
            # Clear buffers
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # Case 1: Device has handshake_command - send it and wait for response
            if device_config.handshake_command:
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG][DeviceDetector] Sending handshake_command '{device_config.handshake_command}'")
                
                # Send command with newline
                ser.write(f"{device_config.handshake_command}\n".encode('utf-8'))
                ser.flush()
                time.sleep(0.5)
                
                # Read response
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    if DEBUG_MODE:
                        rprint(f"[yellow][DEBUG][DeviceDetector] Response to '{device_config.handshake_command}' (with newline): '{response.strip()}'")
                    if response.strip():
                        return response.strip()
                
                # Try without newline
                ser.write(f"{device_config.handshake_command}".encode('utf-8'))
                ser.flush()
                time.sleep(0.5)
                
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    if DEBUG_MODE:
                        rprint(f"[yellow][DEBUG][DeviceDetector] Response to '{device_config.handshake_command}' (no newline): '{response.strip()}'")
                    if response.strip():
                        return response.strip()
            
            # Case 2: Device has no handshake_command - wait for automatic response
            else:
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG][DeviceDetector] No handshake_command - waiting for automatic response")
                
                # Wait for automatic response
                time.sleep(1.0)
                
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    if DEBUG_MODE:
                        rprint(f"[yellow][DEBUG][DeviceDetector] Automatic response: '{response.strip()}'")
                    if response.strip():
                        return response.strip()
            
            ser.close()
            return None
                
        except Exception as e:
            if DEBUG_MODE:
                rprint(f"[yellow][DEBUG][DeviceDetector] Exception opening port {port} at {baud_rate}: {e}")
            return None
    
    def detect_devices(self) -> List[DetectedDevice]:
        """Detect all connected devices."""
        detected_devices = []
        available_ports = self.get_available_ports()
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][DeviceDetector] Starting detection on ports: {available_ports}")
        if not available_ports:
            return detected_devices
        
        # Try each device configuration on each port
        for device_config in self.config.get_all_devices():
            detection_baud_rate = device_config.handshake_baud_rate if device_config.handshake_baud_rate else device_config.baud_rate
            
            for port in available_ports:
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG][DeviceDetector] Testing {device_config.name} on port {port} at {detection_baud_rate} baud")
                
                handshake_response = self.try_handshake(port, detection_baud_rate, device_config)
                
                if handshake_response:
                    if DEBUG_MODE:
                        rprint(f"[yellow][DEBUG][DeviceDetector] Handshake response on {port} ({detection_baud_rate}): {handshake_response}")
                    
                    # Check if response matches expected handshake_response
                    if device_config.handshake_response.lower() in handshake_response.lower():
                        detected_device = DetectedDevice(
                            port=port,
                            device_config=device_config,
                            handshake_response=handshake_response,
                            baud_rate=detection_baud_rate
                        )
                        detected_devices.append(detected_device)
                        if DEBUG_MODE:
                            rprint(f"[yellow][DEBUG][DeviceDetector] Device detected: {detected_device}")
                        break  # Found device on this port, try next device
                    else:
                        if DEBUG_MODE:
                            rprint(f"[yellow][DEBUG][DeviceDetector] Response '{handshake_response}' doesn't match expected '{device_config.handshake_response}'")
        
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][DeviceDetector] Detection finished. Devices: {detected_devices}")
        return detected_devices
    
    def detect_single_device(self, port: str) -> Optional[DetectedDevice]:
        """Detect device on specific port."""
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][DeviceDetector] Detecting single device on port {port}")
        
        # Try each device configuration on the specified port
        for device_config in self.config.get_all_devices():
            detection_baud_rate = device_config.handshake_baud_rate if device_config.handshake_baud_rate else device_config.baud_rate
            
            if DEBUG_MODE:
                rprint(f"[yellow][DEBUG][DeviceDetector] Trying {device_config.name} on port {port} at {detection_baud_rate} baud")
            
            handshake_response = self.try_handshake(port, detection_baud_rate, device_config)
            
            if handshake_response:
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG][DeviceDetector] Handshake response on {port} ({detection_baud_rate}): '{handshake_response}'")
                
                # Check if response matches expected handshake_response
                if device_config.handshake_response.lower() in handshake_response.lower():
                    if DEBUG_MODE:
                        rprint(f"[yellow][DEBUG][DeviceDetector] Device found: {device_config.name}")
                    return DetectedDevice(
                        port=port,
                        device_config=device_config,
                        handshake_response=handshake_response,
                        baud_rate=detection_baud_rate
                    )
                else:
                    if DEBUG_MODE:
                        rprint(f"[yellow][DEBUG][DeviceDetector] Response '{handshake_response}' doesn't match expected '{device_config.handshake_response}'")
            else:
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG][DeviceDetector] No handshake response on {port} at {detection_baud_rate} baud")
        
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][DeviceDetector] No device detected on port {port}")
        return None
    
    def get_device_info(self, detected_device: DetectedDevice) -> Dict[str, str]:
        """Get formatted device information."""
        return {
            'name': detected_device.device_config.name,
            'port': detected_device.port,
            'baud_rate': str(detected_device.baud_rate),
            'avr_device': detected_device.device_config.avr_device,
            'programmer': detected_device.device_config.programmer,
            'handshake_response': detected_device.handshake_response
        }
    
    def format_device_list(self, detected_devices: List[DetectedDevice]) -> List[str]:
        """Format detected devices for display."""
        device_list = []
        for i, device in enumerate(detected_devices):
            info = self.get_device_info(device)
            device_list.append(
                f"{i}: {info['name']} on {info['port']} "
                f"({info['baud_rate']} baud) - {info['handshake_response']}"
            )
        return device_list 