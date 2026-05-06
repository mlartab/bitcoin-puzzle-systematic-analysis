# Bitcoin Puzzle — My Personal Hunt for the Key

**A real story of one laptop, some curiosity, and a deep dive into how Bitcoin private keys are born.**

---

## What Is This?

In 2015, someone created the "Bitcoin Puzzle" — 160 Bitcoin addresses, each holding a little more BTC than the last. The first ones got cracked quickly. Then more. Today, 69 puzzles have been solved, and **Puzzle #71 still holds 7.1 BTC (over $580,000).**

This repository is my attempt to find the key. I didn't succeed — but I learned things most people never discover about how wallets work under the hood.

**Everything here runs on a standard laptop. No GPU farms. No rented cloud servers. Just an i5 with 8 GB of RAM and a lot of patience.**

---

## The Puzzle, Explained Simply

The creator left one big clue:

> *"It is just consecutive keys from a deterministic wallet (masked with leading 000...0001 to set difficulty)."*

What does that mean?

Imagine you have a wallet that spits out private keys one after another — like a really fancy random number generator that always gives the same sequence if you start it with the same seed.

For each puzzle number **n**, the creator took the n-th key from that wallet, then applied a simple mask: set the first (n‑1) bits to `000...0001`, and keep the lower bits from the wallet key. This made early puzzles easy (few bits to guess) and later puzzles hard (many bits).

The formula is:
Private Key = 2^(n-1) + (wallet_key_n & (2^(n-1) - 1)) 

| Puzzle | Range Start | Private Key (example) |
|--------|-------------|----------------------|
| #1     | `1` (1 bit)              | `1`                           |
| #5     | `16` (5 bits)         | `21`                         |
| #33    | `2^32` (33 bits) | `7137437912`         |
| #71    | `2^70` (71 bits)    | ???                         |

The wallet key is the same for all puzzles — only the mask changes. So if I could find the **master seed** that generates the wallet, I would get every remaining key at once.

---

## How I Tried to Find the Seed

I took the **69 already-solved puzzles** and used them as a "truth test." If I guessed a seed (or passphrase, or random generator setting), I could generate all 69 keys and check: do they match the known ones? If yes, I found the seed.

This turns an impossible search (2^70 possible keys for puzzle #71) into "just" finding the seed.

### The Tools I Built

Here is every tool in this repo, and what it does.

| Tool | Language | What It Does |
|------|----------|--------------|
| `seed_hunt_all.py` | Python | Tests passphrases against BIP32 wallets (4 different derivation paths) |
| `seed_hunt_sha256.py` | Python | Tests passphrases against old-school SHA256 brainwallets |
| `z3_crack.py` | Python | Uses Z3 SAT solver to try to reverse-engineer the Mersenne Twister state |
| `gen_observed.py` | Python | Generates partial output lists for the untwister state-recovery tool |
| `mt_brute.cpp` | C++ | Scans ALL 4 billion possible 32-bit seeds for Python's `random` module |
| `rand_brute.cpp` | C++ | Scans ALL 4 billion possible seeds for C's `rand()` |
| `java_crack.cpp` | C++ | Tries to recover Java's Random seed using modular arithmetic (no brute force!) |
| `scanner.py` | Python | A custom range scanner I built to sweep through key ranges |

### The External Tool: Keyhunt

[Keyhunt](https://github.com/albertobsd/keyhunt) is an open-source tool by AlbertoBSD, built specifically for the Bitcoin Puzzle. It's the CPU-based engine that the community uses for hash-based searching.

**How I used it:**

Keyhunt has several modes. The most important one for my hunt was **rmd160 mode**:

//bash --

./keyhunt -m rmd160 -f target71_rmd.txt -b 71 -l compress -R -t 8 -e

Here's what each flag means:

Flag	What It Does
-m rmd160	Search by matching RIPEMD-160 hashes (the address hash)
-f target71_rmd.txt	The target hash file for puzzle #71
-b 71	Tell keyhunt this is a 71-bit puzzle
-l compress	Look for compressed public keys only
-R	Random mode — hop randomly through the range
-t 8	Use 8 CPU threads (all my i5 cores)
-e	Enable endomorphism — a mathematical shortcut that doubles speed
The -e flag is special. It uses the GLV endomorphism — a property of the secp256k1 curve where multiplying a point's x-coordinate by a special constant β (beta) gives you a related point. This effectively cuts the search space in half. On my i5, this pushed me from ~6 Mkeys/s to ~12 Mkeys/s.

Keyhunt also supports BSGS mode (Baby-Step Giant-Step) which uses more RAM but can search faster for smaller bit ranges, and address mode which can verify private keys against known addresses.

⚠️ Keyhunt is included in this repo as source code only (in tools/keyhunt/). The original is by @albertobsd. All credit goes to them. 

The Chain Code: Why This Puzzle Is So Hard
You might wonder: "If I know 69 private keys from the same wallet, why can't I calculate the rest?"

This is where the chain code comes in.

What Is a Chain Code?
When a BIP32 wallet (the standard for HD wallets) is created from a seed phrase, it generates two things:

A master private key — a 256-bit number

A master chain code — another 256-bit number

The chain code is like a "secret ingredient" mixed into the recipe every time a new child key is cooked up. Without it, you can't derive any children — even if you have the master private key.

The chain code is created by running HMAC-SHA512 over the seed:

text
HMAC-SHA512(key="Bitcoin seed", data=your_seed_phrase)
The output is 64 bytes. The left half becomes your master private key. The right half becomes your chain code.

Why You Can't Find It From Public Keys
For non-hardened child keys, the derivation formula is:

text
child_public_key = parent_public_key + HMAC-SHA512(chain_code, parent_public_key || index) × G
Because SHA-512 is a one-way function, you cannot:

Reverse a child public key to find the chain code

Derive the parent private key from a child public key

Compute child keys without the chain code

Even if you have every child public key, without the chain code you're stuck. It's like having a locked box and knowing the shape of every key that fits inside — but not the key that opens the box.

The chain code is 256 random bits. Brute-forcing it would take longer than the age of the universe.

What This Means for the Puzzle
The puzzle creator has the seed phrase. From that seed, they derived the master private key AND the chain code. They used both to generate all 160 puzzle keys.

The six known public keys (from puzzles #135, #140, #145, #150, #155, #160 — revealed by test transactions) are tantalizing clues, but without the chain code they're like a safe with the combination written in invisible ink.

What I Tested (and What Failed)
1. Brainwallets — BIP32 Passphrase Guessing
I tested millions of passphrases — from rockyou.txt, from the creator's own words, from Bitcoin vocabulary, from common patterns. Each passphrase was turned into a BIP32 master seed and tested against all 69 known keys.

Result: Nothing matched. The passphrase is not in any public wordlist.

2. SHA256 Brainwallets (Old-School)
Before BIP32, people used: private_key = SHA256("password" + "1"). I tested millions of passwords with different separators (none, colon, slash, underscore, space).

Result: Nothing.

3. Python's random Module — Full 32-bit Seed Scan
Many scripts from 2015 used Python's random.seed(some_number). Python's random uses the Mersenne Twister (MT19937) internally. I scanned all 4,294,967,296 possible 32-bit seeds in C++. For each seed, I generated 69 keys and checked against the known ones.

Result: No seed worked. The puzzle wasn't made with Python's random.

4. C's rand() — Another Full Scan
The C standard library rand() (glibc) also uses a 32-bit seed. I scanned all 4 billion seeds.

Result: Nothing.

5. Java's java.util.Random — Mathematical State Recovery
Java's Random is a simple linear congruential generator (LCG). If you know two consecutive outputs, you can reverse-engineer the entire state mathematically. I implemented this in java_crack.cpp.

Result: The puzzle keys don't match Java's LCG pattern.

6. Mersenne Twister State Recovery via SAT Solver
I used Z3 (a powerful SAT/SMT solver) to try to reconstruct the Mersenne Twister's internal state from the partial outputs we know. I also tried untwister, a dedicated tool for this.

Result: The SAT solver couldn't crack it. The puzzle likely doesn't use MT19937 at all.

What I Learned
Skill	How I Learned It
BIP32 key derivation	Implementing it from scratch for the seed hunter
Mersenne Twister internals	Building a C++ brute-forcer and a Z3 SAT model
Linear Congruential Generators	Reverse-engineering Java's Random
SAT solving with Z3	Modeling the MT state recovery as a SAT problem
High-performance C++	Writing multi-threaded brute-forcers with early exit
Elliptic curve math	Understanding endomorphisms, GLV optimization
Cryptographic humility	Some problems are designed to be unsolvable
Repository Structure
text
bitcoin-puzzle-systematic-analysis/
│
├── README.md              ← You are here
├── LICENSE                ← MIT
├── .gitignore
│
├── scripts/               ← Python tools (brainwallet tests, SAT solver, etc.)
│   ├── seed_hunt_all.py
│   ├── seed_hunt_sha256.py
│   ├── z3_crack.py
│   ├── gen_observed.py
│   ├── extract_phrases.py
│   └── scanner.py
│
├── cpp/                   ← High-performance C++ brute-forcers
│   ├── mt_brute.cpp       (Python's random, 32-bit seed)
│   ├── rand_brute.cpp     (C's rand, 32-bit seed)
│   ├── java_crack.cpp     (Java's Random, mathematical recovery)
│   └── Makefile
│
├── tools/keyhunt/         ← AlbertoBSD's keyhunt (source only)
│
├── data/                  ← Reference data
│   ├── known_puzzle_keys.txt
│   └── known_public_keys.txt
│
└── docs/                  ← Documentation
    └── CLAIMING.md
How to Run the Tools
Python Scripts
bash
cd scripts
pip install -r requirements.txt
python3 seed_hunt_all.py -f your_wordlist.txt
C++ Programs
bash
cd cpp
make
./mt_brute    # Scan all 32-bit MT19937 seeds
Keyhunt
bash
cd tools/keyhunt
make
./keyhunt -m rmd160 -f target71_rmd.txt -b 71 -l compress -R -t 8 -e
Why I'm Sharing This
I didn't find the key to puzzle #71. But along the way, I built tools that demonstrate:

How to test if a wallet was generated from a weak passphrase

How to verify if a PRNG was used to create private keys

How to approach cryptographic reverse engineering methodically

Why chain codes make HD wallets secure even when child keys leak

If you're learning about Bitcoin internals, wallet security, or just enjoy a good puzzle — I hope this helps you on your journey.

Disclaimer
This code is for educational and research purposes only. The puzzle addresses and their contents belong to their unknown creator. No private keys were recovered through this project. Don't use these tools to try to steal coins. That's not what they're for. 

//Credits & Thanks
AlbertoBSD for the incredible keyhunt tool

Jean-Luc PONS for the Kangaroo solver

The BitcoinTalk puzzle community for years of shared knowledge

Everyone who publishes open-source crypto tools — you make learning possible 

Built with curiosity, on a laptop, late at night. 

