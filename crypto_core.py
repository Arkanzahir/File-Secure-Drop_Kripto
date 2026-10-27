"""Algoritma mandiri untuk tugas kelas. Tidak memakai library kriptografi.
DH: pembentukan rahasia sesi. ElGamal: enkripsi blok file.
SHA-256/HMAC: integritas ciphertext dengan kunci hasil DH.
Parameter 61 bit sengaja untuk demo cepat, bukan keamanan produksi.
"""
import secrets

P = 2305843009213693951  # 2**61 - 1, prima Mersenne
G = 37
BLOCK = 7  # 56 bit, sehingga setiap blok selalu < P
WIDTH = 8  # setiap komponen ciphertext ditulis 8 byte

def mod_pow(base, exponent, modulus):
    """Square-and-multiply O(log exponent), tanpa pow modular bawaan."""
    if exponent < 0 or modulus < 2:
        raise ValueError('Pangkat atau modulus tidak valid.')
    result = 1
    base %= modulus
    while exponent:
        if exponent & 1:
            result = result * base % modulus
        base = base * base % modulus
        exponent >>= 1
    return result

def inverse(value, modulus):
    """Euclid diperluas: mencari invers perkalian modulo."""
    old_r, r, old_t, t = modulus, value % modulus, 0, 1
    while r:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_t, t = t, old_t - q * t
    if old_r != 1:
        raise ValueError('Invers tidak tersedia.')
    return old_t % modulus

def random_private(p=P):
    return secrets.randbelow(p - 3) + 2

def keygen(p=P, g=G, private=None):
    """ElGamal: y = g^x mod p. x privat, (y,g,p) publik."""
    x = random_private(p) if private is None else private
    if not 1 < x < p - 1:
        raise ValueError('Kunci privat di luar rentang.')
    return x, mod_pow(g, x, p)

def diffie_hellman(p=P, g=G, a=None, b=None):
    """Dua pihak menghitung K secara independen, tanpa mengirim a/b/K."""
    a = random_private(p) if a is None else a
    b = random_private(p) if b is None else b
    if not (1 < a < p-1 and 1 < b < p-1):
        raise ValueError('Kunci DH di luar rentang.')
    A, B = mod_pow(g, a, p), mod_pow(g, b, p)
    sender_key, receiver_key = mod_pow(B, a, p), mod_pow(A, b, p)
    if sender_key != receiver_key:
        raise ValueError('Pertukaran kunci gagal.')
    return {'a': a, 'b': b, 'A': A, 'B': B, 'sender_key': sender_key, 'receiver_key': receiver_key}

def encrypt_number(m, public, k, p=P, g=G):
    if not 0 <= m < p or not 1 < k < p-1:
        raise ValueError('Blok atau k di luar rentang.')
    c1 = mod_pow(g, k, p)
    c2 = m * mod_pow(public, k, p) % p
    return c1, c2

def decrypt_number(c1, c2, private, p=P):
    if not (0 < c1 < p and 0 <= c2 < p):
        raise ValueError('Ciphertext di luar rentang.')
    s = mod_pow(c1, private, p)
    return c2 * inverse(s, p) % p

def encrypt_bytes(data, public):
    """ElGamal langsung per 7 byte. k acak berbeda di tiap blok file."""
    output, used = bytearray(), set()
    for offset in range(0, len(data), BLOCK):
        k = random_private()
        while k in used:
            k = random_private()
        used.add(k)
        m = int.from_bytes(data[offset:offset+BLOCK], 'big')
        c1, c2 = encrypt_number(m, public, k)
        output.extend(c1.to_bytes(WIDTH, 'big'))
        output.extend(c2.to_bytes(WIDTH, 'big'))
    return bytes(output)

def decrypt_bytes(cipher, length, private):
    if length < 0 or len(cipher) != ((length + BLOCK-1)//BLOCK)*WIDTH*2:
        raise ValueError('Ukuran ciphertext tidak sesuai.')
    output = bytearray()
    for offset in range(0, len(cipher), WIDTH*2):
        c1 = int.from_bytes(cipher[offset:offset+WIDTH], 'big')
        c2 = int.from_bytes(cipher[offset+WIDTH:offset+WIDTH*2], 'big')
        m = decrypt_number(c1, c2, private)
        chunk_len = min(BLOCK, length-len(output))
        if m >= 1 << (8*chunk_len):
            raise ValueError('Blok hasil dekripsi tidak valid.')
        output.extend(m.to_bytes(chunk_len, 'big'))
    return bytes(output)

# SHA-256 ditulis sendiri. Konstanta dan operasi mengikuti FIPS 180-4.
_K = (0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2)
_MASK = 0xffffffff
def _ror(x,n):
    return ((x >> n) | (x << (32-n))) & _MASK

def sha256(data):
    data = bytes(data)
    bit_length = len(data)*8
    data += b'\x80'
    data += b'\x00' * ((56-len(data)%64)%64)
    data += bit_length.to_bytes(8,'big')
    h = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]
    for offset in range(0,len(data),64):
        w = [int.from_bytes(data[offset+i:offset+i+4],'big') for i in range(0,64,4)]
        for i in range(16,64):
            s0 = _ror(w[i-15],7)^_ror(w[i-15],18)^(w[i-15]>>3)
            s1 = _ror(w[i-2],17)^_ror(w[i-2],19)^(w[i-2]>>10)
            w.append((w[i-16]+s0+w[i-7]+s1)&_MASK)
        a,b,c,d,e,f,g,j = h
        for i in range(64):
            s1 = _ror(e,6)^_ror(e,11)^_ror(e,25)
            ch = (e&f)^((~e)&g)
            t1 = (j+s1+ch+_K[i]+w[i])&_MASK
            s0 = _ror(a,2)^_ror(a,13)^_ror(a,22)
            maj = (a&b)^(a&c)^(b&c)
            t2 = (s0+maj)&_MASK
            j,g,f,e,d,c,b,a = g,f,e,(d+t1)&_MASK,c,b,a,(t1+t2)&_MASK
        h = [(x+y)&_MASK for x,y in zip(h,[a,b,c,d,e,f,g,j])]
    return b''.join(v.to_bytes(4,'big') for v in h)

def hmac_sha256(key, data):
    if len(key)>64:
        key=sha256(key)
    key=key.ljust(64,b'\x00')
    return sha256(bytes(v^0x5c for v in key)+sha256(bytes(v^0x36 for v in key)+data))

def integrity_key(shared):
    return sha256(b'FILE-SECURE-DROP-DH-INTEGRITY-v1'+shared.to_bytes(WIDTH,'big'))

def same_tag(a,b):
    if len(a)!=len(b):
        return False
    mismatch=0
    for x,y in zip(a,b):
        mismatch |= x^y
    return mismatch==0

def validate_parameters():
    """Lucas-Lehmer membuktikan prima Mersenne; akar primitif via faktor p-1."""
    s=4
    for _ in range(59):
        s=(s*s-2)%P
    if s!=0:
        raise ValueError('Parameter prima tidak valid.')
    n=P-1
    factors=[]
    d=2
    while d*d<=n:
        if n%d==0:
            factors.append(d)
            while n%d==0:
                n//=d
        d+=1
    if n>1:
        factors.append(n)
    if any(mod_pow(G,(P-1)//q,P)==1 for q in factors):
        raise ValueError('Basis bukan akar primitif.')
    return True
