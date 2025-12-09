# Meshtastic ↔ Packet Radio Bridge

A robust bidirectional bridge between Meshtastic (MQTT) and AX.25 Packet Radio using Direwolf KISS TNC. Designed for Motorola CDM series radios with RIM-MAXTRAC interfaces on Raspberry Pi.

## Features

- ✅ **Bidirectional relay**: MQTT ↔ RF with byte-for-byte payload integrity
- ✅ **Topic preservation**: MQTT topics preserved end-to-end across RF link
- ✅ **Loop prevention**: Digest-based deduplication prevents message storms
- ✅ **Auto-reconnection**: Handles Direwolf and Mosquitto restarts gracefully
- ✅ **AX.25 UI frames**: Standard packet radio protocol with configurable callsigns
- ✅ **KISS TCP**: Clean interface to Direwolf TNC
- ✅ **FCC compliant**: No encryption over RF, callsigns in the clear
- ✅ **Comprehensive logging**: INFO and DEBUG levels for troubleshooting

## Hardware Requirements

- **Radio**: Motorola CDM series (CDM1250, CDM1550, etc.)
- **Interface**: RIM-MAXTRAC soundcard interface
- **Computer**: Raspberry Pi (3B+ or newer recommended)
- **OS**: Raspberry Pi OS 13 Minimal
- **Antenna**: Appropriate for your frequency band
- **License**: Valid amateur radio license (required for operation)

## Software Components

- **Direwolf**: Software TNC providing KISS interface
- **Mosquitto**: MQTT broker
- **Python 3**: Bridge service runtime
- **paho-mqtt**: MQTT client library
- **pyyaml**: Configuration file parser

## Installation

### Quick Install

```bash
# Clone or download the repository
cd /path/to/Meshtastic_Packet_Bridge

# Run installer from the install folder (requires root)
sudo bash install/install.sh
```

The installer will:
1. Update system packages
2. Install Direwolf, Mosquitto, Python dependencies
3. Create virtual environment at `/opt/msh-bridge`
4. Install Python packages (paho-mqtt, pyyaml)
5. Copy service files
6. Install and enable systemd service

### Manual Installation

If you prefer manual installation:

```bash
# Install system packages
sudo apt-get update
sudo apt-get install -y direwolf mosquitto mosquitto-clients python3 python3-pip python3-venv alsa-utils

# Create directories
sudo mkdir -p /opt/msh-bridge
sudo mkdir -p /var/log/direwolf

# Create virtual environment
python3 -m venv /opt/msh-bridge/venv

# Install Python packages
/opt/msh-bridge/venv/bin/pip install paho-mqtt pyyaml

# Copy files from install folder
sudo cp install/msh_bridge.py install/config.yaml install/direwolf.conf /opt/msh-bridge/
sudo cp install/msh-bridge.service install/direwolf.service /etc/systemd/system/

# Set permissions
sudo chown -R {user}:{user} /opt/msh-bridge
sudo chown -R {user}:{group} /var/log/direwolf

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable msh-bridge
```

## Configuration

### 1. Edit Bridge Configuration

Edit `/opt/msh-bridge/config.yaml`:

```yaml
mqtt:
  host: 127.0.0.1          # MQTT broker address
  port: 1883               # MQTT broker port
  username: meshnerds      # MQTT username
  password: TacosAreTasty69  # MQTT password
  tls: false               # Enable TLS (true/false)
  root_topic: msh/bridge   # Root topic to bridge

ax25:
  kiss_host: 127.0.0.1     # Direwolf KISS host
  kiss_port: 8001          # Direwolf KISS port
  source_callsign: N0CALL-1  # YOUR callsign with SSID
  dest_callsign: APMESH  # Destination callsign

loop_prevention:
  enabled: true            # Enable loop prevention
  cache_ttl_seconds: 60    # Dedup cache TTL

logging_level: INFO        # DEBUG, INFO, WARNING, ERROR
```

**⚠️ IMPORTANT**: Change `source_callsign` to your actual amateur radio callsign!

### 2. Configure Direwolf Audio

Find your audio device:

```bash
aplay -l   # List playback devices
arecord -l # List capture devices
```

Edit `/opt/msh-bridge/direwolf.conf`:

```conf
# Set your audio device (example: card 1, device 0)
ADEVICE plughw:0,0 plughw:0,0

# Configure PTT for your CM108 Sound card
PTT CM108 /dev/hidraw0

# For serial RTS:
# PTT /dev/ttyUSB0 RTS
```

Adjust transmit timing for your radio:

```conf
TXDELAY 250  # PTT to audio delay (ms) - CDM typically needs 200-300
TXTAIL 50    # Audio to PTT release (ms)
```

### 3. Configure Mosquitto

Create password file if using authentication:

```bash
sudo mosquitto_passwd -c /etc/mosquitto/pwfile meshnerds
sudo systemctl restart mosquitto
```

## Operation

### Start Direwolf

Option 1: Run manually (recommended for initial testing):

```bash
direwolf -c /opt/msh-bridge/direwolf.conf
```

Option 2: Create systemd service (for production):

Create `/etc/systemd/system/direwolf.service`:

```ini
[Unit]
Description=Direwolf KISS TNC
After=sound.target

[Service]
Type=simple
User=pi
ExecStart=/usr/bin/direwolf -c /opt/msh-bridge/direwolf.conf
Restart=always

[Install]
WantedBy=multi-user.target
```

Then enable:

```bash
sudo systemctl enable direwolf
sudo systemctl start direwolf
```

### Start Bridge Service

```bash
# Start service
sudo systemctl start msh-bridge

# Check status
sudo systemctl status msh-bridge

# View logs
sudo journalctl -u msh-bridge -f

# Stop service
sudo systemctl stop msh-bridge

# Restart service
sudo systemctl restart msh-bridge
```

### Monitor Logs

```bash
# Follow bridge logs
sudo journalctl -u msh-bridge -f

# Follow Direwolf logs (if running as service)
sudo journalctl -u direwolf -f

# View last 100 lines
sudo journalctl -u msh-bridge -n 100

# View logs with DEBUG level
# First, edit /opt/msh-bridge/config.yaml and set logging_level: DEBUG
# Then restart: sudo systemctl restart msh-bridge
```

## Testing

### Test MQTT → RF Path

On Site A:

```bash
# Publish test message
mosquitto_pub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/test -m "Hello from Site A"

# Monitor bridge logs
sudo journalctl -u msh-bridge -f
```

You should see:
- Bridge log: `MQTT→RF: msh/bridge/test (17 bytes)`
- Direwolf should transmit the packet
- Remote site should receive and publish to MQTT

### Test RF → MQTT Path

On Site A, subscribe to MQTT:

```bash
mosquitto_sub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/# -v
```

Have Site B publish a message. You should see it appear on Site A's MQTT.

### Verify Payload Integrity

Send a binary payload and verify byte-for-byte match:

```bash
# Site A: Publish binary data
echo -n "Binary test: $(date +%s)" | mosquitto_pub -h 127.0.0.1 \
  -u meshnerds -P TacosAreTasty69 -t msh/bridge/integrity -s

# Site B: Subscribe and capture
mosquitto_sub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/integrity -C 1 > received.bin

# Compare with original
sha256sum received.bin original.bin
```

### Test Loop Prevention

Send the same message twice quickly:

```bash
mosquitto_pub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/test -m "Duplicate test"
  
mosquitto_pub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/test -m "Duplicate test"
```

Check logs - second message should be marked as duplicate:
```
Skipping duplicate message: msh/bridge/test
```

### Test Reconnection

```bash
# Restart Direwolf
sudo systemctl restart direwolf

# Watch bridge logs - should reconnect automatically
sudo journalctl -u msh-bridge -f
```

## Troubleshooting

### Bridge won't start

```bash
# Check service status
sudo systemctl status msh-bridge

# Check logs for errors
sudo journalctl -u msh-bridge -n 50

# Common issues:
# - Config file syntax error: check /opt/msh-bridge/config.yaml
# - MQTT connection failed: verify Mosquitto is running
# - KISS connection failed: verify Direwolf is running
```

### No RF transmission

```bash
# Check Direwolf is running
ps aux | grep direwolf

# Check KISS connection
sudo journalctl -u msh-bridge | grep KISS

# Test Direwolf manually
direwolf -c /opt/msh-bridge/direwolf.conf

# Check audio levels
alsamixer
```

### No RF reception

```bash
# Verify Direwolf is decoding packets
# Look for decoded packets in Direwolf output

# Check AX.25 addressing
# Bridge only processes frames addressed to dest_callsign

# Enable DEBUG logging
# Edit config.yaml: logging_level: DEBUG
sudo systemctl restart msh-bridge
```

### MQTT not publishing

```bash
# Check MQTT connection
mosquitto_sub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 -t '$SYS/#' -C 1

# Verify credentials in config.yaml
# Check Mosquitto logs
sudo journalctl -u mosquitto -f
```

### Loop prevention too aggressive

If legitimate messages are being blocked:

```yaml
# Increase cache TTL or disable
loop_prevention:
  enabled: false  # Disable for testing
  cache_ttl_seconds: 30  # Reduce TTL
```

## Two-Site Deployment Runbook

### Site A Setup

1. Install hardware: CDM radio + RIM-MAXTRAC + Raspberry Pi
2. Run `install.sh`
3. Edit `/opt/msh-bridge/config.yaml`:
   - Set `source_callsign: YOURCALL-1`
   - Set MQTT credentials
4. Configure Direwolf audio device
5. Test Direwolf: `direwolf -c /opt/msh-bridge/direwolf.conf`
6. Start services:
   ```bash
   sudo systemctl start direwolf
   sudo systemctl start msh-bridge
   ```
7. Verify logs: `sudo journalctl -u msh-bridge -f`

### Site B Setup

1. Repeat Site A steps 1-7
2. Use different callsign: `source_callsign: YOURCALL-2`
3. Ensure same `dest_callsign` on both sites (e.g., `APMESH-0`)

### Verification

1. Site A: Publish to MQTT
2. Site B: Subscribe to MQTT and verify receipt
3. Site B: Publish to MQTT
4. Site A: Subscribe to MQTT and verify receipt
5. Verify topics match end-to-end
6. Verify payloads are identical (hash comparison)

## Performance Tuning

### Optimize for throughput

```yaml
# Reduce loop prevention TTL
loop_prevention:
  cache_ttl_seconds: 30
```

```conf
# In direwolf.conf, reduce delays
TXDELAY 200
TXTAIL 30
```

### Optimize for reliability

```conf
# Increase delays for marginal links
TXDELAY 300
TXTAIL 100

# Reduce PERSIST for busy channels
PERSIST 32
```

## FCC Compliance Notes

This bridge is designed for amateur radio use and complies with FCC Part 97:

- ✅ No encryption over RF (plaintext transmission)
- ✅ Station identification via AX.25 callsign addressing
- ✅ Callsigns visible in transmitted frames
- ⚠️ **You must use your own amateur radio callsign**
- ⚠️ **Ensure proper station identification per Part 97.119**

## Protocol Details

### RF Payload Wrapper Format

```
Byte 0:        Version (0x01)
Byte 1:        Topic length (N)
Bytes 2..N+1:  UTF-8 topic string
Bytes N+2..:   Original MQTT payload (unmodified)
```

### AX.25 UI Frame Format

```
Bytes 0-6:     Destination callsign (APMESH-0)
Bytes 7-13:    Source callsign (YOUR-SSID)
Byte 14:       Control (0x03 = UI)
Byte 15:       PID (0xF0 = No Layer 3)
Bytes 16+:     Wrapped payload
```

### Message Flow

**MQTT → RF:**
1. Subscribe to `{root_topic}/#`
2. Receive MQTT message (topic + payload)
3. Check loop prevention cache
4. Wrap: version + topic_len + topic + payload
5. Encode AX.25 UI frame
6. Send via KISS TCP to Direwolf
7. Direwolf transmits on RF

**RF → MQTT:**
1. Direwolf receives RF packet
2. Decode via KISS TCP
3. Decode AX.25 UI frame
4. Check destination callsign matches config
5. Unwrap: extract topic and payload
6. Check loop prevention cache
7. Publish to MQTT with original topic

## License

This project is released under the MIT License. See LICENSE file for details.

## Contributing

Contributions welcome! Please submit issues and pull requests on GitHub.

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/msh-bridge
- Amateur Radio: Contact via your local repeater or HF net

## Acknowledgments

- Direwolf by WB2OSZ
- Meshtastic project
- Eclipse Paho MQTT
- Amateur radio community

---

**73 de [YOUR CALL]**





