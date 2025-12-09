#!/bin/bash
#
# MQTT Monitor - Quick start script for monitoring MQTT messages
#

echo "Starting MQTT Monitor..."
echo ""
echo "This will show all MQTT messages on the local broker"
echo "Press Ctrl+C to stop monitoring"
echo ""

# Check if Mosquitto is running
if ! systemctl is-active --quiet mosquitto; then
    echo "Warning: Mosquitto service is not running"
    echo "Start it with: sudo systemctl start mosquitto"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run the monitor
python3 monitor_mqtt.py
