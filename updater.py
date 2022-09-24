from ast import arg
from random import choices
import sys
import glob
from typing import IO, Optional
import serial
from rich import print as rprint
import rich
from rich.panel import Panel
import csv
import os
from os import path
import argparse

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
        rprint(f"[red]Error : Please type a number between 0 and {len(answers) - 1 }[/red]")
        return ask_question(question, answers)
    return choice

def get_supported_device():
    devices = []
    with open('devices.txt') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';')
        for row in csv_reader:
            devices.append(row)
    return devices

def get_serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

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
        rprint("Do you wish to execute \[yY] ? [red] (do NOT disconnect device before end of process)")
        execution_order = input()
        if execution_order is "y" or execution_order == "Y":
            os.system(command)
            rprint("[green] Firmware update done. You can eject device.")
        else:
            rprint("[red] Aborting ..")

def main(filename):
    rprint(Panel("[green]Welcome to [red]Wanderer astro[/red] linux update tool ![/green]"))
    supported_devices = get_supported_device()
    supported_devices_index = ask_question("What device you wish to update ?", supported_devices)
    
    serial_ports = get_serial_ports()
    serial_port_index = ask_question("Which port the device is connected to ?", serial_ports)

    run_update(supported_devices[supported_devices_index], serial_ports[serial_port_index], filename)


if __name__ == '__main__':
    parser = WandererParser(description='WandererLinuxUpdater help')
    parser.add_argument("-f", required=True, type=str, help="Hex file containind the new firmware")
    parser.add_argument("-d", action='store_true', help="Do a dry run (pint avr command instead of executing it")

    args = parser.parse_args()
    if not path.exists(args.f): 
        rprint('[red]Error: The argument provided is not a file\n')
        parser.print_help()
        exit(1)
    make_dry_run = args.d
    main(args.f)
    