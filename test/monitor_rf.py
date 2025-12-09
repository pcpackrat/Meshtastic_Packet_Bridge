#!/usr/bin/env python3
"""
RF Transmission Monitor for Meshtastic Bridge
Displays real-time data being transmitted over RF via Direwolf KISS interface
"""

import socket
import sys
import time
from datetime import datetime
import struct

# KISS protocol constants
FEND = 0xC0  # Frame End
FESC = 0xDB  # Frame Escape
TFEND = 0xDC  # Transposed Frame End
TFESC = 0xDD  # Transposed Frame Escape

# KISS command codes
CMD_DATA = 0x00
CMD_TXDELAY = 0x01
CMD_P = 0x02
CMD_SLOTTIME = 0x03
CMD_TXTAIL = 0x04
CMD_FULLDUPLEX = 0x05
CMD_SETHARDWARE = 0x06
CMD_RETURN = 0xFF

class KISSMonitor:
    def __init__(self, host='127.0.0.1', port=8001):
        self.host = host
        self.port = port
        self.sock = None
        self.packet_count = 0
        self.byte_count = 0
        self.start_time = time.time()
        
    def connect(self):
        """Connect to Direwolf KISS interface"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            print(f"✓ Connected to Direwolf KISS on {self.host}:{self.port}")
            print("=" * 80)
            print("Monitoring RF transmissions... (Press Ctrl+C to stop)")
            print("=" * 80)
            return True
        except Exception as e:
            print(f"✗ Failed to connect to Direwolf: {e}")
            print(f"  Make sure Direwolf is running and listening on {self.host}:{self.port}")
            return False
    
    def decode_kiss_frame(self, data):
        """Decode a KISS frame"""
        if len(data) < 2:
            return None, None
        
        # First byte is command/port
        cmd_byte = data[0]
        port = (cmd_byte >> 4) & 0x0F
        cmd = cmd_byte & 0x0F
        
        # Rest is payload
        payload = data[1:]
        
        return cmd, payload
    
    def decode_ax25_header(self, data):
        """Decode AX.25 header to extract callsigns"""
        if len(data) < 16:
            return None, None
        
        try:
            # Destination callsign (7 bytes)
            dest = ''.join([chr(b >> 1) for b in data[0:6]]).strip()
            dest_ssid = (data[6] >> 1) & 0x0F
            if dest_ssid > 0:
                dest = f"{dest}-{dest_ssid}"
            
            # Source callsign (7 bytes)
            src = ''.join([chr(b >> 1) for b in data[7:13]]).strip()
            src_ssid = (data[13] >> 1) & 0x0F
            if src_ssid > 0:
                src = f"{src}-{src_ssid}"
            
            return src, dest
        except:
            return None, None
    
    def format_hex(self, data, max_bytes=64):
        """Format data as hex string"""
        if len(data) > max_bytes:
            hex_str = ' '.join([f'{b:02X}' for b in data[:max_bytes]])
            return f"{hex_str} ... ({len(data)} bytes total)"
        return ' '.join([f'{b:02X}' for b in data])
    
    def monitor(self):
        """Monitor KISS interface for transmitted frames"""
        buffer = bytearray()
        in_frame = False
        
        while True:
            try:
                # Read data from socket
                chunk = self.sock.recv(4096)
                if not chunk:
                    print("\n✗ Connection closed by Direwolf")
                    break
                
                buffer.extend(chunk)
                
                # Process buffer for KISS frames
                while len(buffer) > 0:
                    # Look for FEND (frame delimiter)
                    if buffer[0] == FEND:
                        if in_frame and len(buffer) > 1:
                            # End of frame found
                            frame_end = buffer.index(FEND, 1) if FEND in buffer[1:] else len(buffer)
                            frame_data = buffer[1:frame_end]
                            
                            # Process the frame
                            self.process_frame(frame_data)
                            
                            # Remove processed frame from buffer
                            buffer = buffer[frame_end:]
                            in_frame = False
                        else:
                            # Start of new frame
                            buffer.pop(0)
                            in_frame = True
                    else:
                        buffer.pop(0)
                        
            except KeyboardInterrupt:
                print("\n\n" + "=" * 80)
                self.print_statistics()
                break
            except Exception as e:
                print(f"\n✗ Error: {e}")
                break
    
    def process_frame(self, data):
        """Process a received KISS frame"""
        if len(data) == 0:
            return
        
        cmd, payload = self.decode_kiss_frame(data)
        
        # Only show data frames (transmitted packets)
        if cmd == CMD_DATA and payload:
            self.packet_count += 1
            self.byte_count += len(payload)
            
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Try to decode AX.25 header
            src, dest = self.decode_ax25_header(payload)
            
            print(f"\n[{timestamp}] Packet #{self.packet_count}")
            if src and dest:
                print(f"  From: {src} → To: {dest}")
            print(f"  Size: {len(payload)} bytes")
            print(f"  Data: {self.format_hex(payload)}")
            
            # Try to show printable ASCII if available
            printable = ''.join([chr(b) if 32 <= b < 127 else '.' for b in payload])
            if any(32 <= b < 127 for b in payload):
                print(f"  ASCII: {printable}")
    
    def print_statistics(self):
        """Print monitoring statistics"""
        elapsed = time.time() - self.start_time
        print(f"Monitoring Statistics:")
        print(f"  Duration: {elapsed:.1f} seconds")
        print(f"  Packets: {self.packet_count}")
        print(f"  Bytes: {self.byte_count}")
        if elapsed > 0:
            print(f"  Rate: {self.packet_count/elapsed:.2f} packets/sec, {self.byte_count/elapsed:.1f} bytes/sec")
        print("=" * 80)
    
    def close(self):
        """Close connection"""
        if self.sock:
            self.sock.close()

def main():
    """Main entry point"""
    print("=" * 80)
    print("Meshtastic Bridge - RF Transmission Monitor")
    print("=" * 80)
    print()
    
    # Parse command line arguments
    host = '127.0.0.1'
    port = 8001
    
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    
    monitor = KISSMonitor(host, port)
    
    if monitor.connect():
        try:
            monitor.monitor()
        finally:
            monitor.close()
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
