#!/usr/bin/env python3
"""
MQTT Monitor for Meshtastic Bridge
Displays real-time MQTT messages on localhost
"""

import paho.mqtt.client as mqtt
import sys
import yaml
from datetime import datetime
import json

class MQTTMonitor:
    def __init__(self, config_file='/opt/msh-bridge/config.yaml'):
        self.config = self.load_config(config_file)
        self.message_count = 0
        self.client = None
        
    def load_config(self, config_file):
        """Load configuration from YAML file"""
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Config file not found: {config_file}")
            print("Using default settings...")
            return {
                'mqtt': {
                    'host': '127.0.0.1',
                    'port': 1883,
                    'username': 'meshnerds',
                    'password': 'TacosAreTasty69',
                    'root_topic': 'msh/bridge'
                }
            }
    
    def on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            print(f"✓ Connected to MQTT broker at {self.config['mqtt']['host']}:{self.config['mqtt']['port']}")
            
            # Subscribe to all topics under root_topic
            topic = f"{self.config['mqtt']['root_topic']}/#"
            client.subscribe(topic)
            print(f"✓ Subscribed to: {topic}")
            print("=" * 80)
            print("Monitoring MQTT messages... (Press Ctrl+C to stop)")
            print("=" * 80)
        else:
            print(f"✗ Connection failed with code {rc}")
            error_messages = {
                1: "Incorrect protocol version",
                2: "Invalid client identifier",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized"
            }
            print(f"  {error_messages.get(rc, 'Unknown error')}")
    
    def on_message(self, client, userdata, msg):
        """Callback when message is received"""
        self.message_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        print(f"\n[{timestamp}] Message #{self.message_count}")
        print(f"  Topic: {msg.topic}")
        print(f"  QoS: {msg.qos}")
        print(f"  Retain: {msg.retain}")
        print(f"  Size: {len(msg.payload)} bytes")
        
        # Try to decode payload
        try:
            # Try JSON first
            payload_str = msg.payload.decode('utf-8')
            try:
                payload_json = json.loads(payload_str)
                print(f"  Payload (JSON):")
                print(f"    {json.dumps(payload_json, indent=4)}")
            except json.JSONDecodeError:
                # Not JSON, show as string
                print(f"  Payload (Text): {payload_str}")
        except UnicodeDecodeError:
            # Binary data
            hex_str = msg.payload.hex()
            if len(hex_str) > 128:
                hex_str = hex_str[:128] + f"... ({len(msg.payload)} bytes total)"
            print(f"  Payload (Hex): {hex_str}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from broker"""
        if rc != 0:
            print(f"\n✗ Unexpected disconnection (code {rc})")
    
    def monitor(self):
        """Start monitoring MQTT"""
        mqtt_config = self.config['mqtt']
        
        self.client = mqtt.Client()
        
        # Set callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # Set credentials if provided
        if mqtt_config.get('username') and mqtt_config.get('password'):
            self.client.username_pw_set(
                mqtt_config['username'],
                mqtt_config['password']
            )
        
        try:
            # Connect to broker
            self.client.connect(
                mqtt_config['host'],
                mqtt_config['port'],
                60  # keepalive
            )
            
            # Start loop
            self.client.loop_forever()
            
        except KeyboardInterrupt:
            print("\n\n" + "=" * 80)
            print(f"Monitoring Statistics:")
            print(f"  Total Messages: {self.message_count}")
            print("=" * 80)
        except Exception as e:
            print(f"\n✗ Error: {e}")
        finally:
            if self.client:
                self.client.disconnect()

def main():
    """Main entry point"""
    print("=" * 80)
    print("Meshtastic Bridge - MQTT Monitor")
    print("=" * 80)
    print()
    
    # Parse command line arguments
    config_file = '/opt/msh-bridge/config.yaml'
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    
    monitor = MQTTMonitor(config_file)
    monitor.monitor()

if __name__ == '__main__':
    main()
