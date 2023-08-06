from srcs.parsers.block import BlockParser
from srcs.model.chunks import Chunk
from srcs.utils.ids import strencode
from pathlib import Path
from typing import Generic, TypeVar, NamedTuple
from dataclasses import dataclass

import re
import difflib


T = TypeVar("T")

# --
# In this notebook, we're looking at how, given a file, we can maintain a list
# of chunks, and compare them across revisions.


@dataclass(frozen=True, slots=True)
class Delta(Generic[T]):
    common: list[T]
    changed: list[T]
    removed: list[T]


class TextChunk(NamedTuple):
    chunk: Chunk
    text: str

    @staticmethod
    def Load(chunk: Chunk) -> "TextChunk":
        return TextChunk(chunk, Chunk.Read(chunk).decode("utf-8"))


# NOTE: The key challenge here is to find which chunks may be a variant of another chunk. This
# is definitely a tricky thing to do.

RE_NONWORD = re.compile(r"[^A-Za-z_0-9]+")
RE_NONWORD = re.compile(r"[^A-Za-z_0-9]+")


def words(text: str) -> list[str]:
    return RE_NONWORD.sub(" ", text).strip().split()


# FROM: ChatGPT
def soundex(word: str):
    # Step 1: Convert the word to uppercase
    word = word.upper()
    # Step 2: Remove non-alphabetic characters and convert to uppercase
    word = "".join(char for char in word if char.isalpha())
    # Step 3: Handle empty and single-letter words
    if not word or len(word) == 1:
        return word
    # Step 4: Replace consonants with appropriate digits
    soundex_mapping = {
        "BFPV": "1",
        "CGJKQSXZ": "2",
        "DT": "3",
        "L": "4",
        "MN": "5",
        "R": "6",
    }
    first_letter = word[0]
    soundex_code = first_letter
    for char in word[1:]:
        for key, value in soundex_mapping.items():
            if char in key:
                if value != soundex_code[-1]:
                    soundex_code += value
    # Step 5: Remove vowels and digits that repeat consecutively
    soundex_code = soundex_code[1:]
    soundex_code = "".join(
        char
        for idx, char in enumerate(soundex_code)
        if idx == 0 or char != soundex_code[idx - 1]
    )
    # Step 6: Pad with zeros to get a 4-character code
    soundex_code = soundex_code.ljust(3, "0")

    return first_letter + soundex_code


class ChunksDiff(NamedTuple):
    removed: list[TextChunk]
    added: list[TextChunk]
    changed: list[tuple[TextChunk, TextChunk]]


class DifferChunks:
    @staticmethod
    def Distance(chunk: TextChunk, other: TextChunk) -> int:
        # NOTE: Here we use words and soundex to normalize. Obviously
        # we should have pre-calculate the soundex words.
        matcher = difflib.SequenceMatcher(
            None,
            ta := [soundex(_) for _ in words(chunk.text)],
            tb := [soundex(_) for _ in words(other.text)],
        )
        matches = matcher.get_matching_blocks()
        # The higher the number, the more common
        return sum(_.size + 1 for _ in matches)

    @classmethod
    def Relate(cls, a: list[TextChunk], b: list[TextChunk]) -> ChunksDiff:
        distance: dict[int, dict[int, int]] = {}
        matched: dict[int, int] = {}
        for i, c in enumerate(a):
            distance[i] = {j: cls.Distance(c, d) for j, d in enumerate(b)}
        for i, c in enumerate(a):
            k = max(distance[i].values())
            for j, kk in distance[i].items():
                if kk == k:
                    print("===\nMATCHED", i, j)
                    print(f"A={a[i].text}")
                    print(f"B={b[j].text}")
                    matched[i] = j
                    break
        removed: list[TextChunk] = [_ for i, _ in enumerate(a) if i not in matched]
        added: list[TextChunk] = [
            _ for j, _ in enumerate(b) if j not in matched.values()
        ]
        return ChunksDiff(added, removed, [(a[i], b[j]) for i, j in matched.items()])


def diffChunks(a: list[Chunk], b: list[Chunk]) -> Delta[Chunk]:
    sig_a: dict[bytes, Chunk] = {_.signature.hash: _ for _ in a}
    sig_b: dict[bytes, Chunk] = {_.signature.hash: _ for _ in b}

    # Create the engine with the given configuration
    removed: set[bytes] = set()
    common: set[bytes] = set()
    added: set[bytes] = set()

    # Common chunks are easy, they are exactly the same
    for k in sig_a:
        if k in sig_b:
            common.add(k)
        else:
            removed.add(k)
    for k in sig_b:
        if k not in sig_a:
            added.add(k)

    diff = DifferChunks.Relate(
        [TextChunk.Load(sig_a[_]) for _ in removed],
        [TextChunk.Load(sig_b[_]) for _ in added],
    )
    print(diff)

    return Delta([], [], [])


if __name__ == "__main__":
    chunks_a = list(BlockParser.Chunks(Path("data/file-V0.py")))
    chunks_b = list(BlockParser.Chunks(Path("data/file-V1.py")))
    print(diffChunks(chunks_a, chunks_b))

# EOF
