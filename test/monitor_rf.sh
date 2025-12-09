#!/bin/bash
#
# RF Monitor - Quick start script for monitoring RF transmissions
#

echo "Starting RF Transmission Monitor..."
echo ""
echo "This will show all data being transmitted over RF via Direwolf"
echo "Press Ctrl+C to stop monitoring"
echo ""

# Check if Direwolf is running
if ! systemctl is-active --quiet direwolf; then
    echo "Warning: Direwolf service is not running"
    echo "Start it with: sudo systemctl start direwolf"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run the monitor
python3 monitor_rf.py
