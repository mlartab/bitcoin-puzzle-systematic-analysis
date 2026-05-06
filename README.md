# Bitcoin Puzzle Systematic Analysis

**A complete, automated analysis of the Bitcoin Puzzle challenge series, designed to methodically test every plausible deterministic wallet generation scheme.**

## Overview
The Bitcoin Puzzle contains 160 addresses with increasing prize amounts. Puzzles #1‑#70 have been solved, leaving #71 (7.1 BTC) and higher. The puzzle creator stated the keys are “consecutive keys from a deterministic wallet, masked with leading 000...0001”.

This repository provides a set of open‑source tools that systematically test every **weak PRNG** and **brainwallet derivation** that a 2015 developer might have used. The approach does **not** rely on brute‑forcing the 2^70 keyspace, but rather on recovering the original seed by checking all 69 known private keys simultaneously.

## What’s Tested
- **BIP32 brainwallets** (passphrase → master seed → hardened derivation `m/{n}'`, `m/0'/{n}'`, `m/0'/0'/{n}'`, BIP44)
- **SHA256(passphrase + index)** with multiple separators
- **Python `random.getrandbits(256)`** with a 32‑bit seed – complete 2^32 seed scan (C++)
- **C `rand()`** (glibc) with 32‑bit seed – complete scan (C++)
- **Java `java.util.Random`** – LCG state recovery from two consecutive known outputs (C++)
- **Mersenne Twister state recovery** – attempted via SAT solver (Z3) and via observed partial outputs (untwister)
- **Custom passphrase lists** generated from the puzzle creator’s public posts

## Key Results
- All 2^32 seeds for Python’s MT19937 and glibc `rand()` were exhausted. **No seed reproduces the known puzzles.**
- The LCG state recovery for Java’s Random also failed, indicating the puzzle does not use Java’s `Random`.
- The creator likely used a cryptographically secure PRNG (e.g., `/dev/urandom`) or a personal passphrase that is not in any public wordlist.

## Why This Matters
This project demonstrates a rigorous approach to **cryptographic reverse engineering**:
- Low‑level elliptic curve and PRNG implementation in C++
- Symbolic SAT solving with Z3
- BIP32 derivation and brainwallet analysis
- Efficient multicore search using custom bloom filters and early‑exit constraints

It is an educational tool for anyone studying deterministic wallets, PRNG weaknesses, and the limits of brute‑force attacks.

## Usage
See the `scripts/` and `cpp/` directories. Each tool is self‑contained and can be run with `python3` or compiled with `g++`.

## Disclaimer
This code is for educational and research purposes only. The puzzle addresses belong to their unknown creator. No keys were recovered; the repository only demonstrates the methodology.
