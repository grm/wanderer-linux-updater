# Wanderer linux updater

This python script aims to automate updating new firmwares on wanderer astro (https://www.wandererastro.com/en/) on Linux.

# Installation

You need to install `avrdude` package under linux. This script calls the binary directly.

```bash
$ sudo apt install avrdude
$ pip install pyserial rich
$ git clone https://github.com/grm/wanderer-linux-updater
$ cd wanderer-linux-updater
```

#  Update

Simply go into your installation directory and update the repository :
```bash
$ cd wanderer-linux-updater
$ git pull
```

# Usage

To update your device, you first need to download the correct firmware for your device here : https://www.wandererastro.com/en/col.jsp?id=106.

This script guides you through the different step.
Before starting, you need :
- to know which model of device you want to update (should be easy to find)
- the serial port the device is connected to (something like `/dev/ttyUSB0`)

Once you are ready, you can launch the program by executing in a terminal :
```bash
$ python updater.py /path/to/the/firmware.hex
```

The script will : 
- first ask you which device you want to update (just type the corresponding number)
- then ask you on which port is connected the device : just type the right number for the device
- ask you a confirmation to flash the device. You can answer `y` or `Y`. IT IS VERY IMPORTANT TO NOT DISCONNECT THE DEVICE BEFORE THE END OF THE PROCESS.

# Screenshot

![screenshot](img/screenshot.png)
