#!/usr/bin/env python3
"""
List all configured devices and their parameters.
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from config_manager import ConfigManager
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table

DEBUG_MODE = False


def main():
    """List all configured devices."""
    rprint(Panel("[green]Wanderer Device Configuration List[/green]"))
    if DEBUG_MODE:
        rprint(f"[yellow][DEBUG][list_devices] Debug mode enabled[/yellow]")
    
    try:
        # Load configuration
        config_manager = ConfigManager()
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG][list_devices] Configuration loaded[/yellow]")
        
        # Validate configuration
        errors = config_manager.validate_config()
        if errors:
            rprint("[red]Configuration errors:[/red]")
            for error in errors:
                rprint(f"  [red]- {error}[/red]")
            return
        
        # Get all devices
        devices = config_manager.get_all_devices()
        
        if not devices:
            rprint("[yellow]No devices configured[/yellow]")
            return
        
        # Create table
        table = Table(title="Configured Devices")
        table.add_column("Device Name", style="cyan", no_wrap=True)
        table.add_column("AVR Device", style="magenta")
        table.add_column("Programmer", style="green")
        table.add_column("Baud Rate", style="yellow")
        table.add_column("Handshake String", style="blue")
        
        # Add rows
        for device in devices:
            table.add_row(
                device.name,
                device.avr_device,
                device.programmer,
                str(device.baud_rate),
                device.handshake_string
            )
        
        rprint(table)
        
        # Summary
        rprint(f"[blue]Total devices configured: {len(devices)}[/blue]")
        
        # Show configuration summary
        summary = config_manager.get_config_summary()
        rprint(f"[blue]Configuration Summary:[/blue]")
        rprint(f"  - Firmware source: {summary['firmware']['source_url']}")
        rprint(f"  - GitHub repo: {summary['firmware']['github_repo']}")
        rprint(f"  - Sync interval: {summary['firmware']['sync_interval_hours']} hours")
        rprint(f"  - Dry run mode: {summary['dry_run']}")
        
    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="List Wanderer device configurations")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()
    DEBUG_MODE = args.debug
    if DEBUG_MODE:
        rprint("[yellow][DEBUG][list_devices] Debug mode enabled (from CLI)")
    main() 