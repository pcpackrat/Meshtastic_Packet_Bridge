# Test and Monitoring Tools

This directory contains scripts for testing and monitoring the Meshtastic Bridge.

## Testing Scripts

### `test_mqtt_to_rf.sh`
Tests the MQTT → RF path by publishing a test message to MQTT and verifying it's transmitted over RF.

**Usage:**
```bash
./test_mqtt_to_rf.sh
```

### `test_rf_to_mqtt.sh`
Tests the RF → MQTT path by simulating an RF packet and verifying it appears on MQTT.

**Usage:**
```bash
./test_rf_to_mqtt.sh
```

### `verify_integrity.py`
Verifies byte-for-byte integrity of packets through the bridge to ensure no data corruption.

**Usage:**
```bash
python3 verify_integrity.py
```

## Monitoring Scripts

### `monitor_mqtt.py` / `monitor_mqtt.sh`
Real-time MQTT message monitor that displays all messages on the local broker.

**Features:**
- Connects to local Mosquitto broker
- Shows timestamps, topics, and payloads
- Decodes JSON, text, and binary data
- Message statistics

**Usage:**
```bash
./monitor_mqtt.sh
# or
python3 monitor_mqtt.py
```

### `monitor_rf.py` / `monitor_rf.sh`
Real-time RF transmission monitor (connects to Direwolf KISS interface).

**Features:**
- Monitors KISS interface on port 8001
- Decodes AX.25 packets
- Shows callsigns and hex data
- Transmission statistics

**Usage:**
```bash
./monitor_rf.sh
# or
python3 monitor_rf.py
```

## Quick Start

Make all scripts executable:
```bash
chmod +x *.sh *.py
```

Run a complete test:
```bash
# Start monitoring in one terminal
./monitor_mqtt.sh

# In another terminal, run tests
./test_mqtt_to_rf.sh
./test_rf_to_mqtt.sh
```
