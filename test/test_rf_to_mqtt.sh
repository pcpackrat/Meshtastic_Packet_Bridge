#!/bin/bash
#
# Test script for Meshtastic Bridge - RF to MQTT path
# This script subscribes to MQTT and waits for messages from RF
#

echo "=========================================="
echo "Meshtastic Bridge - RF→MQTT Test"
echo "=========================================="
echo ""

# Configuration
MQTT_HOST="${MQTT_HOST:-127.0.0.1}"
MQTT_PORT="${MQTT_PORT:-1883}"
MQTT_USER="${MQTT_USER:-meshnerds}"
MQTT_PASS="${MQTT_PASS:-TacosAreTasty69}"
MQTT_TOPIC="${MQTT_TOPIC:-msh/bridge/#}"

echo "Configuration:"
echo "  MQTT Host: $MQTT_HOST:$MQTT_PORT"
echo "  MQTT User: $MQTT_USER"
echo "  Subscribe Topic: $MQTT_TOPIC"
echo ""

# Check if mosquitto_sub is available
if ! command -v mosquitto_sub &> /dev/null; then
    echo "ERROR: mosquitto_sub not found. Install with: sudo apt-get install mosquitto-clients"
    exit 1
fi

echo "Subscribing to MQTT topics..."
echo "Waiting for messages from RF..."
echo "(Press Ctrl+C to stop)"
echo ""
echo "----------------------------------------"

# Subscribe and display messages with timestamps
mosquitto_sub -h "$MQTT_HOST" -p "$MQTT_PORT" \
    -u "$MQTT_USER" -P "$MQTT_PASS" \
    -t "$MQTT_TOPIC" \
    -v \
    -F '@Y-@m-@d @H:@M:@S | %t | %p'

echo ""
echo "Subscription ended."
