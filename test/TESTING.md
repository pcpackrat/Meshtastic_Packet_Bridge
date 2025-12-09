# Testing Guide

This directory contains test scripts and tools for validating the Meshtastic Bridge.

## Test Scripts

### test_mqtt_to_rf.sh

Tests the MQTT → RF path by publishing various test messages to MQTT.

**Usage:**
```bash
chmod +x test_mqtt_to_rf.sh
./test_mqtt_to_rf.sh
```

**Environment variables:**
- `MQTT_HOST` - MQTT broker host (default: 127.0.0.1)
- `MQTT_PORT` - MQTT broker port (default: 1883)
- `MQTT_USER` - MQTT username (default: meshnerds)
- `MQTT_PASS` - MQTT password (default: TacosAreTasty69)
- `MQTT_TOPIC` - Test topic (default: msh/bridge/test)

**Tests performed:**
1. Simple text message
2. Binary payload
3. Long topic path
4. Large payload (~200 bytes)

### test_rf_to_mqtt.sh

Tests the RF → MQTT path by subscribing to MQTT and displaying received messages.

**Usage:**
```bash
chmod +x test_rf_to_mqtt.sh
./test_rf_to_mqtt.sh
```

**Environment variables:** (same as above)

### verify_integrity.py

Verifies payload integrity by comparing files or computing hashes.

**Usage:**
```bash
# Compare two files
python3 verify_integrity.py sent.bin received.bin

# Compute hash of single file
python3 verify_integrity.py data.bin

# Compute hash of string
python3 verify_integrity.py -s "Test message"
```

## End-to-End Test Procedure

### Prerequisites

- Two sites (Site A and Site B) with bridge installed
- Both sites on same RF frequency
- Both sites with working Direwolf and MQTT

### Test 1: MQTT → RF → MQTT

**Site A:**
```bash
# Terminal 1: Monitor logs
sudo journalctl -u msh-bridge -f

# Terminal 2: Publish test message
mosquitto_pub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/test -m "Hello from Site A"
```

**Site B:**
```bash
# Subscribe and wait for message
mosquitto_sub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/test -v
```

**Expected result:** Message appears on Site B MQTT with same topic and payload.

### Test 2: Payload Integrity

**Site A:**
```bash
# Create test file
echo "Integrity test payload $(date)" > test_sent.txt

# Publish file
mosquitto_pub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/integrity -f test_sent.txt

# Compute hash
python3 verify_integrity.py test_sent.txt
```

**Site B:**
```bash
# Subscribe and save to file
mosquitto_sub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/integrity -C 1 > test_received.txt

# Compute hash
python3 verify_integrity.py test_received.txt
```

**Verify:**
```bash
# Compare hashes - should be identical
python3 verify_integrity.py test_sent.txt test_received.txt
```

### Test 3: Bidirectional

Repeat Test 1 but publish from Site B and subscribe on Site A.

### Test 4: Loop Prevention

**Site A:**
```bash
# Publish same message twice quickly
mosquitto_pub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/loop -m "Duplicate test"

mosquitto_pub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/loop -m "Duplicate test"

# Check logs
sudo journalctl -u msh-bridge -n 20
```

**Expected result:** Logs show "Skipping duplicate message" for second transmission.

### Test 5: Reconnection

**Site A:**
```bash
# Restart Direwolf
sudo systemctl restart direwolf

# Watch bridge logs - should show reconnection
sudo journalctl -u msh-bridge -f
```

**Expected result:** Bridge reconnects automatically within 1-60 seconds.

### Test 6: Topic Preservation

**Site A:**
```bash
# Publish to multiple topics
mosquitto_pub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/topic1 -m "Message 1"

mosquitto_pub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/topic2/subtopic -m "Message 2"
```

**Site B:**
```bash
# Subscribe to all topics
mosquitto_sub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/# -v
```

**Expected result:** Messages appear with exact original topics.

## Automated Test Suite

For comprehensive testing, run all tests in sequence:

```bash
#!/bin/bash
# run_all_tests.sh

echo "Starting comprehensive bridge tests..."

# Test MQTT→RF
echo "Test 1: MQTT→RF"
./test_mqtt_to_rf.sh
sleep 5

# Test integrity
echo "Test 2: Payload Integrity"
echo "Test payload" > /tmp/test_sent.txt
mosquitto_pub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/integrity -f /tmp/test_sent.txt

# On remote site, capture and compare
# (Manual step required)

echo "All tests complete. Check logs and remote site."
```

## Debugging Tests

### Enable DEBUG logging

Edit `/opt/msh-bridge/config.yaml`:
```yaml
logging_level: DEBUG
```

Restart bridge:
```bash
sudo systemctl restart msh-bridge
```

### View detailed logs

```bash
# Follow logs with DEBUG output
sudo journalctl -u msh-bridge -f

# Search for specific events
sudo journalctl -u msh-bridge | grep "MQTT→RF"
sudo journalctl -u msh-bridge | grep "RF→MQTT"
sudo journalctl -u msh-bridge | grep "duplicate"
```

### Monitor Direwolf

```bash
# If running as service
sudo journalctl -u direwolf -f

# If running manually, output is to console
```

### Monitor MQTT traffic

```bash
# Subscribe to all topics
mosquitto_sub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t '#' -v

# Monitor system topics
mosquitto_sub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t '$SYS/#' -v
```

## Performance Testing

### Throughput test

```bash
# Send multiple messages rapidly
for i in {1..10}; do
  mosquitto_pub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
    -t msh/bridge/perf -m "Message $i"
  sleep 1
done
```

Monitor how many messages get through and check for any errors.

### Latency test

```bash
# Site A: Publish with timestamp
mosquitto_pub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/latency -m "$(date +%s.%N)"

# Site B: Subscribe and compare timestamp
mosquitto_sub -h 127.0.0.1 -u meshnerds -P TacosAreTasty69 \
  -t msh/bridge/latency -C 1
```

Calculate latency by comparing timestamps.

## Common Test Failures

### Message not received on RF

- Check Direwolf is running and connected
- Check KISS connection in bridge logs
- Verify PTT is working (LED/relay should activate)
- Check audio levels in Direwolf

### Message not received on MQTT

- Check MQTT broker is running
- Verify credentials in config.yaml
- Check bridge is subscribed to correct topic
- Enable DEBUG logging to see message flow

### Payload corruption

- Check for RF interference or weak signal
- Verify Direwolf audio levels
- Test with shorter payloads
- Check for buffer overruns in logs

### Loop prevention too aggressive

- Increase cache TTL in config.yaml
- Temporarily disable loop prevention for testing
- Check if messages are truly identical
