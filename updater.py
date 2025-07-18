import argparse
import csv
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
from typing import IO, Optional, List

# Import our new modules
from config_manager import ConfigManager
from device_detector import DeviceDetector, DetectedDevice

make_dry_run = False
DEBUG_MODE = False


class WandererParser(argparse.ArgumentParser):
    def _print_message(self, message: str, file: Optional[IO[str]] = None) -> None:
        rich.print(message, file=file)


def ask_question(question, answers):
    rprint(f"[green]- {question}[/green]")
    for i in range(len(answers)):
        rprint(f"    [yellow]{i}[/yellow] : [blue]{answers[i]}")
    rprint("Your choice : ")
    ichoice = input()
    try:
        choice = int(ichoice)
        if choice < 0 or choice >= (len(answers)):
            rprint(f"[red]Error : the device number '{choice}' is unkown ![/red]")
            return ask_question(question, answers)
    except ValueError:
        rprint(
            f"[red]Error : Please type a number between 0 and {len(answers) - 1 }[/red]"
        )
        return ask_question(question, answers)
    return choice


def get_supported_device(config_manager: ConfigManager):
    """Get supported devices from configuration."""
    devices = []
    for device_config in config_manager.get_all_devices():
        devices.append([
            device_config.name,
            device_config.avr_device,
            device_config.programmer,
            str(device_config.baud_rate)
        ])
    return devices


def get_serial_ports():
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


def run_update(device, port, file, config_manager: ConfigManager):
    """Run firmware update with device configuration."""
    device_config = config_manager.get_device(device[0])
    if not device_config:
        rprint(f"[red]Error: Device configuration not found for {device[0]}[/red]")
        return
    
    command = f"avrdude -p {device_config.avr_device} -c {device_config.programmer} -b {device_config.baud_rate} -P {port} -U flash:w:{file}:i"
    rprint(f"Command : '{command}'")
    
    if not make_dry_run:
        if config_manager.update_config.confirm_update:
            rprint(
                "Do you wish to execute \[yY] ? [red] (do NOT disconnect device before end of process)"
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


def detect_connected_devices(config_manager: ConfigManager) -> List[DetectedDevice]:
    """Detect connected devices using handshake."""
    detector = DeviceDetector(config_manager)
    detected_devices = detector.detect_devices()
    
    if detected_devices:
        rprint(f"[green]Detected {len(detected_devices)} device(s):[/green]")
        device_list = detector.format_device_list(detected_devices)
        for device_info in device_list:
            rprint(f"  [blue]{device_info}[/blue]")
    else:
        rprint("[yellow]No devices detected via handshake[/yellow]")
    
    return detected_devices


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


def get_available_firmware_for_device(device_name, firmware_index):
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


def download_firmware_list(url):
    """Download the firmware list from the configured URL."""
    try:
        rprint(f"[blue]Downloading firmware list from: {url}[/blue]")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text.strip().split('\n')
    except requests.RequestException as e:
        rprint(f"[red]Error downloading firmware list: {e}[/red]")
        return None


def parse_firmware_list(firmware_list):
    """Parse the firmware list and return a list of firmware info."""
    firmware_files = []
    for line in firmware_list:
        line = line.strip()
        if line and line.startswith('http'):
            # Extract filename from URL
            filename = line.split('/')[-1]
            firmware_files.append({
                'url': line,
                'filename': filename,
                'display_name': filename.replace('.hex', '')
            })
    return firmware_files


def download_firmware_file(firmware_url, temp_dir):
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


def scan_and_detect_devices_with_versions(config_manager, firmware_index):
    """
    Scan all /dev/ttyUSB* and /dev/ttyACM* ports, detect Wanderer devices,
    extract model and version, and return a list of dicts:
    [{ 'port': ..., 'model': ..., 'current_version': ..., 'available_version': ..., 'device_config': ... }]
    """
    ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    detected = []
    for port in ports:
        for baud_rate in config_manager.device_detection_config.baud_rates:
            try:
                import serial
                with serial.Serial(port, baud_rate, timeout=3) as ser:
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()
                    # Read a line or up to 64 bytes
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line:
                        # Try reading raw if readline fails
                        ser.write(b'\n')
                        ser.flush()
                        import time; time.sleep(0.5)
                        if ser.in_waiting > 0:
                            line = ser.read(ser.in_waiting).decode('utf-8', errors='ignore').strip()
                    # Always disconnect after detection (context manager ensures this)
                    # Detection logic
                    if line and 'A' in line:
                        model = line.split('A', 1)[0].strip()
                        version = line.split('A', 2)[1] if line.count('A') >= 1 else ''
                        device_config = config_manager.get_device(model)
                        if device_config:
                            # Get available version from firmware index
                            available_version = None
                            if firmware_index and 'devices' in firmware_index and model in firmware_index['devices']:
                                available_version = firmware_index['devices'][model][0]['version']
                            detected.append({
                                'port': port,
                                'model': model,
                                'current_version': version,
                                'available_version': available_version,
                                'device_config': device_config
                            })
                            break  # Stop trying other baud rates for this port
            except Exception:
                continue
    return detected


def main(firmware_url=None, firmware_file=None, github_repo=None, config_file="config.yml"):
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
    firmware_path = None
    # Mode unique : détection automatique au démarrage
    github_repo = config_manager.firmware_config.github_repo
    if DEBUG_MODE:
        rprint(f"[yellow][DEBUG] github_repo from config: {github_repo}[/yellow]")
    firmware_index = get_firmware_index(github_repo)
    if not firmware_index:
        rprint("[red]Failed to download firmware index. Exiting.[/red]")
        return
    if DEBUG_MODE:
        rprint(f"[yellow][DEBUG] Firmware index loaded: {firmware_index}[/yellow]")
    # Scan all USB/ACM ports for Wanderer devices
    detected = scan_and_detect_devices_with_versions(config_manager, firmware_index)
    if DEBUG_MODE:
        rprint(f"[yellow][DEBUG] Detected devices: {detected}[/yellow]")
    if detected:
        rprint("[green]Appareils Wanderer détectés :[/green]")
        choices = []
        for i, d in enumerate(detected):
            choices.append(f"{d['port']} | {d['model']} | version actuelle: {d['current_version']} | version dispo: {d['available_version']}")
            rprint(f"  [yellow]{i}[/yellow] : [blue]{choices[-1]}")
        rprint("Votre choix : ")
        ichoice = input()
        try:
            choice = int(ichoice)
            if choice < 0 or choice >= len(detected):
                rprint(f"[red]Erreur : numéro invalide[/red]")
                return
        except ValueError:
            rprint(f"[red]Erreur : veuillez entrer un numéro valide[/red]")
            return
        selected = detected[choice]
        # On lance la mise à jour sur ce port et ce modèle
        available_firmware = get_available_firmware_for_device(selected['model'], firmware_index)
        if not available_firmware:
            rprint(f"[red]Aucun firmware trouvé pour {selected['model']}")
            return
        # Trier du plus récent au plus ancien (ordre décroissant)
        available_firmware = sorted(available_firmware, key=lambda fw: fw['version_date'], reverse=True)
        # Proposer le choix de version si plusieurs
        if len(available_firmware) > 1:
            fw_choices = [f"{fw['version']} ({fw['filename']})" for fw in available_firmware]
            fw_index = ask_question(f"Quelle version installer pour {selected['model']} ?", fw_choices)
            selected_firmware = available_firmware[fw_index]
        else:
            selected_firmware = available_firmware[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            firmware_path = download_firmware_file(selected_firmware['url'], temp_dir)
            if not firmware_path:
                rprint("[red]Echec du téléchargement du firmware. Abandon.[/red]")
                return
            run_update(
                [selected['model'], selected['device_config'].avr_device, selected['device_config'].programmer, str(selected['device_config'].baud_rate)],
                selected['port'],
                firmware_path,
                config_manager
            )
        return
    else:
        rprint("[yellow]Aucun appareil Wanderer détecté sur les ports USB/ACM. Arrêt du script.[/yellow]")
        return


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
    if DEBUG_MODE:
        rprint("[yellow][DEBUG] Debug mode enabled[/yellow]")
    main(config_file=args.config)
