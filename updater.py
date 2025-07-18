#!/usr/bin/env python3
"""
Wanderer Linux Updater - Interactive Firmware Update Tool
Allows users to manually select device type, firmware, and port for updates.
"""

import argparse
import glob
import os
import rich
import serial
import sys
import requests
import tempfile
from urllib.parse import urlparse

from ast import arg
from os import path
from random import choices
from rich import print as rprint
from rich.panel import Panel
from typing import IO, Optional, List, Dict

# Import our modules
from config_manager import ConfigManager, set_debug_mode as set_config_debug_mode
from device_detector import DeviceDetector, DetectedDevice, set_debug_mode as set_detector_debug_mode

make_dry_run = False
DEBUG_MODE = False


class WandererParser(argparse.ArgumentParser):
    def _print_message(self, message: str, file: Optional[IO[str]] = None) -> None:
        rich.print(message, file=file)


def ask_question(question: str, answers: List[str]) -> int:
    """Ask user to choose from a list of options."""
    rprint(f"[green]- {question}[/green]")
    for i in range(len(answers)):
        rprint(f"    [yellow]{i}[/yellow] : [blue]{answers[i]}[/blue]")
    rprint("Your choice : ")
    ichoice = input()
    try:
        choice = int(ichoice)
        if choice < 0 or choice >= (len(answers)):
            rprint(f"[red]Error : the device number '{choice}' is unknown ![/red]")
            return ask_question(question, answers)
    except ValueError:
        rprint(
            f"[red]Error : Please type a number between 0 and {len(answers) - 1 }[/red]"
        )
        return ask_question(question, answers)
    return choice


def get_available_ports() -> List[str]:
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


def run_update(device_config, port: str, firmware_path: str, config_manager: ConfigManager):
    """Run firmware update with device configuration."""
    command = f"avrdude -p {device_config.avr_device} -c {device_config.programmer} -b {device_config.baud_rate} -P {port} -U flash:w:{firmware_path}:i"
    rprint(f"Command : '{command}'")
    
    if not make_dry_run:
        if config_manager.update_config.confirm_update:
            rprint(
                "Do you wish to execute \\[yY] ? [red] (do NOT disconnect device before end of process)"
            )
            execution_order = input()
            if execution_order == "y" or execution_order == "Y":
                os.system(command)
                rprint("[green] Firmware update done. You can eject device.")
            else:
                rprint("[red] Aborting ..")
        else:
            os.system(command)
            rprint("[green] Firmware update done. You can eject device.")
    else:
        rprint("[yellow]Dry run mode - command not executed[/yellow]")


def get_firmware_index(github_repo=None):
    """Get firmware index from GitHub Pages."""
    if not github_repo:
        github_repo = "your-username/wanderer-linux-updater"  # Update with your repo
    if DEBUG_MODE:
        rprint(f"[yellow][DEBUG] get_firmware_index() using github_repo={github_repo}[/yellow]")
    if not github_repo or '/' not in github_repo:
        raise ValueError(f"Invalid github_repo format: '{github_repo}'. Expected 'username/reponame'.")
    parts = github_repo.split('/')
    index_url = f"https://{parts[0]}.github.io/{parts[1]}/firmware_index.json"
    if DEBUG_MODE:
        rprint(f"[yellow][DEBUG] Firmware index URL: {index_url}[/yellow]")
    try:
        rprint(f"[blue]Downloading firmware index from: {index_url}[/blue]")
        response = requests.get(index_url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        rprint(f"[red]Error downloading firmware index: {e}[/red]")
        return None


def get_available_firmware_for_device(device_name: str, firmware_index: Dict) -> List[Dict]:
    """Get available firmware for a specific device."""
    if not firmware_index or 'devices' not in firmware_index:
        return []
    
    # Try exact match first
    if device_name in firmware_index['devices']:
        return firmware_index['devices'][device_name]
    
    # Try partial matches
    available_firmware = []
    for device, firmwares in firmware_index['devices'].items():
        if device_name.lower() in device.lower() or device.lower() in device_name.lower():
            available_firmware.extend(firmwares)
    
    return available_firmware


def download_firmware_file(firmware_url: str, temp_dir: str) -> Optional[str]:
    """Download a firmware file to a temporary location."""
    try:
        rprint(f"[blue]Downloading firmware: {firmware_url}[/blue]")
        response = requests.get(firmware_url, timeout=60)
        response.raise_for_status()
        
        # Extract filename from URL
        filename = firmware_url.split('/')[-1]
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        rprint(f"[green]Firmware downloaded to: {file_path}[/green]")
        return file_path
    except requests.RequestException as e:
        rprint(f"[red]Error downloading firmware: {e}[/red]")
        return None


def select_device_type(config_manager: ConfigManager) -> Optional[str]:
    """Let user select device type from available devices."""
    available_devices = config_manager.get_device_names()
    if not available_devices:
        rprint("[red]No devices configured in config.yml[/red]")
        return None
    
    rprint("[blue]Available device types:[/blue]")
    device_choices = []
    for device_name in available_devices:
        device_config = config_manager.get_device(device_name)
        device_choices.append(f"{device_name} ({device_config.avr_device}, {device_config.baud_rate} baud)")
    
    choice = ask_question("Select device type:", device_choices)
    return available_devices[choice]


def select_port() -> Optional[str]:
    """Let user select a serial port."""
    available_ports = get_available_ports()
    if not available_ports:
        rprint("[red]No serial ports found[/red]")
        return None
    
    rprint("[blue]Available serial ports:[/blue]")
    port_choices = []
    for port in available_ports:
        port_choices.append(port)
    
    choice = ask_question("Select serial port:", port_choices)
    return available_ports[choice]


def select_firmware(device_name: str, firmware_index: Dict) -> Optional[Dict]:
    """Let user select firmware for the device."""
    available_firmware = get_available_firmware_for_device(device_name, firmware_index)
    if not available_firmware:
        rprint(f"[red]No firmware found for device {device_name}[/red]")
        return None
    
    # Sort by version date (newest first)
    available_firmware = sorted(available_firmware, key=lambda fw: fw.get('version_date', ''), reverse=True)
    
    rprint(f"[blue]Available firmware for {device_name}:[/blue]")
    firmware_choices = []
    for fw in available_firmware:
        version = fw.get('version', 'Unknown')
        version_date = fw.get('version_date', 'Unknown date')
        filename = fw.get('filename', 'Unknown file')
        firmware_choices.append(f"{version} ({version_date}) - {filename}")
    
    choice = ask_question("Select firmware version:", firmware_choices)
    return available_firmware[choice]


def test_device_connection(port: str, device_config) -> bool:
    """Test if device is connected and responding on the selected port."""
    rprint(f"[blue]Testing connection to {device_config.name} on {port}...[/blue]")
    
    if DEBUG_MODE:
        rprint(f"[yellow][DEBUG] Testing device {device_config.name} on {port} at {device_config.baud_rate} baud")
        if device_config.handshake_string:
            rprint(f"[yellow][DEBUG] Device has handshake_string: '{device_config.handshake_string}'")
        else:
            rprint(f"[yellow][DEBUG] Device has no handshake_string - waiting for automatic response")
    
    try:
        import serial
        with serial.Serial(port, device_config.baud_rate, timeout=5) as ser:
            if DEBUG_MODE:
                rprint(f"[yellow][DEBUG] Serial port opened successfully")
            
            # Clear any existing data
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            if device_config.handshake_string:
                # Case 1: Device has handshake_string - send it and wait for response
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG] Sending handshake_string '{device_config.handshake_string}'")
                
                # Send the handshake string
                ser.write(f"{device_config.handshake_string}\n".encode('utf-8'))
                ser.flush()
                
                # Wait for response and analyze all received data (up to 5 seconds)
                import time
                start_time = time.time()
                all_received_data = ""
                
                while time.time() - start_time < 5.0:
                    if ser.in_waiting > 0:
                        new_data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                        all_received_data += new_data
                        if DEBUG_MODE:
                            rprint(f"[yellow][DEBUG] Received data: '{new_data.strip()}'")
                        
                        # Check if we have a complete response (contains newline)
                        if '\n' in all_received_data:
                            lines = all_received_data.split('\n')
                            for line in lines:
                                line = line.strip()
                                if line:
                                    if DEBUG_MODE:
                                        rprint(f"[yellow][DEBUG] Analyzing line: '{line}'")
                                    # Check if this line indicates a response
                                    if line and not line.startswith(device_config.handshake_string):
                                        if DEBUG_MODE:
                                            rprint(f"[yellow][DEBUG] Found response line: '{line}'")
                                        rprint(f"[green]✓ Device {device_config.name} detected on {port}[/green]")
                                        return True
                    
                    time.sleep(0.1)  # Check every 100ms
                
                # Try without newline if no response with newline
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG] No response with newline, trying without newline")
                
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                ser.write(f"{device_config.handshake_string}".encode('utf-8'))
                ser.flush()
                
                start_time = time.time()
                all_received_data = ""
                
                while time.time() - start_time < 5.0:
                    if ser.in_waiting > 0:
                        new_data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                        all_received_data += new_data
                        if DEBUG_MODE:
                            rprint(f"[yellow][DEBUG] Received data (no newline): '{new_data.strip()}'")
                        
                        # Check if we have any response
                        if DEBUG_MODE:
                            rprint(f"[yellow][DEBUG] Checking response: '{repr(all_received_data)}'")
                            rprint(f"[yellow][DEBUG] Stripped response: '{repr(all_received_data.strip())}'")
                            rprint(f"[yellow][DEBUG] Response length: {len(all_received_data.strip())}")
                        
                        if all_received_data.strip() and len(all_received_data.strip()) > 0:
                            if DEBUG_MODE:
                                rprint(f"[yellow][DEBUG] Found valid response: '{all_received_data.strip()}'")
                                rprint(f"[yellow][DEBUG] Response length: {len(all_received_data.strip())}")
                                rprint(f"[yellow][DEBUG] Response bytes: {repr(all_received_data)}")
                            rprint(f"[green]✓ Device {device_config.name} detected on {port}[/green]")
                            return True
                        elif DEBUG_MODE:
                            rprint(f"[yellow][DEBUG] No valid response yet, continuing to wait...")
                    
                    time.sleep(0.1)
                
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG] No response to handshake_string after 5 seconds")
                
            else:
                # Case 2: Device has no handshake_string - wait for automatic response
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG] Waiting for automatic response (up to 5 seconds)")
                
                import time
                start_time = time.time()
                all_received_data = ""
                
                while time.time() - start_time < 5.0:
                    if ser.in_waiting > 0:
                        new_data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                        all_received_data += new_data
                        if DEBUG_MODE:
                            rprint(f"[yellow][DEBUG] Received automatic data: '{new_data.strip()}'")
                        
                        # Check if we have any response
                        if all_received_data.strip():
                            if DEBUG_MODE:
                                rprint(f"[yellow][DEBUG] Found automatic response: '{all_received_data.strip()}'")
                            rprint(f"[green]✓ Device {device_config.name} detected on {port}[/green]")
                            return True
                    
                    time.sleep(0.1)  # Check every 100ms
                
                if DEBUG_MODE:
                    rprint(f"[yellow][DEBUG] No automatic response received after 5 seconds")
            
            rprint(f"[yellow]⚠ No {device_config.name} detected on {port}[/yellow]")
            rprint("[blue]You can still proceed with the update if you're sure the device is connected.[/blue]")
            return False
            
    except Exception as e:
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG] Exception opening port {port}: {e}")
        rprint(f"[red]Error testing connection to {device_config.name} on {port}: {e}[/red]")
        rprint("[blue]You can still proceed with the update if you're sure the device is connected.[/blue]")
        return False


def main(firmware_url=None, firmware_file=None, github_repo=None, config_file="config.yml"):
    """Main function for interactive firmware update."""
    rprint(
        Panel("[green]Welcome to [red]Wanderer astro[/red] linux update tool ![/green]")
    )
    
    if DEBUG_MODE:
        rprint(f"[yellow][DEBUG] main() called with config_file={config_file}[/yellow]")
    
    # Load configuration
    try:
        config_manager = ConfigManager(config_file)
        if DEBUG_MODE:
            rprint(f"[yellow][DEBUG] Configuration loaded from {config_file}[/yellow]")
            rprint(f"[yellow][DEBUG] Config summary: {config_manager.get_config_summary()}[/yellow]")
    except Exception as e:
        rprint(f"[red]Error loading configuration: {e}[/red]")
        return
    
    # Validate configuration
    errors = config_manager.validate_config()
    if errors:
        rprint("[red]Configuration errors:[/red]")
        for error in errors:
            rprint(f"  [red]- {error}[/red]")
        return
    
    # Get firmware index
    github_repo = config_manager.firmware_config.github_repo
    if DEBUG_MODE:
        rprint(f"[yellow][DEBUG] github_repo from config: {github_repo}[/yellow]")
    
    firmware_index = get_firmware_index(github_repo)
    if not firmware_index:
        rprint("[red]Failed to download firmware index. Exiting.[/red]")
        return
    
    if DEBUG_MODE:
        rprint(f"[yellow][DEBUG] Firmware index loaded: {firmware_index}[/yellow]")
    
    # Step 1: Select device type
    rprint("[blue]Step 1: Select device type[/blue]")
    device_name = select_device_type(config_manager)
    if not device_name:
        return
    
    device_config = config_manager.get_device(device_name)
    rprint(f"[green]Selected device: {device_name}[/green]")
    
    # Step 2: Select port
    rprint("[blue]Step 2: Select serial port[/blue]")
    port = select_port()
    if not port:
        return
    
    rprint(f"[green]Selected port: {port}[/green]")
    
    # Step 3: Test device connection (optional)
    test_device_connection(port, device_config)
    
    # Step 4: Select firmware
    rprint("[blue]Step 3: Select firmware[/blue]")
    selected_firmware = select_firmware(device_name, firmware_index)
    if not selected_firmware:
        return
    
    rprint(f"[green]Selected firmware: {selected_firmware.get('filename', 'Unknown')}[/green]")
    
    # Step 5: Download and update
    rprint("[blue]Step 4: Download and update firmware[/blue]")
    with tempfile.TemporaryDirectory() as temp_dir:
        firmware_path = download_firmware_file(selected_firmware['url'], temp_dir)
        if not firmware_path:
            rprint("[red]Failed to download firmware. Aborting.[/red]")
            return
        
        run_update(device_config, port, firmware_path, config_manager)


if __name__ == "__main__":
    parser = WandererParser(description="WandererLinuxUpdater help")
    parser.add_argument(
        "-c", "--config",
        type=str,
        default="config.yml",
        help="Configuration file path (default: config.yml)"
    )
    parser.add_argument(
        "-d",
        action="store_true",
        help="Do a dry run (print avr command instead of executing it)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output"
    )
    args = parser.parse_args()
    make_dry_run = args.d
    DEBUG_MODE = args.debug
    
    # Set debug mode in imported modules
    set_config_debug_mode(DEBUG_MODE)
    set_detector_debug_mode(DEBUG_MODE)
    
    if DEBUG_MODE:
        rprint("[yellow][DEBUG] Debug mode enabled[/yellow]")
    main(config_file=args.config)
