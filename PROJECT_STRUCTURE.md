# Project Structure

```
Meshtastic Full Bridge/
├── install/                   # Installation files
│   ├── msh_bridge.py         # Main bridge service
│   ├── config.yaml           # Configuration file
│   ├── direwolf.conf         # Direwolf TNC configuration
│   ├── mosquitto.conf        # Mosquitto MQTT broker configuration
│   ├── msh-bridge.service    # Bridge systemd unit file
│   ├── direwolf.service      # Direwolf systemd unit file
│   └── install.sh            # Automated installer script
│
├── test/                      # Test and monitoring tools
│   ├── test_mqtt_to_rf.sh    # MQTT→RF test script
│   ├── test_rf_to_mqtt.sh    # RF→MQTT test script
│   ├── verify_integrity.py   # Payload verification tool
│   ├── monitor_mqtt.py       # MQTT message monitor
│   ├── monitor_mqtt.sh       # MQTT monitor launcher
│   ├── monitor_rf.py         # RF transmission monitor
│   ├── monitor_rf.sh         # RF monitor launcher
│   └── README.md             # Test tools documentation
│
├── .gitignore                 # Git ignore rules
├── LICENSE                    # MIT License
├── README.md                  # Comprehensive documentation
├── TESTING.md                 # Testing guide
└── PROJECT_STRUCTURE.md       # This file
```

## Installation Files (`install/`)

All files required for deployment are in the `install/` directory:

- **msh_bridge.py** - Main Python service implementing the bridge
- **config.yaml** - Configuration with MQTT, AX.25, and loop prevention settings
- **direwolf.conf** - Direwolf TNC configuration for CM108 PTT
- **mosquitto.conf** - Mosquitto MQTT broker configuration
- **msh-bridge.service** - Systemd unit for bridge service
- **direwolf.service** - Systemd unit for Direwolf TNC
- **install.sh** - Automated installation script with:
  - Root user prevention (requires sudo from regular user)
  - Dynamic user detection and file ownership
  - Mosquitto auto-configuration with authentication
  - Direwolf callsign synchronization from config.yaml
  - Service user configuration

## Test and Monitoring Tools (`test/`)

All testing and monitoring scripts are organized in the `test/` directory:

### Testing Scripts
- **test_mqtt_to_rf.sh** - Test MQTT→RF message path
- **test_rf_to_mqtt.sh** - Monitor RF→MQTT message path
- **verify_integrity.py** - Verify payload integrity (byte-for-byte)

### Monitoring Tools
- **monitor_mqtt.py** - Real-time MQTT message monitor
- **monitor_mqtt.sh** - Convenience launcher for MQTT monitor
- **monitor_rf.py** - Real-time RF transmission monitor
- **monitor_rf.sh** - Convenience launcher for RF monitor

See `test/README.md` for detailed usage instructions.

## Documentation (root)

- **README.md** - Complete documentation including installation, configuration, operation, and troubleshooting
- **TESTING.md** - Detailed testing procedures and debugging guide
- **PROJECT_STRUCTURE.md** - This file, project organization overview
- **.gitignore** - Git ignore rules for Python, IDE, and OS files
- **LICENSE** - MIT License

## Quick Start

```bash
# Transfer to Raspberry Pi
scp -r "Meshtastic Full Bridge" pi@raspberrypi.local:~/

# SSH and install
ssh pi@raspberrypi.local
cd "Meshtastic Full Bridge"
sudo ./install/install.sh

# Configure (edit callsign and MQTT credentials)
sudo nano /opt/msh-bridge/config.yaml

# Configure audio device (optional)
sudo nano /opt/msh-bridge/direwolf.conf

# Start services
sudo systemctl start direwolf
sudo systemctl start msh-bridge

# Monitor
sudo journalctl -u msh-bridge -f

# Test (from test directory)
cd test
./monitor_mqtt.sh  # In one terminal
./test_mqtt_to_rf.sh  # In another terminal
```

