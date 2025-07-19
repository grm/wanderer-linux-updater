#!/usr/bin/env python3
"""
Firmware sync script for Wanderer devices.
Downloads firmware files and creates an index for GitHub Pages hosting.
"""

import os
import re
import json
import argparse
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from config_manager import ConfigManager

def download_firmware_list(firmware_url):
    """Download the firmware list from the given URL."""
    try:
        import requests
        print(f"Downloading firmware list from: {firmware_url}")
        response = requests.get(firmware_url, timeout=60)
        response.raise_for_status()
        return response.text.strip().split('\n')
    except Exception as e:
        print(f"Error downloading firmware list: {e}")
        return []

def extract_filename_from_url(url):
    """Extract filename from URL."""
    parsed_url = urlparse(url)
    path = parsed_url.path
    filename = os.path.basename(path)
    return filename

def download_firmware_file(url, filename, firmware_dir):
    """Download a firmware file only if it does not already exist."""
    file_path = firmware_dir / filename
    if file_path.exists():
        print(f"[SKIP] {filename} already exists, skipping download.")
        return file_path.stat().st_size
    try:
        print(f"Downloading: {filename}")
        import requests
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return file_path.stat().st_size
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        return None

def sync_firmwares_from_url(firmware_url):
    """Sync firmwares from the given URL."""
    config_manager = ConfigManager()
    firmware_dir = Path(config_manager.firmware_config.firmware_dir)
    
    # Create firmware directory if it doesn't exist
    firmware_dir.mkdir(exist_ok=True)
    
    # Download firmware list
    firmware_list = download_firmware_list(firmware_url)
    if not firmware_list:
        print("No firmware list downloaded. Exiting.")
        return
    
    print(f"Found {len(firmware_list)} firmware entries")
    
    # Download each firmware file
    downloaded_count = 0
    for line in firmware_list:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Each line is a direct URL to a firmware file
        url = line
        filename = extract_filename_from_url(url)
        
        if filename.endswith('.hex'):
            size = download_firmware_file(url, filename, firmware_dir)
            if size:
                downloaded_count += 1
        else:
            print(f"Skipping non-hex file: {filename}")
    
    print(f"Downloaded {downloaded_count} firmware files")

def generate_index_from_local_firmwares():
    """Generate index from locally downloaded firmware files."""
    config_manager = ConfigManager()
    firmware_dir = Path(config_manager.firmware_config.firmware_dir)
    index_file = Path(config_manager.firmware_config.index_file)
    github_repo = config_manager.firmware_config.github_repo

    # Build index without last_updated first
    index = {
        'source_url': None,
        'devices': {}
    }
    if github_repo:
        index['base_url'] = f"https://{github_repo.split('/')[0]}.github.io/{github_repo.split('/')[1]}/firmwares/"

    # Get all configured device names for validation
    configured_devices = set(config_manager.get_device_names())
    print(f"Configured devices: {sorted(configured_devices)}")
    
    processed_files = 0
    matched_devices = set()
    unmatched_files = []

    for file in firmware_dir.glob('*.hex'):
        filename = file.name
        match = re.match(r'^([^-]+)-(\d{8})\.hex$', filename)
        if match:
            device_name = match.group(1)
            version_date = match.group(2)
            
            # Validate that device is configured
            if device_name in configured_devices:
                matched_devices.add(device_name)
                print(f"✅ Matched: {filename} -> {device_name}")
            else:
                unmatched_files.append(filename)
                print(f"⚠️  Unmatched: {filename} -> {device_name} (not in config)")
                continue
            
            try:
                version = datetime.strptime(version_date, '%Y%m%d').strftime('%Y-%m-%d')
            except Exception:
                version = version_date
            size = file.stat().st_size
            if device_name not in index['devices']:
                index['devices'][device_name] = []
            url = f"{index['base_url']}{filename}" if 'base_url' in index else filename
            index['devices'][device_name].append({
                'filename': filename,
                'version': version,
                'version_date': version_date,
                'size': size,
                'url': url,
                'original_url': None,
                'device_config': {
                    'avr_device': config_manager.get_device(device_name).avr_device if config_manager.get_device(device_name) else '',
                    'programmer': config_manager.get_device(device_name).programmer if config_manager.get_device(device_name) else '',
                    'baud_rate': config_manager.get_device(device_name).baud_rate if config_manager.get_device(device_name) else ''
                }
            })
            processed_files += 1
        else:
            print(f"⚠️  Invalid filename format: {filename}")
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"  - Processed files: {processed_files}")
    print(f"  - Matched devices: {len(matched_devices)}")
    print(f"  - Unmatched files: {len(unmatched_files)}")
    
    if unmatched_files:
        print(f"  - Unmatched files: {unmatched_files}")
    
    # Check for configured devices without firmware
    missing_devices = configured_devices - matched_devices
    if missing_devices:
        print(f"  - Missing firmware for devices: {sorted(missing_devices)}")
    
    # Sort by version_date descending (most recent first)
    for device in index['devices']:
        index['devices'][device].sort(key=lambda x: x['version_date'], reverse=True)

    # Compare with existing index file (excluding last_updated)
    new_index_json = json.dumps(index, indent=2, sort_keys=True)
    if index_file.exists():
        with open(index_file, 'r') as f:
            old_index = json.load(f)
        # Remove last_updated from old index for comparison
        if 'last_updated' in old_index:
            del old_index['last_updated']
        old_index_json = json.dumps(old_index, indent=2, sort_keys=True)
        if new_index_json == old_index_json:
            print("No change in firmware index. Skipping file write and last_updated update.")
            return
    # Only now add last_updated and write the file
    index['last_updated'] = datetime.now().isoformat()
    with open(index_file, 'w') as f:
        json.dump(index, f, indent=2, sort_keys=True)
    print(f"Index generated with {sum(len(v) for v in index['devices'].values())} firmwares in {len(index['devices'])} models.")
    print(f"Index file: {index_file.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync firmware files from URL")
    parser.add_argument("--firmware-url", 
                       required=True,
                       help="URL to download firmware list from")
    args = parser.parse_args()
    
    # Sync firmwares from URL
    sync_firmwares_from_url(args.firmware_url)
    
    # Generate index from downloaded files
    generate_index_from_local_firmwares() 