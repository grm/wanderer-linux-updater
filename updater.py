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
from typing import IO, Optional

make_dry_run = False


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


def get_supported_device():
    devices = []
    with open("devices.txt") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=";")
        for row in csv_reader:
            devices.append(row)
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


def run_update(device, port, file):
    command = f"avrdude -p {device[1]} -c {device[2]} -b {device[3]}  -P {port} -U flash:w:{file}:i"
    rprint(f"Command : '{command}'")
    if not make_dry_run:
        rprint(
            "Do you wish to execute \[yY] ? [red] (do NOT disconnect device before end of process)"
        )
        execution_order = input()
        if execution_order == "y" or execution_order == "Y":
            os.system(command)
            rprint("[green] Firmware update done. You can eject device.")
        else:
            rprint("[red] Aborting ..")


def main(firmware_url):
    rprint(
        Panel("[green]Welcome to [red]Wanderer astro[/red] linux update tool ![/green]")
    )
    
    # Download and parse firmware list
    firmware_list = download_firmware_list(firmware_url)
    if not firmware_list:
        rprint("[red]Failed to download firmware list. Exiting.[/red]")
        return
    
    firmware_files = parse_firmware_list(firmware_list)
    if not firmware_files:
        rprint("[red]No firmware files found in the list. Exiting.[/red]")
        return
    
    # Display available firmware files
    firmware_names = [fw['display_name'] for fw in firmware_files]
    firmware_index = ask_question(
        "Which firmware would you like to install?", firmware_names
    )
    
    selected_firmware = firmware_files[firmware_index]
    
    # Get device selection
    supported_devices = get_supported_device()
    supported_devices_index = ask_question(
        "What device you wish to update ?", supported_devices
    )

    # Get serial port selection
    serial_ports = get_serial_ports()
    serial_port_index = ask_question(
        "Which port the device is connected to ?", serial_ports
    )

    # Create temporary directory for firmware download
    with tempfile.TemporaryDirectory() as temp_dir:
        # Download the selected firmware
        firmware_path = download_firmware_file(selected_firmware['url'], temp_dir)
        if not firmware_path:
            rprint("[red]Failed to download firmware. Exiting.[/red]")
            return
        
        # Run the update
        run_update(
            supported_devices[supported_devices_index],
            serial_ports[serial_port_index],
            firmware_path,
        )


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


if __name__ == "__main__":
    parser = WandererParser(description="WandererLinuxUpdater help")
    parser.add_argument(
        "-u", "--url", 
        type=str, 
        required=True,
        help="URL to firmware list (required)"
    )
    parser.add_argument(
        "-d",
        action="store_true",
        help="Do a dry run (pint avr command instead of executing it",
    )

    args = parser.parse_args()
    make_dry_run = args.d
    
    # Use the provided URL
    firmware_url = args.url
    
    # Create a modified main function that uses the specified URL
    def main_with_url(url):
        main(url)
    
    main_with_url(firmware_url)
