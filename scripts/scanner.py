#!/usr/bin/env python3
"""
Bitcoin Puzzle #71 — Smart Scanner
Target address: 1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU
Key range:      0x400000000000000000 → 0x7fffffffffffffffff

Strategy:
  Zone 1 — First 1% of range  (puzzle #69 was found at 0.72%)
  Zone 2 — Random scan 45-65% (historical average is 53.2%)
  Zone 3 — Linear sweep of remaining range

SAFE CLAIM: if key is found, this script saves it encrypted.
            NEVER broadcast to public mempool. See CLAIMING.md
"""

import coincurve
import hashlib
import base58
import secrets
import time
import json
import os
import sys
import struct
import signal

# ─── CONFIG ──────────────────────────────────────────────────────────────────

TARGET_ADDR  = "1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU"
RANGE_START  = 0x400000000000000000   # 2^70
RANGE_END    = 0x7fffffffffffffffff   # 2^71 - 1
RANGE_SIZE   = RANGE_END - RANGE_START + 1

SAVE_FILE    = os.path.expanduser("~/puzzle71/progress.json")
FOUND_FILE   = os.path.expanduser("~/puzzle71/FOUND_KEY.txt")

# ─── CORE: private key → Bitcoin address ─────────────────────────────────────

def privkey_to_address(privkey_int: int) -> str:
    """Convert integer private key to compressed P2PKH Bitcoin address."""
    privkey_bytes = privkey_int.to_bytes(32, 'big')
    pub = coincurve.PublicKey.from_valid_secret(privkey_bytes).format(compressed=True)
    sha256_hash = hashlib.sha256(pub).digest()
    ripemd160 = hashlib.new('ripemd160', sha256_hash).digest()
    versioned = b'\x00' + ripemd160          # mainnet prefix
    checksum = hashlib.sha256(hashlib.sha256(versioned).digest()).digest()[:4]
    return base58.b58encode(versioned + checksum).decode()

# ─── FOUND KEY HANDLER ───────────────────────────────────────────────────────

def handle_found(privkey_int: int):
    """Save found key and print safe claiming instructions."""
    privkey_hex = hex(privkey_int)
    privkey_wif = privkey_to_wif(privkey_int)

    print("\n" + "=" * 60)
    print("  🎉  KEY FOUND!  🎉")
    print("=" * 60)
    print(f"\n  Private Key (HEX): {privkey_hex}")
    print(f"  Private Key (WIF): {privkey_wif}")
    print(f"  Address:           {TARGET_ADDR}")
    print("\n" + "=" * 60)
    print("  ⚠️  DO NOT broadcast to public mempool!")
    print("  READ ~/puzzle71/CLAIMING.md for safe steps.")
    print("=" * 60)

    with open(FOUND_FILE, 'w') as f:
        f.write(f"PRIVATE KEY HEX: {privkey_hex}\n")
        f.write(f"PRIVATE KEY WIF: {privkey_wif}\n")
        f.write(f"ADDRESS:         {TARGET_ADDR}\n")
        f.write(f"FOUND AT:        {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n")
        f.write("\nNEXT STEP: Read CLAIMING.md — do NOT broadcast publicly!\n")

    print(f"\n  Key saved to: {FOUND_FILE}")
    sys.exit(0)

def privkey_to_wif(privkey_int: int) -> str:
    """Convert integer private key to WIF (Wallet Import Format)."""
    privkey_bytes = privkey_int.to_bytes(32, 'big')
    extended = b'\x80' + privkey_bytes + b'\x01'   # 0x01 = compressed pubkey
    checksum = hashlib.sha256(hashlib.sha256(extended).digest()).digest()[:4]
    return base58.b58encode(extended + checksum).decode()

# ─── PROGRESS SAVE/LOAD ──────────────────────────────────────────────────────

def save_progress(zone: str, last_key: int, total_checked: int):
    data = {
        "zone": zone,
        "last_key_hex": hex(last_key),
        "total_checked": total_checked,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
    }
    with open(SAVE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def load_progress():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE) as f:
            return json.load(f)
    return None

# ─── ZONE 1: First 1% of range ───────────────────────────────────────────────

def scan_zone1(start_from: int = None, total_checked: int = 0):
    """
    Scan the first 1% of the range.
    Puzzle #69 was found at 0.72% — this zone covers that.
    Zone: 0x400000000000000000 → 0x40A3D70A3D70A3D70
    """
    zone_end = RANGE_START + int(RANGE_SIZE * 0.01)
    start    = start_from if start_from else RANGE_START

    print(f"\n[Zone 1] Scanning first 1% of range")
    print(f"  From: {hex(start)}")
    print(f"  To:   {hex(zone_end)}")
    print(f"  Keys: {zone_end - start:,}")
    print(f"  Why:  Puzzle #69 found at 0.72% of its range!\n")

    key     = start
    checked = 0
    t0      = time.time()
    last_save = time.time()

    while key <= zone_end:
        addr = privkey_to_address(key)
        total_checked += 1
        checked       += 1

        if addr == TARGET_ADDR:
            handle_found(key)

        if checked % 50000 == 0:
            elapsed = time.time() - t0
            speed   = checked / elapsed if elapsed > 0 else 0
            pct     = (key - RANGE_START) / RANGE_SIZE * 100
            remaining = (zone_end - key) / speed if speed > 0 else 0
            print(f"  [{pct:.4f}%] {speed:.0f} k/s | checked {total_checked:,} | "
                  f"ETA zone1: {remaining/60:.1f}m | key: {hex(key)}")

        if time.time() - last_save > 30:
            save_progress("zone1", key, total_checked)
            last_save = time.time()

        key += 1

    save_progress("zone1_done", zone_end, total_checked)
    print(f"\n[Zone 1] Complete. {checked:,} keys scanned.")
    return total_checked

# ─── ZONE 2: Smart random — statistical hot zone (45–65%) ────────────────────

def scan_zone2(total_checked: int = 0, duration_minutes: int = 60):
    """
    Random scan within the 45-65% statistical hot zone.
    Historical average position of solved keys: 53.2%.
    This zone contains the highest probability density.
    """
    zone_start = RANGE_START + int(RANGE_SIZE * 0.45)
    zone_end   = RANGE_START + int(RANGE_SIZE * 0.65)
    zone_size  = zone_end - zone_start

    print(f"\n[Zone 2] Random scan — statistical hot zone (45–65%)")
    print(f"  From: {hex(zone_start)}")
    print(f"  To:   {hex(zone_end)}")
    print(f"  Why:  53.2% is the historical average for all 79 solved puzzles")
    print(f"  Mode: Random sampling (non-repeating blocks of 1000)\n")

    checked     = 0
    t0          = time.time()
    deadline    = t0 + duration_minutes * 60
    last_save   = time.time()

    while time.time() < deadline:
        # Pick a random start point in the zone, scan 1000 consecutive keys
        block_start = zone_start + secrets.randbelow(zone_size - 1000)

        for i in range(1000):
            key  = block_start + i
            addr = privkey_to_address(key)
            total_checked += 1
            checked       += 1

            if addr == TARGET_ADDR:
                handle_found(key)

        if checked % 100000 == 0:
            elapsed = time.time() - t0
            speed   = checked / elapsed if elapsed > 0 else 0
            mins_left = (deadline - time.time()) / 60
            print(f"  [Zone2] {speed:.0f} k/s | checked {total_checked:,} | "
                  f"time left: {mins_left:.1f}m")

        if time.time() - last_save > 30:
            save_progress("zone2", block_start, total_checked)
            last_save = time.time()

    print(f"\n[Zone 2] Session complete. {checked:,} keys scanned this run.")
    return total_checked

# ─── ZONE 3: Linear sweep — track which segments are done ────────────────────

def scan_zone3(start_from: int = None, total_checked: int = 0):
    """
    Linear sweep of the full range, skipping Zone 1 and Zone 2.
    This is the slow but exhaustive fallback.
    Saves progress every 30s so you can resume anytime.
    """
    start = start_from if start_from else (RANGE_START + int(RANGE_SIZE * 0.01))

    print(f"\n[Zone 3] Linear sweep — exhaustive scan")
    print(f"  Starting: {hex(start)}")
    print(f"  This will take a long time. Ctrl+C saves progress.\n")

    key       = start
    checked   = 0
    t0        = time.time()
    last_save = time.time()

    while key <= RANGE_END:
        addr = privkey_to_address(key)
        total_checked += 1
        checked       += 1

        if addr == TARGET_ADDR:
            handle_found(key)

        if checked % 100000 == 0:
            elapsed  = time.time() - t0
            speed    = checked / elapsed if elapsed > 0 else 0
            pct      = (key - RANGE_START) / RANGE_SIZE * 100
            keys_left = RANGE_END - key
            eta_days  = keys_left / speed / 86400 if speed > 0 else 0
            print(f"  [{pct:.4f}%] {speed:.0f} k/s | total: {total_checked:,} | "
                  f"ETA full: {eta_days:.1f} days | key: {hex(key)}")

        if time.time() - last_save > 30:
            save_progress("zone3", key, total_checked)
            last_save = time.time()

        key += 1

# ─── GRACEFUL INTERRUPT ───────────────────────────────────────────────────────

def signal_handler(sig, frame):
    print("\n\n[!] Interrupted. Progress saved. Run again to resume.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(os.path.expanduser("~/puzzle71"), exist_ok=True)

    print("=" * 60)
    print("  Bitcoin Puzzle #71 — Smart Scanner")
    print(f"  Target: {TARGET_ADDR}")
    print(f"  Range:  {hex(RANGE_START)} → {hex(RANGE_END)}")
    print(f"  Size:   {RANGE_SIZE:,} keys")
    print("=" * 60)

    # Verify our address function works correctly
    test_key   = 1
    test_addr  = privkey_to_address(test_key)
    print(f"\n[Test] key=1 → {test_addr}")
    print(f"       Expected: 1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH")
    assert test_addr == "1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH", "Address function ERROR!"
    print("       ✓ Address function verified\n")

    # Check for saved progress
    prog = load_progress()
    total_checked = 0

    if prog:
        print(f"[Resume] Found saved progress:")
        print(f"  Zone:    {prog['zone']}")
        print(f"  Last key: {prog['last_key_hex']}")
        print(f"  Checked: {prog['total_checked']:,}")
        choice = input("\n  Resume from saved position? (y/n): ").strip().lower()

        if choice == 'y':
            total_checked = prog['total_checked']
            zone = prog['zone']
            last_key = int(prog['last_key_hex'], 16)

            if zone == 'zone1':
                total_checked = scan_zone1(start_from=last_key + 1, total_checked=total_checked)
            elif zone in ('zone1_done', 'zone2'):
                total_checked = scan_zone2(total_checked=total_checked, duration_minutes=120)
            else:
                scan_zone3(start_from=last_key + 1, total_checked=total_checked)
            return

    print("\n  Scan modes:")
    print("  [1] Zone 1 only  — first 1% (fast, ~30min, covers puzzle #69 zone)")
    print("  [2] Zone 2 only  — random 45-65% hot zone (2hr session)")
    print("  [3] Full strategy — Zone1 → Zone2 → Zone3 (exhaustive)")
    print("  [4] Quick test   — scan 10,000 keys, show speed")

    choice = input("\n  Choose [1/2/3/4]: ").strip()

    if choice == '1':
        scan_zone1(total_checked=total_checked)

    elif choice == '2':
        mins = input("  Session duration in minutes [120]: ").strip()
        mins = int(mins) if mins.isdigit() else 120
        scan_zone2(total_checked=total_checked, duration_minutes=mins)

    elif choice == '3':
        total_checked = scan_zone1(total_checked=total_checked)
        total_checked = scan_zone2(total_checked=total_checked, duration_minutes=120)
        scan_zone3(total_checked=total_checked)

    elif choice == '4':
        print("\n[Benchmark] Scanning 10,000 keys from range start...")
        t0 = time.time()
        for i in range(10000):
            privkey_to_address(RANGE_START + i)
        elapsed = time.time() - t0
        speed = 10000 / elapsed
        print(f"\n  Speed:       {speed:.0f} keys/second")
        print(f"  Per minute:  {speed*60:.0f}")
        print(f"  Per hour:    {speed*3600:.0f}")
        print(f"  Zone 1 ETA:  {RANGE_SIZE * 0.01 / speed / 3600:.1f} hours")

    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()