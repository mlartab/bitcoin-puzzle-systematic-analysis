#!/usr/bin/env python3
"""
SHA256 Brainwallet Hunter for Bitcoin Puzzles
Tests: child = SHA256( passphrase + str(puzzle_num) )
       child = SHA256( passphrase + ":" + str(puzzle_num) )
"""

import sys, os, time, hashlib, multiprocessing

# ──────── KNOWN PRIVATE KEYS (integers) for puzzles 1‑65 ────────
KNOWN = {
    1: 1, 2: 3, 3: 7, 4: 8, 5: 21, 6: 49, 7: 76, 8: 224,
    9: 467, 10: 514, 11: 1155, 12: 2683, 13: 5216, 14: 10544,
    15: 26867, 16: 51510, 17: 95823, 18: 198669, 19: 357535,
    20: 863317, 21: 1811764, 22: 3007503, 23: 5598802, 24: 14428676,
    25: 33185509, 26: 54538862, 27: 111949941, 28: 227634408,
    29: 400708894, 30: 1033162084, 31: 2102388551, 32: 3093472814,
    33: 7137437912, 34: 14133072157, 35: 20112871792, 36: 42387769980,
    37: 100251560595, 38: 146971536592, 39: 323724968937, 40: 1003651412950,
    41: 1458252205147, 42: 2895374552463, 43: 7409811047825, 44: 15404761757071,
    45: 19996463086597, 46: 51408670348612, 47: 119666659114170, 48: 191206974700443,
    49: 409118905032525, 50: 611140496167764, 51: 2058769515153876, 52: 4216495639600700,
    53: 6763683971478124, 54: 9974455244496707, 55: 30045390491869460, 56: 44218742292676575,
    57: 138245758910846492, 58: 199976667976342049, 59: 525070384258266191, 60: 1135041350219496382,
    61: 1425787542618654982, 62: 3908372542507822062, 63: 8993229949524469768, 64: 17799667357578236628,
    65: 30568377312064202855
}
MAX_CHECK = 65

# ──────── SHA256 brainwallet functions ────────
def sha256_child(passphrase, n, separator=""):
    """child = SHA256( passphrase + separator + str(n) )"""
    data = f"{passphrase}{separator}{n}".encode('utf-8')
    return int.from_bytes(hashlib.sha256(data).digest(), 'big')

def puzzle_private_key(child_int, n):
    start = 1 << (n - 1)
    mask = start - 1
    return start | (child_int & mask)

# Separators to test
SEPARATORS = ["", ":", "/", "-", "_", " "]

# ──────── Worker ────────
def worker(seeds, result_queue):
    for phrase in seeds:
        for sep in SEPARATORS:
            ok = True
            for n in range(1, MAX_CHECK + 1):
                child = sha256_child(phrase, n, sep)
                masked = puzzle_private_key(child, n)
                if masked != KNOWN[n]:
                    ok = False
                    break
            if ok:
                result_queue.put((phrase, sep))
                return

# ──────── Main ────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help='wordlist file')
    args = parser.parse_args()

    if args.file and os.path.exists(args.file):
        with open(args.file, 'r', encoding='utf-8', errors='ignore') as f:
            seeds = [line.strip() for line in f if line.strip()]
    else:
        seeds = ["satoshi", "bitcoin", "puzzle"]

    print(f"Testing {len(seeds)} seeds × {len(SEPARATORS)} separators on {multiprocessing.cpu_count()} cores...")
    start = time.time()

    procs = multiprocessing.cpu_count()
    chunk_size = max(1, len(seeds) // procs)
    chunks = [seeds[i:i+chunk_size] for i in range(0, len(seeds), chunk_size)]
    result_queue = multiprocessing.Queue()
    processes = [multiprocessing.Process(target=worker, args=(chunk, result_queue))
                 for chunk in chunks]
    for p in processes: p.start()
    for p in processes: p.join()

    if not result_queue.empty():
        phrase, sep = result_queue.get()
        print(f"\n🎉 MATCH FOUND! Passphrase='{phrase}'  Separator='{sep}'")
        # Derive puzzle #71
        child71 = sha256_child(phrase, 71, sep)
        priv71 = puzzle_private_key(child71, 71)
        print(f"Puzzle #71 private key (hex): 0x{priv71:x}")
    else:
        elapsed = time.time() - start
        print(f"\nNo match. {len(seeds)} seeds tested in {elapsed:.2f}s")