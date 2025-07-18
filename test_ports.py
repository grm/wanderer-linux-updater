#!/usr/bin/env python3
"""
Test script for USB port detection functionality.
This script only detects available serial ports without trying to identify device types.
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
    """Test USB port detection."""
    rprint(Panel("[green]Wanderer USB Port Detection Test[/green]"))
    if DEBUG_MODE:
        rprint(f"[yellow][DEBUG][test_ports] Debug mode enabled[/yellow]")
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][test_ports] Configuration loaded[/yellow]")
        rprint("[green]\u2713 Configuration loaded successfully[/green]")
        
        # Validate configuration
        errors = config_manager.validate_config()
        if errors:
            rprint("[red]Configuration errors:[/red]")
            for error in errors:
                rprint(f"  [red]- {error}[/red]")
            return
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][test_ports] Configuration validated successfully[/yellow]")
        rprint("[green]\u2713 Configuration validated successfully[/green]")
        
        # Show configuration summary
        summary = config_manager.get_config_summary()
        rprint(f"[blue]Configuration Summary:[/blue]")
        rprint(f"  - Devices configured: {summary['devices_count']}")
        rprint(f"  - Dry run: {summary['dry_run']}")
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][test_ports] Config summary: {summary}")
        
        # Test port detection
        detector = DeviceDetector(config_manager)
        
        # Get available ports
        ports = detector.get_available_ports()
        rprint(f"[blue]Available USB/Serial ports:[/blue] {ports}")
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][test_ports] Ports found: {ports}")
        
        if not ports:
            rprint("[yellow]No serial ports found[/yellow]")
            rprint("[blue]This could mean:[/blue]")
            rprint("  - No USB devices are connected")
            rprint("  - No serial devices are connected")
            rprint("  - Permission issues with /dev/tty* devices")
            return
        
        rprint(f"[green]\u2713 Found {len(ports)} available port(s)[/green]")
        
        # Test basic connectivity on each port
        rprint("[blue]Testing basic connectivity on each port...[/blue]")
        for port in ports:
            rprint(f"  Testing port {port}...")
            try:
                import serial
                with serial.Serial(port, 115200, timeout=1) as ser:
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()
                    # Try to read any available data
                    if ser.in_waiting > 0:
                        data = ser.read(ser.in_waiting)
                        rprint(f"    \u2713 Port {port} is accessible and has data")
                    else:
                        rprint(f"    \u2713 Port {port} is accessible (no data)")
            except Exception as e:
                rprint(f"    \u2717 Port {port} error: {e}")
        
        # Show device types that can be selected
        rprint("[blue]Available device types for manual selection:[/blue]")
        for device_name in config_manager.get_device_names():
            device_config = config_manager.get_device(device_name)
            rprint(f"  - {device_name} ({device_config.avr_device}, {device_config.baud_rate} baud)")
        
    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test Wanderer USB port detection")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()
    DEBUG_MODE = args.debug
    if DEBUG_MODE:
        rprint("[yellow][DEBUG][test_ports] Debug mode enabled (from CLI)")
    main() 