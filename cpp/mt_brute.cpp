#include <iostream>
#include <vector>
#include <cstring>
#include <thread>
#include <mutex>
#include <atomic>
#include <iomanip>
#include <climits>
#include <string>

// ─────────────────────────────────────────────────
// MT19937 (Python random.Random) replication
// ─────────────────────────────────────────────────
class MT19937 {
    uint32_t state[624];
    int idx;

    void twist() {
        for (int i = 0; i < 624; i++) {
            uint32_t y = (state[i] & 0x80000000) + (state[(i+1) % 624] & 0x7fffffff);
            state[i] = state[(i + 397) % 624] ^ (y >> 1);
            if (y & 1) state[i] ^= 0x9908b0df;
        }
        idx = 0;
    }

public:
    void seed(uint32_t s) {
        state[0] = s;
        for (int i = 1; i < 624; i++) {
            uint32_t prev = state[i-1];
            state[i] = 1812433253u * (prev ^ (prev >> 30)) + i;
        }
        idx = 624;
    }

    uint32_t rand32() {
        if (idx >= 624) twist();
        uint32_t y = state[idx++];
        y ^= (y >> 11);
        y ^= (y << 7) & 0x9d2c5680;
        y ^= (y << 15) & 0xefc60000;
        y ^= (y >> 18);
        return y;
    }

    // getrandbits(256) – first word is highest 32 bits.
    void getrandbits256(uint32_t out[8]) {
        for (int i = 0; i < 8; i++) out[i] = rand32();
    }
};

// ─────────────────────────────────────────────────
// 128‑bit helper functions
// ─────────────────────────────────────────────────
void set128(uint64_t &lo, uint64_t &hi, uint64_t l, uint64_t h = 0) { lo = l; hi = h; }

// subtraction: res = a - b, assumed a >= b
void sub128(uint64_t &lo, uint64_t &hi, uint64_t a_lo, uint64_t a_hi, uint64_t b_lo, uint64_t b_hi) {
    if (a_lo < b_lo) {
        lo = a_lo - b_lo;
        hi = a_hi - b_hi - 1;
    } else {
        lo = a_lo - b_lo;
        hi = a_hi - b_hi;
    }
}

// return lower 64 bits of (x & mask) where mask is 128-bit
uint64_t and128_lo(uint64_t x_lo, uint64_t x_hi, uint64_t mask_lo, uint64_t mask_hi) {
    return (x_lo & mask_lo) | ((x_hi & mask_hi) << 0); // actually hi bits not needed for lo, just mask_lo
}

// For checking L == (d & mask) we compare lower bits using lo/hi.
bool eq_masked(const uint32_t d_words[8], uint64_t mask_lo, uint64_t mask_hi, uint64_t L_lo, uint64_t L_hi) {
    // Convert d_words (big-endian, first word is high) into 256-bit number
    // We only need the lower part up to the mask bits. For n ≤ 64 mask is 64‑bit, we can just use the lowest 64 bits from d_words.
    // Actually d_words[7] is lowest 32 bits, d_words[6] next, etc. We'll extract the full 256-bit as uint64_t chunks (little-endian order from most significant?).
    // Since the mask may be up to 68 bits for n=69, we need 128-bit.
    // Build a 256-bit number stored as four 64-bit limbs: limbs[0] = high 64 bits, limbs[3] = low 64 bits.
    uint64_t limbs[4];
    for (int i = 0; i < 4; i++) {
        limbs[i] = ((uint64_t)d_words[2*i] << 32) | d_words[2*i+1];
    }
    // limbs[3] contains the lowest 64 bits (d_words[6],d_words[7])
    uint64_t d_lo = limbs[3];
    uint64_t d_hi = limbs[2]; // next 64 bits (bits 64..127)
    // Apply mask (128-bit)
    uint64_t masked_lo = d_lo & mask_lo;
    uint64_t masked_hi = d_hi & mask_hi;
    return (masked_lo == L_lo) && (masked_hi == L_hi);
}

// ─────────────────────────────────────────────────
// Puzzle constraints (n, mask, expected L)
// ─────────────────────────────────────────────────
struct Constraint {
    int n;
    uint64_t mask_lo, mask_hi;
    uint64_t L_lo, L_hi;
};

std::vector<Constraint> constraints;

void add_constraint(int n, uint64_t K_lo, uint64_t K_hi) {
    Constraint c;
    c.n = n;
    uint64_t start_lo = 0, start_hi = 0;
    if (n <= 64) {
        start_lo = (n == 64) ? 0x8000000000000000ULL : (1ULL << (n-1));
        start_hi = 0;
    } else {
        int bits = n - 1; // 65..69
        int shift_hi = bits / 64;  // 1
        int shift_lo = bits % 64;  // 1..5
        start_hi = (shift_hi > 0) ? (1ULL << shift_lo) : 0; // actually 1<<shift_lo for hi part? Wrong: 2^65 = hi=2, lo=0. So hi = 1 << (bits-64), lo=0.
        if (bits == 65) { start_hi = 2; start_lo = 0; }
        else if (bits == 66) { start_hi = 4; start_lo = 0; }
        else if (bits == 67) { start_hi = 8; start_lo = 0; }
        else if (bits == 68) { start_hi = 16; start_lo = 0; }
        else if (bits == 69) { start_hi = 32; start_lo = 0; }
    }
    // mask = start - 1 (128-bit)
    uint64_t mask_lo, mask_hi;
    if (start_lo == 0 && start_hi == 0) {
        mask_lo = mask_hi = 0;
    } else {
        // subtract 1
        if (start_lo == 0) {
            mask_lo = ~0ULL;
            mask_hi = start_hi - 1;
        } else {
            mask_lo = start_lo - 1;
            mask_hi = start_hi;
        }
    }
    // L = K - start
    uint64_t L_lo, L_hi;
    sub128(L_lo, L_hi, K_lo, K_hi, start_lo, start_hi);
    c.mask_lo = mask_lo; c.mask_hi = mask_hi;
    c.L_lo = L_lo; c.L_hi = L_hi;
    constraints.push_back(c);
}

void init_constraints() {
    // K_n values for n=2..69
    // For n=2..65: direct integer values
    uint64_t K_small_lo[66] = {0}; // index n
    K_small_lo[2]=3; K_small_lo[3]=7; K_small_lo[4]=8; K_small_lo[5]=21; K_small_lo[6]=49;
    K_small_lo[7]=76; K_small_lo[8]=224; K_small_lo[9]=467; K_small_lo[10]=514;
    K_small_lo[11]=1155; K_small_lo[12]=2683; K_small_lo[13]=5216; K_small_lo[14]=10544;
    K_small_lo[15]=26867; K_small_lo[16]=51510; K_small_lo[17]=95823; K_small_lo[18]=198669;
    K_small_lo[19]=357535; K_small_lo[20]=863317; K_small_lo[21]=1811764; K_small_lo[22]=3007503;
    K_small_lo[23]=5598802; K_small_lo[24]=14428676; K_small_lo[25]=33185509; K_small_lo[26]=54538862;
    K_small_lo[27]=111949941; K_small_lo[28]=227634408; K_small_lo[29]=400708894; K_small_lo[30]=1033162084;
    K_small_lo[31]=2102388551; K_small_lo[32]=3093472814; K_small_lo[33]=7137437912; K_small_lo[34]=14133072157;
    K_small_lo[35]=20112871792; K_small_lo[36]=42387769980; K_small_lo[37]=100251560595; K_small_lo[38]=146971536592;
    K_small_lo[39]=323724968937; K_small_lo[40]=1003651412950; K_small_lo[41]=1458252205147; K_small_lo[42]=2895374552463;
    K_small_lo[43]=7409811047825; K_small_lo[44]=15404761757071; K_small_lo[45]=19996463086597; K_small_lo[46]=51408670348612;
    K_small_lo[47]=119666659114170; K_small_lo[48]=191206974700443; K_small_lo[49]=409118905032525; K_small_lo[50]=611140496167764;
    K_small_lo[51]=2058769515153876; K_small_lo[52]=4216495639600700; K_small_lo[53]=6763683971478124; K_small_lo[54]=9974455244496707;
    K_small_lo[55]=30045390491869460; K_small_lo[56]=44218742292676575; K_small_lo[57]=138245758910846492; K_small_lo[58]=199976667976342049;
    K_small_lo[59]=525070384258266191; K_small_lo[60]=1135041350219496382; K_small_lo[61]=1425787542618654982; K_small_lo[62]=3908372542507822062;
    K_small_lo[63]=8993229949524469768u; K_small_lo[64]=17799667357578236628u; K_small_lo[65]=30568377312064202855u;

    for (int n = 2; n <= 65; n++) {
        add_constraint(n, K_small_lo[n], 0);
    }

    // n=66..69 from hex strings
    struct HexK { int n; const char *hex; };
    HexK big[] = {
        {66, "2832ed74f2b5e35ee"},
        {67, "730fc235c1942c1ae"},
        {68, "bebb3940cd0fc1491"},
        {69, "101d83275fb2bc7e0c"}
    };
    for (auto &h : big) {
        uint64_t lo = 0, hi = 0;
        std::string s = h.hex;
        size_t len = s.length();
        if (len <= 16) {
            lo = std::stoull(s, nullptr, 16);
        } else {
            std::string lo_str = s.substr(len-16);
            std::string hi_str = s.substr(0, len-16);
            lo = std::stoull(lo_str, nullptr, 16);
            hi = std::stoull(hi_str, nullptr, 16);
        }
        add_constraint(h.n, lo, hi);
    }
}

// ─────────────────────────────────────────────────
// Global state
// ─────────────────────────────────────────────────
std::atomic<bool> found(false);
std::mutex print_mutex;
uint32_t winning_seed = 0;

void worker(uint32_t start, uint32_t end) {
    MT19937 mt;
    uint32_t d_words[8];

    for (uint32_t s = start; s <= end && !found; s++) {
        mt.seed(s);
        // Generate d_n for n=2..69, compare each constraint consecutively
        // We must generate in order: n=2 first, then n=3, etc. (skip n=1)
        // To avoid generating all 69 values for rejected seeds, we do early exit.
        bool match = true;
        // Use an index to track which constraint we're on.
        for (size_t ci = 0; ci < constraints.size() && match; ci++) {
            int n = constraints[ci].n;
            // Advance MT to produce the d_n for this n. For n=2, we need to have generated d_2 after d_1.
            // We'll generate d_1 and discard, then d_2, etc. But n are not sequential; constraints have n from 2..69 sorted.
            // We'll generate d for each n in a single loop. The easiest: after seeding, we'll generate d_1..d_69, store them, then check.
            // That would be inefficient per seed. Better: for each constraint, we generate all intermediate d's up to that n.
            // Since constraints are sorted, we can keep a counter 'current_n' and generate until we reach n.
            // We'll do that.
        }

        // Simplified: after seeding, generate d_1..d_69 once and check all constraints.
        // 69 calls to getrandbits256 is cheap. We'll just generate all and check.
        // We'll implement this way:
        // Generate d_1..d_69, then iterate over constraints.
        // To avoid overhead, use a single loop over n=1..69 and check if n is in constraints.
        // Since constraints vector size 68, we'll just generate all and compare.
        bool ok = true;
        mt.seed(s);
        // We'll generate from n=1 upward, and check constraint when n matches.
        for (int n = 2; n <= 69 && ok; n++) {
            // skip generation for n=1 (no constraint), but we must call getrandbits256 for n=1 to advance.
            if (n == 2) {
                // first, generate d_1 (n=1) and discard
                mt.getrandbits256(d_words);
            }
            mt.getrandbits256(d_words);
            // check if this n has a constraint
            // Since constraints are sorted, we can just use an index into constraints.
            // We'll use a pointer that increments when we've matched the current constraint's n.
        }
        // Better: iterate over constraints, and for each, call getrandbits256 for n = prev_n+1 .. constraint.n, then check.
        {
            int last_n = 2; // first constraint n >=2
            mt.seed(s);
            // generate d_1 first (n=1) – discard
            mt.getrandbits256(d_words);
            bool valid = true;
            for (const auto &c : constraints) {
                while (last_n < c.n) {
                    mt.getrandbits256(d_words); // not needed, just advance
                    last_n++;
                }
                // now last_n == c.n, generate its d
                mt.getrandbits256(d_words);
                last_n++;
                // check
                if (!eq_masked(d_words, c.mask_lo, c.mask_hi, c.L_lo, c.L_hi)) {
                    valid = false;
                    break;
                }
            }
            if (valid) {
                std::lock_guard<std::mutex> lock(print_mutex);
                if (!found) {
                    found = true;
                    winning_seed = s;
                    std::cout << "\n🎉 Seed found: " << s << std::endl;
                    // Derive puzzle #71
                    // First, we must generate d_70 and d_71 (we have already generated up to d_69)
                    // last_n is currently 70 after the loop? Actually after checking n=69, last_n becomes 70 (we incremented after generating). So we need d_70 and d_71.
                    // Advance to d_70: already? After checking n=69, we generated d_69 and then last_n became 70 (means next to generate is 70). So we need to generate d_70:
                    mt.getrandbits256(d_words); // d_70
                    mt.getrandbits256(d_words); // d_71
                    // Compute K_71 = 2^70 + (d_71 & (2^70-1))
                    // 2^70: start = 0x400000000000000000 (70 bits)
                    // mask = 0x3FFFFFFFFFFFFFFFFF (70 bits) = (1<<70)-1
                    // Extract d_71 as 256-bit, get lower 70 bits.
                    uint64_t start_lo = 0, start_hi = 0x400; // 2^70 = 0x400 << 64 = 0x4000000000000000 0000000000000000 ? No, 2^70 = 1,180,591,620,717,411,303,424 = 0x400000000000000000 (that's 70 bits). In 128-bit: hi = 0x40, lo = 0.
                    // Actually 2^70 = 0x400000000000000000 = (0x4 << 64) | 0, so hi = 0x4, lo = 0.
                    uint64_t mask_lo = 0xFFFFFFFFFFFFFFFF; // lower 64 bits of mask
                    uint64_t mask_hi = 0x3F; // mask = 2^70-1 = 0x3FFFFFFFFFFFFFFFFF -> hi = 0x3F, lo = 0xFFFFFFFFFFFFFFFF
                    // d_71 low bits
                    uint64_t d_lo = ((uint64_t)d_words[6] << 32) | d_words[7];
                    uint64_t d_hi = ((uint64_t)d_words[4] << 32) | d_words[5]; // bits 64..127
                    uint64_t masked_lo = d_lo & mask_lo;
                    uint64_t masked_hi = d_hi & mask_hi;
                    uint64_t priv_lo = masked_lo; // start_lo = 0
                    uint64_t priv_hi = 0x4 | masked_hi; // start_hi = 0x4
                    // Print private key hex
                    std::cout << "Puzzle #71 private key: 0x";
                    if (priv_hi > 0) std::cout << std::hex << priv_hi;
                    std::cout << std::setfill('0') << std::setw(16) << priv_lo << std::dec << "\n";
                }
            }
        }
    }
}

int main() {
    init_constraints();
    unsigned int n_threads = std::thread::hardware_concurrency();
    if (n_threads == 0) n_threads = 8;
    std::cout << "Testing all 32-bit seeds for Python MT19937...\n";
    const uint64_t total_seeds = 1ULL << 32;
    uint64_t chunk = total_seeds / n_threads;
    std::vector<std::thread> threads;
    for (unsigned t = 0; t < n_threads; t++) {
        uint32_t start = t * chunk;
        uint32_t end = (t == n_threads - 1) ? 0xFFFFFFFF : (t + 1) * chunk - 1;
        threads.emplace_back(worker, start, end);
    }
    for (auto &th : threads) th.join();
    if (!found) std::cout << "No matching seed found.\n";
    return 0;
}