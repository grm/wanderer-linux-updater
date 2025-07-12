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
        return result
    
    def try_handshake(self, port: str, baud_rate: int, timeout: int = 5) -> Optional[str]:
        """Try to perform handshake with device on given port."""
        try:
            with serial.Serial(port, baud_rate, timeout=timeout) as ser:
                # Clear any existing data
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                
                # Try each handshake command
                for command in self.detection_config.handshake_commands:
                    try:
                        # Send command with newline
                        ser.write(f"{command}\n".encode('utf-8'))
                        ser.flush()
                        
                        # Wait a bit for response
                        time.sleep(0.5)
                        
                        # Read response
                        if ser.in_waiting > 0:
                            response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                            if response.strip():
                                return response.strip()
                        
                        # Try without newline
                        ser.write(f"{command}".encode('utf-8'))
                        ser.flush()
                        time.sleep(0.5)
                        
                        if ser.in_waiting > 0:
                            response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                            if response.strip():
                                return response.strip()
                                
                    except Exception as e:
                        continue
                
                return None
                
        except Exception as e:
            return None
    
    def detect_devices(self) -> List[DetectedDevice]:
        """Detect all connected devices."""
        detected_devices = []
        available_ports = self.get_available_ports()
        
        if not available_ports:
            return detected_devices
        
        for port in available_ports:
            for baud_rate in self.detection_config.baud_rates:
                handshake_response = self.try_handshake(
                    port, 
                    baud_rate, 
                    self.detection_config.handshake_timeout
                )
                
                if handshake_response:
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
                        break  # Found device on this port, try next port
        
        return detected_devices
    
    def detect_single_device(self, port: str) -> Optional[DetectedDevice]:
        """Detect device on specific port."""
        for baud_rate in self.detection_config.baud_rates:
            handshake_response = self.try_handshake(
                port, 
                baud_rate, 
                self.detection_config.handshake_timeout
            )
            
            if handshake_response:
                device_config = self.config.find_device_by_handshake(handshake_response)
                
                if device_config:
                    return DetectedDevice(
                        port=port,
                        device_config=device_config,
                        handshake_response=handshake_response,
                        baud_rate=baud_rate
                    )
        
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