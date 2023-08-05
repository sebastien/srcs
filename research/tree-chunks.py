from srcs.parsers.block import BlockParser
from srcs.model.chunks import Chunk
from srcs.utils.ids import strencode
from pathlib import Path
from typing import Generic, TypeVar
from dataclasses import dataclass
import nearpy
from nearpy.hashes import RandomBinaryProjections
from nearpy.storage import MemoryStorage

T = TypeVar("T")

# --
# In this notebook, we're looking at how, given a file, we can maintain a list
# of chunks, and compare them across revisions.


@dataclass(frozen=True, slots=True)
class Delta(Generic[T]):
    common: list[T]
    changed: list[T]
    removed: list[T]


# Number of dimensions in the SimHash fingerprint
dimension = 64
# Create a random binary projection hash
rbp = RandomBinaryProjections("rbp", 10)
# Create a memory storage to store the data (you can use other storage options like Redis)
storage = MemoryStorage()


# Data to be indexed (you can use the ID of the document as the data identifier)
data1 = "This is some example text."
data2 = "This is another example text."


def vector(data: bytes):
    return [hash(data) % 2**32 for _ in range(dimension)]


def diffChunks(a: list[Chunk], b: list[Chunk]) -> Delta[Chunk]:
    sig_a = {_.signature.hash: _ for _ in a}
    sig_b = {_.signature.hash: _ for _ in b}

    # Create the engine with the given configuration
    engine = nearpy.Engine(dimension, lshashes=[rbp], storage=storage)
    changed: dict[str, tuple[Chunk, bytes]] = {}
    # Common chunks are easy, they are exactly the same
    for k in sig_a:
        if k in sig_b:
            print("COMMON", k)
        else:
            chunk = sig_a[k]
            data = vector(Chunk.Read(sig_a[k]))
            key = f"a:{strencode(k)}"
            changed[key] = (chunk, data)
            engine.store_vector(data, key)
    for k in sig_b:
        if k not in sig_a:
            chunk = sig_b[k]
            data = vector(Chunk.Read(sig_b[k]))
            key = f"b:{strencode(k)}"
            changed[key] = (chunk, data)
            engine.store_vector(data, key)
    for chunk, data in changed.values():
        # query_vector = nearpy.hashes.vector.Vector(data=data)
        print(data)
        result = engine.neighbours(data)
        print("Nearest neighbors:")
        for neighbor_id, distance in result:
            print(f"ID: {neighbor_id}, Distance: {distance}")

    return Delta([], [], [])


if __name__ == "__main__":
    chunks_a = list(BlockParser.Chunks(Path("data/file-V0.py")))
    chunks_b = list(BlockParser.Chunks(Path("data/file-V1.py")))
    print(diffChunks(chunks_a, chunks_b))

# EOF
