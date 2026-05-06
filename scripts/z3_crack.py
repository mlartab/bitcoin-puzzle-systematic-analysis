from z3 import *
import random

# Mersenne Twister parameters
N = 624
M = 397
MATRIX_A = 0x9908b0df
UPPER_MASK = 0x80000000
LOWER_MASK = 0x7fffffff

# Symbolic state: an array of N 32-bit BitVecs
state = [BitVec(f'state_{i}', 32) for i in range(N)]

# Twist function: modifies state symbolically
def twist():
    for i in range(N):
        y = (state[i] & UPPER_MASK) | (state[(i+1) % N] & LOWER_MASK)
        y = LShR(y, 1) ^ If(y & 1 == 1, BitVecVal(MATRIX_A, 32), BitVecVal(0, 32))
        state[i] = state[(i+M) % N] ^ y

# Tempering transform (output function)
def temper(y):
    y = y ^ (LShR(y, 11))
    y = y ^ ((y << 7) & 0x9d2c5680)
    y = y ^ ((y << 15) & 0xefc60000)
    y = y ^ (LShR(y, 18))
    return y

# Generate consecutive 32-bit outputs
index = N
def rand32():
    global index
    if index >= N:
        twist()
        index = 0
    y = state[index]
    index += 1
    return temper(y)

# Build solver and add puzzle constraints
s = Solver()

# add MT seeding constraints: state[0] = seed, others follow the initialization
seed = BitVec('seed', 32)
s.add(state[0] == seed)
for i in range(1, N):
    s.add(state[i] == (1812433253 * (state[i-1] ^ (LShR(state[i-1], 30))) + i) & 0xffffffff)

# Now we must simulate generating d_1, d_2, ..., d_69 and add constraints
# Each d_n is a 256-bit number = concatenation of 8 outputs (MSB first)
# For n=1, we need 8 outputs (but no constraint)
for _ in range(8):
    rand32()  # d_1, discard

# Puzzle constraints L_n for n=2..69
K_small = {
    2: 3, 3: 7, 4: 8, 5: 21, 6: 49, 7: 76, 8: 224,
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
K_big = {
    66: 0x2832ed74f2b5e35ee,
    67: 0x730fc235c1942c1ae,
    68: 0xbebb3940cd0fc1491,
    69: 0x101d83275fb2bc7e0c
}

for n in range(2, 70):
    # generate 8 words for this n
    words = [rand32() for _ in range(8)]
    # Build the 256-bit number from words (MSB first)
    # We'll constrain the lower k bits (k = n-1) to equal L_n
    k = n - 1
    # L_256 = sum(words[7-i] << (32*i) for i in 0..7)
    # We only need the lower k bits.
    # We'll create a bit-vector of size 256 by concatenation: Concat(words[0], words[1], ... words[7])
    # Then extract the low bits.
    full = Concat(words[0], words[1], words[2], words[3], words[4], words[5], words[6], words[7])
    # Extract low k bits
    low_bits = Extract(k-1, 0, full)
    # L_n value
    if n <= 65:
        L = K_small[n]
    else:
        L = K_big[n] - (1 << (n-1))
    # Add constraint
    s.add(low_bits == BitVecVal(L, k))

print("Solving... (this may take a few seconds)")
if s.check() == sat:
    m = s.model()
    found_seed = m.eval(seed).as_long()
    print(f"Found seed: {found_seed}")
    # Derive puzzle 71
    import random
    random.seed(found_seed)
    for i in range(71):
        d = random.getrandbits(256)
    priv71 = (d & ((1 << 70) - 1)) | (1 << 70)
    print(f"Puzzle #71 private key: {hex(priv71)}")
else:
    print("No solution found. The puzzle may not use standard MT19937.")