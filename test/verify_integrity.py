#!/usr/bin/env python3
"""
Payload integrity verification tool
Compares payloads sent vs received to verify byte-for-byte integrity
"""

import sys
import hashlib
import argparse


def compute_hash(data: bytes) -> str:
    """Compute SHA-256 hash of data"""
    return hashlib.sha256(data).hexdigest()


def verify_files(file1: str, file2: str) -> bool:
    """Verify two files are identical"""
    try:
        with open(file1, 'rb') as f1:
            data1 = f1.read()
        
        with open(file2, 'rb') as f2:
            data2 = f2.read()
        
        hash1 = compute_hash(data1)
        hash2 = compute_hash(data2)
        
        print(f"File 1: {file1}")
        print(f"  Size: {len(data1)} bytes")
        print(f"  SHA-256: {hash1}")
        print()
        print(f"File 2: {file2}")
        print(f"  Size: {len(data2)} bytes")
        print(f"  SHA-256: {hash2}")
        print()
        
        if hash1 == hash2:
            print("✓ FILES ARE IDENTICAL - Payload integrity verified!")
            return True
        else:
            print("✗ FILES DIFFER - Payload integrity check FAILED!")
            print()
            print("Differences:")
            print(f"  Size difference: {len(data2) - len(data1)} bytes")
            
            # Find first difference
            min_len = min(len(data1), len(data2))
            for i in range(min_len):
                if data1[i] != data2[i]:
                    print(f"  First difference at byte {i}:")
                    print(f"    File 1: 0x{data1[i]:02x}")
                    print(f"    File 2: 0x{data2[i]:02x}")
                    break
            
            return False
    
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def verify_string(data: str) -> None:
    """Compute hash of string data"""
    data_bytes = data.encode('utf-8')
    hash_val = compute_hash(data_bytes)
    
    print(f"Data: {data}")
    print(f"Size: {len(data_bytes)} bytes")
    print(f"SHA-256: {hash_val}")


def main():
    parser = argparse.ArgumentParser(
        description='Verify payload integrity for Meshtastic Bridge'
    )
    
    parser.add_argument(
        'files',
        nargs='*',
        help='Files to compare (provide 2 files) or compute hash (1 file)'
    )
    
    parser.add_argument(
        '-s', '--string',
        help='Compute hash of string data'
    )
    
    args = parser.parse_args()
    
    if args.string:
        verify_string(args.string)
        return
    
    if len(args.files) == 2:
        success = verify_files(args.files[0], args.files[1])
        sys.exit(0 if success else 1)
    elif len(args.files) == 1:
        # Single file - just compute hash
        try:
            with open(args.files[0], 'rb') as f:
                data = f.read()
            hash_val = compute_hash(data)
            print(f"File: {args.files[0]}")
            print(f"Size: {len(data)} bytes")
            print(f"SHA-256: {hash_val}")
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
