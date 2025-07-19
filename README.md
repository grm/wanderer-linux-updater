# Wanderer Linux Updater

A firmware update tool for Wanderer Astro devices, with manual device selection and firmware synchronization via GitHub.

**[Lire en français](README.fr.md)**

## Features

- **YAML Configuration** : Centralized and flexible configuration
- **Manual device selection** : User interface to choose device type
- **USB port detection** : Automatic detection of available serial ports
- **Automatic synchronization** : GitHub Actions to sync firmwares
- **GitHub Pages hosting** : Firmwares hosted reliably
- **Multi-device support** : All Wanderer devices supported

## Installation

1. Clone the repository :
```bash
git clone https://github.com/your-username/wanderer-linux-updater.git
cd wanderer-linux-updater
```

2. Install dependencies using pipenv :
```bash
pipenv install
```

3. Configure your `config.yml` file (see Configuration section)

## Configuration

The `config.yml` file contains all configuration :

```yaml
# Firmware configuration
firmware:
  source_url: "https://od.lk/d/MzNfMzIzNTQ2OTNf/FirmwareDownloadList.txt"
  github_repo: "your-username/wanderer-linux-updater"
  sync_interval_hours: 6

# Device detection configuration (for testing and debugging)
device_detection:
  handshake_timeout: 5
  port_detection_timeout: 3

# Device definitions
devices:
  WandererBoxPlusV3:
    avr_device: "m168p"
    programmer: "arduino"
    baud_rate: 115200
    handshake_baud_rate: 19200
    handshake_command: "ZXWBPlusV3"
    handshake_response: "ZXWBPlusV3"
```

## Usage

### Interactive update (recommended)

```bash
# Launch the interactive update tool
pipenv run python updater.py
```

The tool will guide you through the following steps :
1. **Device type selection** : Choose from configured devices
2. **Serial port selection** : Choose from available USB ports
3. **Connection test** : Optional verification of device presence
4. **Firmware selection** : Choose the firmware version to install
5. **Update** : Execute the update

### Additional options

```bash
# Use a custom configuration file
pipenv run python updater.py --config my-config.yml

# Dry-run mode (shows the command without executing it)
pipenv run python updater.py --dry-run

# Debug mode
pipenv run python updater.py --debug
```

## Utility scripts

### List configured devices

```bash
# Display all configured devices with their parameters
pipenv run python list_devices.py
```

### Test USB port detection

```bash
# Test detection of available serial ports
pipenv run python test_ports.py
```

### Test automatic detection (optional)

```bash
# Test automatic device detection via handshake
pipenv run python test_detection.py
```

## Automatic synchronization

The GitHub Actions workflow automatically synchronizes firmwares :

1. **Activation** : The workflow runs every 6 hours
2. **Download** : Retrieves firmware list from configured URL
3. **Hosting** : Firmwares are hosted on GitHub Pages
4. **Index** : A JSON index file is generated with metadata

### GitHub Pages configuration

1. Go to Settings > Pages
2. Source : "Deploy from a branch"
3. Branch : `main` (or your main branch)
4. Folder : `/ (root)`

## File structure

```
wanderer-linux-updater/
├── .github/workflows/sync-firmware.yml  # GitHub Actions workflow
├── scripts/sync_firmware.py             # Synchronization script
├── config.yml                           # Main configuration
├── config_manager.py                    # Configuration manager
├── device_detector.py                   # Device detection (for testing)
├── updater.py                          # Main interactive script
├── test_detection.py                   # Automatic detection test
├── test_ports.py                       # Port detection test
├── list_devices.py                     # Configured devices list
├── firmware/                           # Firmwares (auto-generated)
├── firmware_index.json                 # Firmware index (auto-generated)
└── README.md
```

## Supported devices

- WandererBoxPlusV3 
- WandererBoxProV3 (Tested ✔️)
- WandererCoverV3
- WandererCover V4/V4Pro (Tested ✔️)
- WandererDewTerminator
- WandererEclipse
- WandererRotatorLiteV1/V2
- WandererRotatorMini (Tested ✔️)
- WandererRotatorProV1/V2
- WandererETA54

## Advanced configuration

### Adding a new device

Add a new entry in the `devices` section of `config.yml` :

```yaml
devices:
  MyNewDevice:
    avr_device: "m328p"
    programmer: "arduino"
    baud_rate: 115200
    handshake_baud_rate: 19200
    handshake_command: "MyCommand"      # Optional: command to send
    handshake_response: "MyResponse"    # Required: expected response
```

### Handshake configuration

Each device can have specific handshake behavior:

- **`handshake_command`** : Optional command to send to the device
- **`handshake_response`** : Required expected response from the device
- **`handshake_baud_rate`** : Optional baud rate for handshake (defaults to `baud_rate`)

### Device detection configuration

```yaml
device_detection:
  handshake_timeout: 5        # Timeout for handshake operations (seconds)
  port_detection_timeout: 3   # Timeout for port detection (seconds)
```

### Update configuration

```yaml
update:
  confirm_update: true        # Ask for confirmation before update
  dry_run: false             # Dry-run mode
```

## Troubleshooting

### No ports detected

1. Verify that the device is connected via USB
2. Test with `pipenv run python test_ports.py`
3. Check permissions on `/dev/tty*` (Linux)
4. Install appropriate USB drivers

### Configuration errors

```bash
# Validate configuration
pipenv run python -c "from config_manager import ConfigManager; ConfigManager().validate_config()"
```

### Update issues

1. Verify that the device is in bootloader mode
2. Ensure `avrdude` is installed
3. Check serial port permissions
4. Test with `--dry-run` mode first

### Firmware download errors

1. Check internet connectivity
2. Verify firmware URL in configuration
3. Verify that GitHub repository is correctly configured

## Development

### Using pipenv

This project uses [pipenv](https://pipenv.pypa.io/) for dependency management. Here are the key commands:

```bash
# Install dependencies
pipenv install

# Run a script in the virtual environment
pipenv run python script.py

# Activate the virtual environment
pipenv shell

# Add a new dependency
pipenv install package_name

# Add a development dependency
pipenv install --dev package_name
```

## Contributing

1. Fork the repository
2. Create a branch for your feature
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License. See the LICENSE file for details.
