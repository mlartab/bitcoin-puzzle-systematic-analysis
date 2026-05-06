#include <iostream>
#include <iomanip>
#include <cstdint>
#include <cstring>

// Java Random constants
const uint64_t MULT = 0x5DEECE66DULL;
const uint64_t ADD  = 0xBULL;
const uint64_t MASK48 = (1ULL << 48) - 1;

// Modular inverse of MULT mod 2^48 (precomputed)
const uint64_t INV_MULT = 0xDFE05BCB1365ULL; // (MULT * INV_MULT) mod 2^48 = 1

// Known L_n for puzzles 33 and 34 (K - start)
const uint64_t L_33 = 7137437912ULL - (1ULL << 32);   // = 2842470616
const uint64_t L_34 = 14133072157ULL - (1ULL << 33);  // = 5543137565

// Java's nextInt() returns the top 32 bits of the new state, after advancing.
uint32_t nextInt(uint64_t &state) {
    state = (state * MULT + ADD) & MASK48;
    return (uint32_t)(state >> 16);
}

// Reverse one step of the LCG
uint64_t reverseState(uint64_t state) {
    // state_prev = ((state - ADD) * INV_MULT) mod 2^48
    return ((state - ADD) * INV_MULT) & MASK48;
}

// Seed to initial state (setSeed): state = (seed ^ MULT) & MASK48
uint64_t seedToState(uint64_t seed) {
    return (seed ^ MULT) & MASK48;
}

uint64_t stateToSeed(uint64_t state) {
    return (state ^ MULT) & MASK48;
}

// Verify the recovered seed against known puzzles 1-65
bool verifySeed(uint64_t seed) {
    uint64_t state = seedToState(seed);
    // known K values (hex) for n=1..65
    uint64_t K_lo[66] = {0};
    K_lo[1]=1; K_lo[2]=3; K_lo[3]=7; K_lo[4]=8; K_lo[5]=21; K_lo[6]=49;
    K_lo[7]=76; K_lo[8]=224; K_lo[9]=467; K_lo[10]=514;
    K_lo[11]=1155; K_lo[12]=2683; K_lo[13]=5216; K_lo[14]=10544;
    K_lo[15]=26867; K_lo[16]=51510; K_lo[17]=95823; K_lo[18]=198669;
    K_lo[19]=357535; K_lo[20]=863317; K_lo[21]=1811764; K_lo[22]=3007503;
    K_lo[23]=5598802; K_lo[24]=14428676; K_lo[25]=33185509; K_lo[26]=54538862;
    K_lo[27]=111949941; K_lo[28]=227634408; K_lo[29]=400708894; K_lo[30]=1033162084;
    K_lo[31]=2102388551; K_lo[32]=3093472814; K_lo[33]=7137437912; K_lo[34]=14133072157;
    K_lo[35]=20112871792; K_lo[36]=42387769980; K_lo[37]=100251560595; K_lo[38]=146971536592;
    K_lo[39]=323724968937; K_lo[40]=1003651412950; K_lo[41]=1458252205147; K_lo[42]=2895374552463;
    K_lo[43]=7409811047825; K_lo[44]=15404761757071; K_lo[45]=19996463086597; K_lo[46]=51408670348612;
    K_lo[47]=119666659114170; K_lo[48]=191206974700443; K_lo[49]=409118905032525; K_lo[50]=611140496167764;
    K_lo[51]=2058769515153876; K_lo[52]=4216495639600700; K_lo[53]=6763683971478124; K_lo[54]=9974455244496707;
    K_lo[55]=30045390491869460; K_lo[56]=44218742292676575; K_lo[57]=138245758910846492; K_lo[58]=199976667976342049;
    K_lo[59]=525070384258266191; K_lo[60]=1135041350219496382; K_lo[61]=1425787542618654982; K_lo[62]=3908372542507822062;
    K_lo[63]=8993229949524469768u; K_lo[64]=17799667357578236628u; K_lo[65]=30568377312064202855u;

    for (int n = 1; n <= 65; n++) {
        // Generate 256-bit number from 8 nextInt calls
        uint64_t block = 0;
        for (int i = 0; i < 8; i++) {
            uint32_t w = nextInt(state);
            block = (block << 32) | w;
        }
        // Mask with puzzle formula
        uint64_t start = (n == 1) ? 0 : (1ULL << (n-1));
        uint64_t mask = (n == 1) ? 0 : (start - 1);
        uint64_t expected = K_lo[n];
        uint64_t computed = (block & mask) | start;
        if (computed != expected) {
            std::cout << "Mismatch at puzzle " << n << ": expected " << expected << ", got " << computed << "\n";
            return false;
        }
    }
    return true;
}

int main() {
    // Outputs from puzzle 33 and 34 (lowest 32 bits of L)
    uint32_t out33 = L_33 & 0xFFFFFFFF;  // 2842470616 = 0xA96D59D8
    uint32_t out34 = L_34 & 0xFFFFFFFF;  // 5543137565 = 0x14A2D51D

    std::cout << "Output 33: 0x" << std::hex << out33 << "\n";
    std::cout << "Output 34: 0x" << out34 << std::dec << "\n";

    // The call indices: puzzle 33 uses calls 8*32..8*32+7, so the 8th word (lowest) is at index 8*32+7=263.
    // puzzle 34: 8*33+7=271.
    // We know out263 = out33, out271 = out34.
    // We'll iterate over possible lower 16 bits of new_state_263 (state after the 263rd call),
    // which determines state_263 (the state before that call) and then step forward to 271.
    bool found = false;
    uint64_t seed = 0;
    for (uint64_t low16 = 0; low16 <= 0xFFFF && !found; low16++) {
        // new_state_263 = (output33 << 16) | low16
        uint64_t new_state_263 = ((uint64_t)out33 << 16) | low16;
        // state_263 is the state before call 263, which produced new_state_263.
        // state_263 = ((new_state_263 - ADD) * INV_MULT) mod 2^48
        uint64_t state_263 = ((new_state_263 - ADD) * INV_MULT) & MASK48;
        // Now step forward to the state before call 271 (i.e., after call 270).
        // We need to apply nextInt() 8 times to get the start of puzzle 34? Actually we need to generate
        // the output for call 271, which is the 8th word of puzzle 34. So we start from state_263,
        // which is the state before call 263. We'll advance 8 calls to get past the remaining words of puzzle 33?
        // Wait: call 263 is the 8th word of puzzle 33. After that, puzzle 33 is complete. The next calls
        // (264..271) are the first 8 calls of puzzle 34? No: puzzle 34 starts at call 8*33 = 264. So calls
        // 264,265,266,267,268,269,270,271 are the 8 words of puzzle 34. The 8th word is call 271.
        // We need to start from state_263 (before call 263), execute call 263 (which we already have as output33),
        // then execute calls 264..270 (7 calls), then call 271 and check its output.
        uint64_t s = state_263;
        // Call 263
        uint32_t dummy = nextInt(s); // this should equal out33, we can verify but skip for speed.
        // Now s is state after call 263 = state_264 (before call 264)
        // Generate next 7 calls (264..270) – these are words 0..6 of puzzle 34
        for (int i = 0; i < 7; i++) {
            dummy = nextInt(s);
        }
        // Now s is state before call 271
        uint64_t state_before_271 = s;
        // Call 271
        uint32_t out271 = nextInt(state_before_271);
        if (out271 == out34) {
            found = true;
            // We now have state_263. We can recover the initial state (state before call 0) by rewinding 263 steps.
            uint64_t s0 = state_263;
            for (int i = 0; i < 263; i++) {
                s0 = reverseState(s0);
            }
            seed = stateToSeed(s0);
            std::cout << "Recovered seed: " << seed << " (0x" << std::hex << seed << std::dec << ")\n";
        }
    }

    if (!found) {
        std::cout << "Could not recover state. Puzzle does not use Java Random.\n";
        return 1;
    }

    // Verify against all solved puzzles
    if (!verifySeed(seed)) {
        std::cout << "Verification failed! The recovered seed does not produce the known puzzles.\n";
        return 1;
    }
    std::cout << "Seed verified! All known puzzles match.\n";

    // Generate puzzle 71
    uint64_t state = seedToState(seed);
    // Advance to the start of puzzle 71: call index 8*70=560. We need the 8 words (560..567) and apply the mask.
    for (int i = 0; i < 560; i++) {
        nextInt(state);
    }
    // Now state is before call 560 (start of puzzle 71)
    // Generate the 8 words
    uint64_t block71 = 0;
    for (int i = 0; i < 8; i++) {
        uint32_t w = nextInt(state);
        block71 = (block71 << 32) | w;
    }
    // Apply mask for puzzle 71: start = 2^70, mask = 2^70 - 1
    uint64_t start71 = 1ULL << 70;  // but this overflows 64 bits, we need 128-bit.
    // The start is 2^70 = 0x400000000000000000 (70 bits). The mask is 0x3FFFFFFFFFFFFFFFFF.
    // Our block71 is a 256-bit number; we need to mask and OR start.
    // We'll compute using __int128 if available, or do manual 128-bit.
    // Since the low 64 bits of block71 are (block71 & 0xFFFFFFFFFFFFFFFF),
    // and the next 64 bits are (block71 >> 64).
    // The mask is (2^70 - 1): lower 64 bits = 0xFFFFFFFFFFFFFFFF, upper 6 bits = 0x3F.
    uint64_t lo_mask = 0xFFFFFFFFFFFFFFFF;
    uint64_t hi_mask = 0x3F;
    uint64_t block_lo = block71 & 0xFFFFFFFFFFFFFFFF;
    uint64_t block_hi = (block71 >> 64) & 0xFFFFFFFFFFFFFFFF;
    uint64_t masked_lo = block_lo & lo_mask;
    uint64_t masked_hi = block_hi & hi_mask;
    // Start: hi = 0x4, lo = 0 (since 2^70 = (0x4 << 64) | 0)
    uint64_t priv_lo = 0;  // start_lo = 0
    uint64_t priv_hi = 0x4 | masked_hi;
    // Combine and print hex
    std::cout << "Puzzle #71 private key: 0x";
    if (priv_hi) std::cout << std::hex << priv_hi;
    std::cout << std::setfill('0') << std::setw(16) << priv_lo << std::dec << "\n";
    return 0;
}
