#!/usr/bin/env python3
"""
Test script for device detection functionality.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from config_manager import ConfigManager
from device_detector import DeviceDetector
from rich import print as rprint
from rich.panel import Panel

DEBUG_MODE = False


def main():
    """Test device detection."""
    rprint(Panel("[green]Wanderer Device Detection Test[/green]"))
    if DEBUG_MODE:
        rprint(f"[yellow][DEBUG][test_detection] Debug mode enabled[/yellow]")
    try:
        # Load configuration
        config_manager = ConfigManager()
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][test_detection] Configuration loaded[/yellow]")
        rprint("[green]\u2713 Configuration loaded successfully[/green]")
        
        # Validate configuration
        errors = config_manager.validate_config()
        if errors:
            rprint("[red]Configuration errors:[/red]")
            for error in errors:
                rprint(f"  [red]- {error}[/red]")
            return
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][test_detection] Configuration validated successfully[/yellow]")
        rprint("[green]\u2713 Configuration validated successfully[/green]")
        
        # Show configuration summary
        summary = config_manager.get_config_summary()
        rprint(f"[blue]Configuration Summary:[/blue]")
        rprint(f"  - Devices configured: {summary['devices_count']}")
        rprint(f"  - Auto-detect: {summary['auto_detect']}")
        rprint(f"  - Dry run: {summary['dry_run']}")
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][test_detection] Config summary: {summary}")
        
        # Test device detection
        detector = DeviceDetector(config_manager)
        
        # Get available ports
        ports = detector.get_available_ports()
        rprint(f"[blue]Available ports:[/blue] {ports}")
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][test_detection] Ports found: {ports}")
        
        if not ports:
            rprint("[yellow]No serial ports found[/yellow]")
            return
        
        # Detect devices
        rprint("[blue]Detecting devices...[/blue]")
        detected_devices = detector.detect_devices()
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][test_detection] Detected devices: {detected_devices}")
        
        if detected_devices:
            rprint(f"[green]\u2713 Detected {len(detected_devices)} device(s):[/green]")
            for i, device in enumerate(detected_devices):
                info = detector.get_device_info(device)
                rprint(f"  [green]{i+1}.[/green] {info['name']}")
                rprint(f"      Port: {info['port']}")
                rprint(f"      Baud rate: {info['baud_rate']}")
                rprint(f"      AVR device: {info['avr_device']}")
                rprint(f"      Programmer: {info['programmer']}")
                rprint(f"      Handshake response: {info['handshake_response']}")
                rprint()
        else:
            rprint("[yellow]No devices detected[/yellow]")
            rprint("[blue]This could mean:[/blue]")
            rprint("  - No devices are connected")
            rprint("  - Devices are not responding to handshake commands")
            rprint("  - Handshake commands need to be adjusted")
            rprint("  - Baud rates need to be adjusted")
        
        # Test individual port detection
        rprint("[blue]Testing individual port detection...[/blue]")
        for port in ports[:3]:  # Test first 3 ports
            rprint(f"  Testing port {port}...")
            device = detector.detect_single_device(port)
            if DEBUG_MODE:
                rprint(f"[yellow][DEBUG][test_detection] Single device detection result for {port}: {device}")
            if device:
                info = detector.get_device_info(device)
                rprint(f"    \u2713 Found {info['name']} on {port}")
            else:
                rprint(f"    \u2717 No device detected on {port}")
        
    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test Wanderer device detection")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()
    DEBUG_MODE = args.debug
    if DEBUG_MODE:
        rprint("[yellow][DEBUG][test_detection] Debug mode enabled (from CLI)")
    main() 