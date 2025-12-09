#!/bin/bash
#
# Meshtastic Packet Radio Bridge - Installation Script
# For Raspberry Pi OS 13 Minimal
#

set -e  # Exit on error

echo "=========================================="
echo "Meshtastic Bridge Installation"
echo "=========================================="
echo ""

# Check if running with sudo (not as root directly)
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script requires root privileges."
    echo "Please run with sudo: sudo ./install.sh"
    exit 1
fi

# Prevent running as root user directly
if [ -z "$SUDO_USER" ] || [ "$SUDO_USER" = "root" ]; then
    echo "ERROR: Do not run this script as root user directly!"
    echo ""
    echo "This script must be run using 'sudo' from a regular user account."
    echo ""

    # Check if any non-root users exist
    REGULAR_USERS=$(awk -F: '$3 >= 1000 && $3 < 65534 {print $1}' /etc/passwd)

    if [ -z "$REGULAR_USERS" ]; then
        echo "No regular user accounts found on this system."
        echo ""
        echo "Please create a regular user first:"
        echo "  1. adduser <username>"
        echo "  2. usermod -aG sudo <username>"
        echo "  3. Log in as that user"
        echo "  4. Run: sudo ./install.sh"
    else
        echo "Available regular users on this system:"
        echo "$REGULAR_USERS"
        echo ""
        echo "Please log in as one of these users and run:"
        echo "  sudo ./install.sh"
    fi
    echo ""
    exit 1
fi

# Get the actual user who invoked sudo
INSTALL_USER="$SUDO_USER"
echo "Installing for user: $INSTALL_USER"
echo ""

# Update system
echo "[1/8] Updating system packages..."
apt-get update
apt-get upgrade -y

# Install dependencies
echo "[2/8] Installing dependencies..."
apt-get install -y \
    direwolf \
    mosquitto \
    mosquitto-clients \
    python3 \
    python3-pip \
    python3-venv \
    git \
    alsa-utils

# Create installation directory
echo "[3/8] Creating installation directory..."
mkdir -p /opt/msh-bridge
mkdir -p /var/log/direwolf

# Create Python virtual environment
echo "[4/8] Setting up Python virtual environment..."
python3 -m venv /opt/msh-bridge/venv

# Install Python packages
echo "[5/8] Installing Python packages..."
/opt/msh-bridge/venv/bin/pip install --upgrade pip
/opt/msh-bridge/venv/bin/pip install paho-mqtt pyyaml

# Copy files
echo "[6/8] Copying service files..."

# Determine source directory (where this script is located)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cp "$SCRIPT_DIR/msh_bridge.py" /opt/msh-bridge/
cp "$SCRIPT_DIR/config.yaml" /opt/msh-bridge/
cp "$SCRIPT_DIR/direwolf.conf" /opt/msh-bridge/

# Make Python script executable
chmod +x /opt/msh-bridge/msh_bridge.py

# Extract callsign from config.yaml and update direwolf.conf
echo "  Configuring Direwolf callsign from config.yaml..."
AX25_CALLSIGN=$(grep "source_callsign:" /opt/msh-bridge/config.yaml | awk '{print $2}' | tr -d '\r\n' | xargs)
if [ -n "$AX25_CALLSIGN" ]; then
    sed -i "s/^MYCALL .*/MYCALL $AX25_CALLSIGN/" /opt/msh-bridge/direwolf.conf
    echo "  Set MYCALL to: $AX25_CALLSIGN"
else
    echo "  WARNING: Could not extract callsign from config.yaml"
fi

# Set ownership to the user who invoked sudo
chown -R "$INSTALL_USER":"$INSTALL_USER" /opt/msh-bridge
chown -R "$INSTALL_USER":"$INSTALL_USER" /var/log/direwolf

# Configure Mosquitto MQTT broker
echo "[7/9] Configuring Mosquitto MQTT broker..."

# Backup existing mosquitto.conf if it exists
if [ -f /etc/mosquitto/mosquitto.conf ]; then
    cp /etc/mosquitto/mosquitto.conf /etc/mosquitto/mosquitto.conf.backup
    echo "  Backed up existing mosquitto.conf"
fi

# Copy our mosquitto configuration
cp "$SCRIPT_DIR/mosquitto.conf" /etc/mosquitto/mosquitto.conf

# Extract MQTT credentials from the installed config.yaml (respects user modifications)
# Strip carriage returns and whitespace to avoid control character errors
MQTT_USER=$(grep "username:" /opt/msh-bridge/config.yaml | awk '{print $2}' | tr -d '\r\n' | xargs)
MQTT_PASS=$(grep "password:" /opt/msh-bridge/config.yaml | awk '{print $2}' | tr -d '\r\n' | xargs)

# Create password file
echo "  Creating password file for user: $MQTT_USER"
mosquitto_passwd -c -b /etc/mosquitto/pwfile "$MQTT_USER" "$MQTT_PASS"

# Set proper permissions
chmod 600 /etc/mosquitto/pwfile
chown mosquitto:mosquitto /etc/mosquitto/pwfile
chown mosquitto:mosquitto /etc/mosquitto/mosquitto.conf

# Restart mosquitto to apply changes
systemctl restart mosquitto
systemctl enable mosquitto
echo "  Mosquitto configured and restarted"

# Install systemd service
echo "[8/9] Installing systemd services..."
cp "$SCRIPT_DIR/msh-bridge.service" /etc/systemd/system/
cp "$SCRIPT_DIR/direwolf.service" /etc/systemd/system/

# Update service files to use the actual user instead of hardcoded 'pi'
echo "  Updating service files to run as user: $INSTALL_USER"
sed -i "s/^User=pi$/User=$INSTALL_USER/" /etc/systemd/system/msh-bridge.service
sed -i "s/^Group=pi$/Group=$INSTALL_USER/" /etc/systemd/system/msh-bridge.service
sed -i "s/^User=pi$/User=$INSTALL_USER/" /etc/systemd/system/direwolf.service
sed -i "s/^Group=pi$/Group=$INSTALL_USER/" /etc/systemd/system/direwolf.service

systemctl daemon-reload

# Enable services
echo "[9/9] Enabling services..."
systemctl enable direwolf.service
systemctl enable msh-bridge.service

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit configuration:"
echo "   sudo nano /opt/msh-bridge/config.yaml"
echo ""
echo "   IMPORTANT: Set your amateur radio callsign!"
echo "   Change 'source_callsign' from N0CALL-1 to YOUR-SSID"
echo ""
echo "2. Configure Direwolf audio device:"
echo "   - Run 'aplay -l' and 'arecord -l' to find your sound card"
echo "   - Edit /opt/msh-bridge/direwolf.conf"
echo "   - Update ADEVICE line with your device (default: plughw:0,0)"
echo "   - Adjust PTT device if needed (default: /dev/hidraw0)"
echo "   [OK] MYCALL automatically set from config.yaml"
echo ""
echo "3. Mosquitto MQTT Broker:"
echo "   [OK] Already configured with authentication"
echo "   [OK] Username: meshnerds (from config.yaml)"
echo "   [OK] Listening on port 1883 (TCP) and 9001 (WebSocket)"
echo "   [OK] Password file: /etc/mosquitto/pwfile"
echo ""
echo "4. Start the services:"
echo "   sudo systemctl start direwolf"
echo "   sudo systemctl start msh-bridge"
echo ""
echo "5. Monitor logs:"
echo "   sudo journalctl -u direwolf -f"
echo "   sudo journalctl -u msh-bridge -f"
echo ""
echo "6. Check status:"
echo "   sudo systemctl status direwolf"
echo "   sudo systemctl status msh-bridge"
echo ""
echo "For testing and troubleshooting, see README.md"
echo ""
