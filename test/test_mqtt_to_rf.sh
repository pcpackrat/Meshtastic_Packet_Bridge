#!/bin/bash
#
# Test script for Meshtastic Bridge - MQTT to RF path
#

echo "=========================================="
echo "Meshtastic Bridge - MQTT→RF Test"
echo "=========================================="
echo ""

# Configuration
MQTT_HOST="${MQTT_HOST:-127.0.0.1}"
MQTT_PORT="${MQTT_PORT:-1883}"
MQTT_USER="${MQTT_USER:-meshnerds}"
MQTT_PASS="${MQTT_PASS:-TacosAreTasty69}"
MQTT_TOPIC="${MQTT_TOPIC:-msh/bridge/test}"

echo "Configuration:"
echo "  MQTT Host: $MQTT_HOST:$MQTT_PORT"
echo "  MQTT User: $MQTT_USER"
echo "  Test Topic: $MQTT_TOPIC"
echo ""

# Check if mosquitto_pub is available
if ! command -v mosquitto_pub &> /dev/null; then
    echo "ERROR: mosquitto_pub not found. Install with: sudo apt-get install mosquitto-clients"
    exit 1
fi

# Test 1: Simple text message
echo "[Test 1] Publishing simple text message..."
mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" \
    -u "$MQTT_USER" -P "$MQTT_PASS" \
    -t "$MQTT_TOPIC" \
    -m "Test message from $(hostname) at $(date)"

if [ $? -eq 0 ]; then
    echo "✓ Message published successfully"
else
    echo "✗ Failed to publish message"
    exit 1
fi

sleep 2

# Test 2: Binary payload
echo ""
echo "[Test 2] Publishing binary payload..."
echo -n -e '\x01\x02\x03\x04\x05' | mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" \
    -u "$MQTT_USER" -P "$MQTT_PASS" \
    -t "${MQTT_TOPIC}/binary" \
    -s

if [ $? -eq 0 ]; then
    echo "✓ Binary payload published successfully"
else
    echo "✗ Failed to publish binary payload"
fi

sleep 2

# Test 3: Long topic
echo ""
echo "[Test 3] Publishing to long topic path..."
mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" \
    -u "$MQTT_USER" -P "$MQTT_PASS" \
    -t "${MQTT_TOPIC}/level1/level2/level3" \
    -m "Deep topic test"

if [ $? -eq 0 ]; then
    echo "✓ Long topic published successfully"
else
    echo "✗ Failed to publish to long topic"
fi

sleep 2

# Test 4: Large payload (but within reasonable limits)
echo ""
echo "[Test 4] Publishing larger payload..."
LARGE_MSG=$(head -c 200 /dev/urandom | base64)
mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" \
    -u "$MQTT_USER" -P "$MQTT_PASS" \
    -t "${MQTT_TOPIC}/large" \
    -m "$LARGE_MSG"

if [ $? -eq 0 ]; then
    echo "✓ Large payload published successfully"
else
    echo "✗ Failed to publish large payload"
fi

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Check bridge logs: sudo journalctl -u msh-bridge -f"
echo "2. Check Direwolf logs for transmitted frames"
echo "3. Verify remote site receives messages on MQTT"
echo ""
echo "To monitor MQTT on remote site:"
echo "  mosquitto_sub -h $MQTT_HOST -u $MQTT_USER -P $MQTT_PASS -t '$MQTT_TOPIC/#' -v"
echo ""
