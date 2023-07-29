from math import floor, ceil
import os, time

CHARS: str = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def strhash(text: str, seed: int = 5381) -> int:
    """Returns a hash for the given text"""
    hash_value = 5381
    for char in text:
        hash_value = (hash_value * 33) ^ ord(char)
    return hash_value & 0xFFFFFFFF


def numcode(num: int, alphabet: str = CHARS) -> str:
    """Formats a number into a string using the given alphabet."""
    res: list[str] = []
    n: int = len(alphabet)
    v: int = abs(num)
    while v > 0:
        res.insert(0, alphabet[v % n])
        v = floor(v / n)
    return "".join(res)


def jid(node: int = 0) -> str:
    """Creates an id that contains a timestamp, a node id and some random
    factor, that should make the jobs ids largely sortable"""
    t: str = numcode(time.clock_gettime_ns(time.CLOCK_TAI)).rjust(14, "0")[:14]
    n: str = numcode(node).rjust(4, "0")[:4]
    # NOTE: math.log(math.pow(2,3 * 8), 62) ~ 3
    r = numcode(int.from_bytes(os.urandom(3))).rjust(4, "0")[:4]
    return f"{t}-{n}-{r}"


def strencode(data: bytes, mapping: str = CHARS) -> str:
    n: int = len(mapping)
    num = int.from_bytes(data, byteorder="big")
    encoded: list[str] = []
    while num > 0:
        num, remainder = divmod(num, n)
        encoded.append(mapping[remainder])
    return "".join(encoded)


def strdecode(encoded: str, mapping: str = CHARS) -> bytes:

    n = len(mapping)
    num = 0
    for char in encoded:
        if char not in CHARS:
            raise ValueError(f"Invalid character in encoded string: {char}")

        num = num * n + CHARS.index(char)

    # Convert the integer back to bytes
    return num.to_bytes((num.bit_length() + 7) // 8, byteorder="big")


def strchunks(text: str, size: int = 10) -> list[str]:
    n = ceil(len(text) / size)
    res: list[str] = []
    o: int = 0
    while o < n:
        res.append(text[o * size : (o + 1) * size])
        o += 1
    return res


# EOF
