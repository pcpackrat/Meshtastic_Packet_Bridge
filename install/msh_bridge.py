#!/usr/bin/env python3
"""
Meshtastic <-> Packet Radio Bridge
Bidirectional bridge between MQTT (Meshtastic) and AX.25 Packet Radio (Direwolf KISS)
"""

import socket
import time
import hashlib
import logging
import yaml
import threading
import queue
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
import paho.mqtt.client as mqtt


# Constants
KISS_FEND = 0xC0  # Frame End
KISS_FESC = 0xDB  # Frame Escape
KISS_TFEND = 0xDC  # Transposed Frame End
KISS_TFESC = 0xDD  # Transposed Frame Escape
KISS_CMD_DATA = 0x00  # Data frame command

AX25_UI_CONTROL = 0x03  # Unnumbered Information
AX25_PID_NO_L3 = 0xF0  # No Layer 3 protocol

RF_WRAPPER_VERSION = 0x01  # Current wrapper version


class LoopPreventionCache:
    """Cache to prevent message loops using digest-based deduplication"""
    
    def __init__(self, ttl_seconds: int = 60):
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, datetime] = {}
        self.lock = threading.Lock()
    
    def _cleanup(self):
        """Remove expired entries"""
        now = datetime.now()
        expired = [k for k, v in self.cache.items() if now - v > timedelta(seconds=self.ttl_seconds)]
        for k in expired:
            del self.cache[k]
    
    def check_and_add(self, topic: str, payload: bytes) -> bool:
        """
        Check if message is a duplicate and add to cache if not.
        Returns True if message is NEW (should be processed), False if duplicate.
        """
        # Create digest from topic + payload
        digest = hashlib.sha256(f"{topic}:".encode() + payload).hexdigest()
        
        with self.lock:
            self._cleanup()
            
            if digest in self.cache:
                logging.debug(f"Duplicate message detected: {digest[:16]}...")
                return False
            
            self.cache[digest] = datetime.now()
            return True


class AX25Frame:
    """AX.25 frame encoder/decoder"""
    
    @staticmethod
    def encode_callsign(callsign: str) -> bytes:
        """
        Encode callsign to AX.25 format (7 bytes)
        Format: 6 bytes for call (space-padded), 1 byte for SSID
        Each character is shifted left by 1 bit
        """
        # Split callsign and SSID
        if '-' in callsign:
            call, ssid = callsign.split('-', 1)
            ssid = int(ssid)
        else:
            call = callsign
            ssid = 0
        
        # Pad callsign to 6 characters
        call = call.upper().ljust(6)[:6]
        
        # Encode callsign (shift left by 1)
        encoded = bytes([ord(c) << 1 for c in call])
        
        # Add SSID byte: bits 7-5 are reserved (111), bits 4-1 are SSID, bit 0 is extension bit
        # For destination/source addresses in the middle of address field, extension bit = 0
        # For last address, extension bit = 1
        ssid_byte = 0b01100000 | ((ssid & 0x0F) << 1)
        
        return encoded + bytes([ssid_byte])
    
    @staticmethod
    def decode_callsign(data: bytes) -> Tuple[str, int]:
        """
        Decode AX.25 callsign from 7 bytes
        Returns (callsign, bytes_consumed)
        """
        if len(data) < 7:
            raise ValueError("Insufficient data for callsign")
        
        # Decode callsign (shift right by 1)
        call = ''.join([chr(b >> 1) for b in data[:6]]).strip()
        
        # Decode SSID
        ssid = (data[6] >> 1) & 0x0F
        
        if ssid > 0:
            callsign = f"{call}-{ssid}"
        else:
            callsign = call
        
        return callsign, 7
    
    @staticmethod
    def encode_ui_frame(dest: str, src: str, payload: bytes) -> bytes:
        """
        Encode AX.25 UI frame
        Format: DEST (7) + SRC (7) + CONTROL (1) + PID (1) + INFO
        """
        # Encode destination (extension bit = 0)
        dest_encoded = AX25Frame.encode_callsign(dest)
        
        # Encode source (extension bit = 1 to mark end of address field)
        src_encoded = AX25Frame.encode_callsign(src)
        src_encoded = src_encoded[:-1] + bytes([src_encoded[-1] | 0x01])  # Set extension bit
        
        # Build frame
        frame = dest_encoded + src_encoded + bytes([AX25_UI_CONTROL, AX25_PID_NO_L3]) + payload
        
        return frame
    
    @staticmethod
    def decode_ui_frame(frame: bytes) -> Optional[Tuple[str, str, bytes]]:
        """
        Decode AX.25 UI frame
        Returns (dest_callsign, src_callsign, payload) or None if invalid
        """
        if len(frame) < 16:  # Minimum: 7 (dest) + 7 (src) + 1 (ctrl) + 1 (pid)
            return None
        
        try:
            # Decode destination
            dest, offset = AX25Frame.decode_callsign(frame[0:7])
            
            # Decode source
            src, _ = AX25Frame.decode_callsign(frame[7:14])
            
            # Check control and PID
            control = frame[14]
            pid = frame[15]
            
            if control != AX25_UI_CONTROL or pid != AX25_PID_NO_L3:
                logging.debug(f"Not a UI frame: control={control:02x}, pid={pid:02x}")
                return None
            
            # Extract payload
            payload = frame[16:]
            
            return dest, src, payload
            
        except Exception as e:
            logging.error(f"Error decoding AX.25 frame: {e}")
            return None


class RFPayloadWrapper:
    """RF payload wrapper for topic + payload encapsulation"""
    
    @staticmethod
    def wrap(topic: str, payload: bytes) -> bytes:
        """
        Wrap MQTT topic and payload for RF transmission
        Format: VERSION (1) + TOPIC_LEN (1) + TOPIC (N) + PAYLOAD
        """
        topic_bytes = topic.encode('utf-8')
        topic_len = len(topic_bytes)
        
        if topic_len > 255:
            raise ValueError(f"Topic too long: {topic_len} bytes (max 255)")
        
        wrapped = bytes([RF_WRAPPER_VERSION, topic_len]) + topic_bytes + payload
        
        return wrapped
    
    @staticmethod
    def unwrap(data: bytes) -> Optional[Tuple[str, bytes]]:
        """
        Unwrap RF payload to extract topic and payload
        Returns (topic, payload) or None if invalid
        """
        if len(data) < 2:
            return None
        
        version = data[0]
        if version != RF_WRAPPER_VERSION:
            logging.warning(f"Unknown wrapper version: {version}")
            return None
        
        topic_len = data[1]
        
        if len(data) < 2 + topic_len:
            logging.error(f"Insufficient data for topic: expected {topic_len}, got {len(data) - 2}")
            return None
        
        try:
            topic = data[2:2+topic_len].decode('utf-8')
            payload = data[2+topic_len:]
            
            return topic, payload
            
        except Exception as e:
            logging.error(f"Error unwrapping payload: {e}")
            return None


class KISSClient:
    """KISS TCP client for Direwolf communication"""
    
    def __init__(self, host: str, port: int, on_frame_received):
        self.host = host
        self.port = port
        self.on_frame_received = on_frame_received
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.reconnect_delay = 1
        self.max_reconnect_delay = 60
    
    def _escape_kiss(self, data: bytes) -> bytes:
        """Escape special KISS characters"""
        result = bytearray()
        for b in data:
            if b == KISS_FEND:
                result.extend([KISS_FESC, KISS_TFEND])
            elif b == KISS_FESC:
                result.extend([KISS_FESC, KISS_TFESC])
            else:
                result.append(b)
        return bytes(result)
    
    def _unescape_kiss(self, data: bytes) -> bytes:
        """Unescape KISS characters"""
        result = bytearray()
        i = 0
        while i < len(data):
            if data[i] == KISS_FESC:
                if i + 1 < len(data):
                    if data[i + 1] == KISS_TFEND:
                        result.append(KISS_FEND)
                        i += 2
                    elif data[i + 1] == KISS_TFESC:
                        result.append(KISS_FESC)
                        i += 2
                    else:
                        i += 1
                else:
                    i += 1
            else:
                result.append(data[i])
                i += 1
        return bytes(result)
    
    def connect(self) -> bool:
        """Connect to KISS TCP server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            logging.info(f"Connected to KISS at {self.host}:{self.port}")
            self.reconnect_delay = 1
            return True
        except Exception as e:
            logging.error(f"Failed to connect to KISS: {e}")
            self.socket = None
            return False
    
    def disconnect(self):
        """Disconnect from KISS server"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def send_frame(self, frame: bytes) -> bool:
        """Send AX.25 frame via KISS"""
        if not self.socket:
            logging.warning("KISS not connected, cannot send frame")
            return False
        
        try:
            # Build KISS frame: FEND + CMD + DATA + FEND
            kiss_frame = bytes([KISS_FEND, KISS_CMD_DATA]) + self._escape_kiss(frame) + bytes([KISS_FEND])
            
            self.socket.sendall(kiss_frame)
            logging.debug(f"Sent KISS frame ({len(frame)} bytes): {frame.hex()}")
            return True
            
        except Exception as e:
            logging.error(f"Error sending KISS frame: {e}")
            self.disconnect()
            return False
    
    def _receive_loop(self):
        """Background thread to receive KISS frames"""
        buffer = bytearray()
        
        while self.running:
            if not self.socket:
                # Try to reconnect
                logging.info(f"Attempting to reconnect to KISS in {self.reconnect_delay}s...")
                time.sleep(self.reconnect_delay)
                
                if self.connect():
                    buffer.clear()
                else:
                    self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
                continue
            
            try:
                data = self.socket.recv(4096)
                if not data:
                    logging.warning("KISS connection closed")
                    self.disconnect()
                    continue
                
                buffer.extend(data)
                
                # Process complete KISS frames
                while KISS_FEND in buffer:
                    # Find frame boundaries
                    start = buffer.index(KISS_FEND)
                    
                    # Look for end of frame
                    end = buffer.find(KISS_FEND, start + 1)
                    if end == -1:
                        break  # Incomplete frame
                    
                    # Extract frame
                    kiss_frame = buffer[start+1:end]
                    buffer = buffer[end+1:]
                    
                    if len(kiss_frame) < 1:
                        continue
                    
                    # Check command byte
                    cmd = kiss_frame[0]
                    if cmd != KISS_CMD_DATA:
                        continue
                    
                    # Unescape and extract AX.25 frame
                    ax25_frame = self._unescape_kiss(kiss_frame[1:])
                    
                    if len(ax25_frame) > 0:
                        logging.debug(f"Received KISS frame ({len(ax25_frame)} bytes): {ax25_frame.hex()}")
                        self.on_frame_received(ax25_frame)
                
            except socket.timeout:
                continue
            except Exception as e:
                logging.error(f"Error in KISS receive loop: {e}")
                self.disconnect()
    
    def start(self):
        """Start KISS client"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.thread.start()
        logging.info("KISS client started")
    
    def stop(self):
        """Stop KISS client"""
        self.running = False
        self.disconnect()
        if self.thread:
            self.thread.join(timeout=5)
        logging.info("KISS client stopped")


class MeshtasticBridge:
    """Main bridge service"""
    
    def __init__(self, config_path: str = "config.yaml"):
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Setup logging
        log_level = getattr(logging, self.config.get('logging_level', 'INFO'))
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Initialize components
        self.loop_cache = None
        if self.config.get('loop_prevention', {}).get('enabled', True):
            ttl = self.config.get('loop_prevention', {}).get('cache_ttl_seconds', 60)
            self.loop_cache = LoopPreventionCache(ttl_seconds=ttl)
        
        self.kiss_client = KISSClient(
            host=self.config['ax25']['kiss_host'],
            port=self.config['ax25']['kiss_port'],
            on_frame_received=self._on_rf_received
        )
        
        self.mqtt_client = mqtt.Client()
        self.mqtt_connected = False
        
        # Setup MQTT callbacks
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        self.mqtt_client.on_message = self._on_mqtt_message
        
        # Setup MQTT authentication
        if 'username' in self.config['mqtt'] and 'password' in self.config['mqtt']:
            self.mqtt_client.username_pw_set(
                self.config['mqtt']['username'],
                self.config['mqtt']['password']
            )
        
        # Setup MQTT TLS
        if self.config['mqtt'].get('tls', False):
            self.mqtt_client.tls_set()
        
        self.running = False
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logging.info("Connected to MQTT broker")
            self.mqtt_connected = True
            
            # Subscribe to root topic
            topic = f"{self.config['mqtt']['root_topic']}/#"
            client.subscribe(topic)
            logging.info(f"Subscribed to {topic}")
        else:
            logging.error(f"MQTT connection failed with code {rc}")
            self.mqtt_connected = False
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        logging.warning(f"Disconnected from MQTT broker (rc={rc})")
        self.mqtt_connected = False
    
    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback - relay to RF"""
        try:
            topic = msg.topic
            payload = msg.payload
            
            logging.info(f"MQTTâ†’RF: {topic} ({len(payload)} bytes)")
            logging.debug(f"Payload: {payload.hex()}")
            
            # Check loop prevention
            if self.loop_cache and not self.loop_cache.check_and_add(topic, payload):
                logging.info(f"Skipping duplicate message: {topic}")
                return
            
            # Wrap topic + payload
            wrapped = RFPayloadWrapper.wrap(topic, payload)
            
            # Encode AX.25 UI frame
            ax25_frame = AX25Frame.encode_ui_frame(
                dest=self.config['ax25']['dest_callsign'],
                src=self.config['ax25']['source_callsign'],
                payload=wrapped
            )
            
            # Send via KISS
            self.kiss_client.send_frame(ax25_frame)
            
        except Exception as e:
            logging.error(f"Error processing MQTT message: {e}", exc_info=True)
    
    def _on_rf_received(self, ax25_frame: bytes):
        """RF frame received callback - relay to MQTT"""
        try:
            # Decode AX.25 frame
            result = AX25Frame.decode_ui_frame(ax25_frame)
            if not result:
                logging.debug("Ignoring non-UI frame")
                return
            
            dest, src, payload = result
            
            # Check if frame is addressed to us
            dest_call = dest.split('-')[0]
            our_dest = self.config['ax25']['dest_callsign'].split('-')[0]
            
            if dest_call != our_dest:
                logging.debug(f"Ignoring frame for {dest} (we are {our_dest})")
                return
            
            logging.info(f"RFâ†’MQTT: from {src} to {dest} ({len(payload)} bytes)")
            logging.debug(f"Payload: {payload.hex()}")
            
            # Unwrap topic + payload
            result = RFPayloadWrapper.unwrap(payload)
            if not result:
                logging.warning("Failed to unwrap RF payload")
                return
            
            topic, mqtt_payload = result
            
            # Check loop prevention
            if self.loop_cache and not self.loop_cache.check_and_add(topic, mqtt_payload):
                logging.info(f"Skipping duplicate message: {topic}")
                return
            
            # Publish to MQTT
            if self.mqtt_connected:
                self.mqtt_client.publish(topic, mqtt_payload)
                logging.info(f"Published to MQTT: {topic} ({len(mqtt_payload)} bytes)")
            else:
                logging.warning("MQTT not connected, cannot publish")
            
        except Exception as e:
            logging.error(f"Error processing RF frame: {e}", exc_info=True)
    
    def start(self):
        """Start the bridge service"""
        logging.info("Starting Meshtastic <-> Packet Radio Bridge")
        logging.info(f"MQTT: {self.config['mqtt']['host']}:{self.config['mqtt']['port']}")
        logging.info(f"KISS: {self.config['ax25']['kiss_host']}:{self.config['ax25']['kiss_port']}")
        logging.info(f"Callsigns: {self.config['ax25']['source_callsign']} -> {self.config['ax25']['dest_callsign']}")
        
        self.running = True
        
        # Start KISS client
        self.kiss_client.start()
        
        # Connect to MQTT
        self.mqtt_client.connect_async(
            self.config['mqtt']['host'],
            self.config['mqtt']['port'],
            keepalive=60
        )
        self.mqtt_client.loop_start()
        
        logging.info("Bridge started successfully")
    
    def stop(self):
        """Stop the bridge service"""
        logging.info("Stopping bridge...")
        self.running = False
        
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        
        self.kiss_client.stop()
        
        logging.info("Bridge stopped")
    
    def run(self):
        """Run the bridge (blocking)"""
        self.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Received interrupt signal")
        finally:
            self.stop()


def main():
    """Main entry point"""
    import sys
    
    config_path = "config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    bridge = MeshtasticBridge(config_path)
    bridge.run()


if __name__ == "__main__":
    main()
