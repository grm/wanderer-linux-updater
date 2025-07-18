#!/usr/bin/env python3
"""
Device detection module for Wanderer Linux Updater.
Handles automatic detection of connected devices through handshake.
"""

import glob
import sys
import time
import serial
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass
from config_manager import ConfigManager, DeviceConfig

try:
    from rich import print as rprint
except ImportError:
    rprint = print

# Global debug mode - will be set by updater.py
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
        self.detection_config = config_manager.device_detection_config
    
    def get_available_ports(self) -> List[str]:
        """Get list of available serial ports."""
        if sys.platform.startswith("win"):
            ports = ["COM%s" % (i + 1) for i in range(256)]
        elif sys.platform.startswith("linux") or sys.platform.startswith("cygwin"):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob("/dev/tty[A-Za-z]*")
        elif sys.platform.startswith("darwin"):
            ports = glob.glob("/dev/tty.*")
        else:
            raise EnvironmentError("Unsupported platform")

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][DeviceDetector] Available ports: {result}")
        return result
    
    def try_handshake(self, port: str, baud_rate: int, timeout: int = 5) -> Optional[str]:
        """Try to perform handshake with device on given port."""
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][DeviceDetector] Trying handshake on port {port} at {baud_rate} baud");
        try:
            with serial.Serial(port, baud_rate, timeout=timeout) as ser:
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG][DeviceDetector] Serial port opened successfully")
                
                # Clear any existing data
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                # Try each handshake command
                for command in self.detection_config.handshake_commands:
                    try:
                        if DEBUG_MODE:
                            rprint(f"[yellow][DEBUG][DeviceDetector] Sending handshake command '{command}' to {port}")
                        
                        # Send command with newline
                        ser.write(f"{command}\n".encode('utf-8'))
                        ser.flush()
                        
                        # Wait a bit for response
                        time.sleep(0.5)
                        
                        # Read response
                        if ser.in_waiting > 0:
                            response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                            if DEBUG_MODE:
                                rprint(f"[yellow][DEBUG][DeviceDetector] Response to '{command}' (with newline): '{response.strip()}'")
                            if response.strip():
                                return response.strip()
                        else:
                            if DEBUG_MODE:
                                rprint(f"[yellow][DEBUG][DeviceDetector] No response to '{command}' (with newline)")
                        
                        # Try without newline
                        ser.write(f"{command}".encode('utf-8'))
                        ser.flush()
                        time.sleep(0.5)
                        
                        if ser.in_waiting > 0:
                            response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                            if DEBUG_MODE:
                                rprint(f"[yellow][DEBUG][DeviceDetector] Response to '{command}' (no newline): '{response.strip()}'")
                            if response.strip():
                                return response.strip()
                        else:
                            if DEBUG_MODE:
                                rprint(f"[yellow][DEBUG][DeviceDetector] No response to '{command}' (no newline)")
                                
                    except Exception as e:
                        if DEBUG_MODE:
                            rprint(f"[yellow][DEBUG][DeviceDetector] Exception during handshake command '{command}': {e}")
                        continue
                
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG][DeviceDetector] No response to any handshake command on {port}")
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
        for port in available_ports:
            for baud_rate in self.detection_config.baud_rates:
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG][DeviceDetector] Testing port {port} at baud {baud_rate}")
                handshake_response = self.try_handshake(
                    port, 
                    baud_rate, 
                    self.detection_config.handshake_timeout
                )
                if handshake_response:
                    if DEBUG_MODE:
                        rprint(f"[yellow][DEBUG][DeviceDetector] Handshake response on {port} ({baud_rate}): {handshake_response}")
                    # Try to identify device from response
                    device_config = self.config.find_device_by_handshake(handshake_response)
                    if device_config:
                        detected_device = DetectedDevice(
                            port=port,
                            device_config=device_config,
                            handshake_response=handshake_response,
                            baud_rate=baud_rate
                        )
                        detected_devices.append(detected_device)
                        if DEBUG_MODE:
                            rprint(f"[yellow][DEBUG][DeviceDetector] Device detected: {detected_device}")
                        break  # Found device on this port, try next port
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][DeviceDetector] Detection finished. Devices: {detected_devices}")
        return detected_devices
    
    def detect_single_device(self, port: str) -> Optional[DetectedDevice]:
        """Detect device on specific port."""
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][DeviceDetector] Detecting single device on port {port}")
        
        for baud_rate in self.detection_config.baud_rates:
            if DEBUG_MODE:
                rprint(f"[yellow][DEBUG][DeviceDetector] Trying baud rate {baud_rate} on port {port}")
            
            handshake_response = self.try_handshake(
                port, 
                baud_rate, 
                self.detection_config.handshake_timeout
            )
            
            if handshake_response:
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG][DeviceDetector] Handshake response on {port} ({baud_rate}): '{handshake_response}'")
                
                device_config = self.config.find_device_by_handshake(handshake_response)
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG][DeviceDetector] Device config found: {device_config}")
                
                if device_config:
                    if DEBUG_MODE:
                        rprint(f"[yellow][DEBUG][DeviceDetector] Device found: {device_config.name}")
                    return DetectedDevice(
                        port=port,
                        device_config=device_config,
                        handshake_response=handshake_response,
                        baud_rate=baud_rate
                    )
                else:
                    if DEBUG_MODE:
                        rprint(f"[yellow][DEBUG][DeviceDetector] No device config matched for response: '{handshake_response}'")
            else:
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG][DeviceDetector] No handshake response on {port} at {baud_rate} baud")
        
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