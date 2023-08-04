from typing import NamedTuple, Optional, Generic, TypeVar, Iterator
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from hashlib import sha256
from uuid import uuid4
import os.path

T = TypeVar("T")
BASE_PATH = Path.cwd()
# --
# # Simple Structured Version Control
#
# The idea that we're exploring here is to create a version control system
# that is focused on code. The assumption is that a program is a tree defining
# symbols. VCS like git or mercurial primarily work on text files, and do not
# have a notion of the overall program structure.
#
# Obviously, working with text files in general, as well as binary files
# is a baseline requirement for a VCS, but using a more structured representation
# of a subset of files may have the potential of simplifying the design,
# implementation and operation of a VCS.

# --
# ## Positions
#
# We introduce the notion of _position_ that can point to a specific part
# of a file, or a specific part of a semantic representation of a program
# (ie. a symbol).
class Position(NamedTuple):
    """Represents a position in binary"""

    offset: int


class TextPosition(NamedTuple):
    offset: int
    line: Optional[int] = None
    column: Optional[int] = None


# --
# ## Ranges
#
# For text and binary data, we introduce the notion of _range_ that delimits
# a start and an end.


class Range(NamedTuple):
    """A range in an asset"""

    start: Position | TextPosition
    end: Position | TextPosition


# --
# ## Chunks
#
# We consider that a project is made out of chunks. Chunks are bits of
# data (binary or text) that are at a specific location. Chunks can be
# combined into symbols. which represents the semantic components of a
# program.


class Location(NamedTuple):
    path: list[str]


class Symbol(NamedTuple):
    name: list[str]


class HashType(Enum):
    SHA256 = 1


class Signature(NamedTuple):
    hashtype: int
    signature: str


@dataclass
class Chunk:
    location: Location
    scope: Symbol
    range: Range
    signature: Signature


# class MetaData:
#     location: Location
#     attributes: dict[str, bool | int | float | str]


# --
# ## Changes
#
# We're going to leave the task of cataloguing the chunks for later. Instead,
# let's focus on defining operations that determine what we do with the chunk.


@dataclass
class ChunkContext:
    next: Optional[Chunk]
    previous: Optional[Chunk]


@dataclass
class Create(Generic[T]):
    data: T
    chunk: Chunk
    context: ChunkContext


@dataclass
class Delete:
    chunk: Chunk
    context: ChunkContext


@dataclass
class Update(Generic[T]):
    data: T
    chunk: Chunk
    origin: Chunk
    context: ChunkContext


# --
# ## Catalogue
#
# The next step is to create a catalogue of chunks. We can imagine a smart
# cataloguer that would use something like `ctypes` or TreeSitter to build
# a catalogue of chunks with semantic information. For now, we're going
# to take a simple approach:
#
# - Binary files are considered a whole chunk
# - Text files chunks are separated by one or more empty new lines.


def isBinary(path: Path) -> bool:
    """Checks if the given path has binary contents or not"""
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024), b""):
            if b"\0" in chunk:
                return True
            if any(b < 0x09 or (0x0E <= b <= 0x1F) for b in chunk):
                return True
    return False


def signature(
    path: Path, start: Optional[int] = None, end: Optional[int] = None
) -> Signature:
    """Returns the SHA256 signature for the file at the given path, optionally taking
    offsets to calculate the signature of a subset"""
    h = sha256()
    with path.open("rb") as file:
        if start:
            file.seek(start)
        if end is None:
            for chunk in iter(lambda: file.read(1024), b""):
                h.update(chunk)
        else:
            to_read = end - (start or 0)
            while to_read > 0:
                chunk = file.read(min(1024, to_read))
                h.update(chunk)
                to_read -= len(chunk)
    return Signature(HashType.SHA256.value, h.hexdigest())


def makeID() -> str:
    return str(uuid4())


def getLocation(path: Path, base: Path) -> Location:
    return Location(list(path.resolve().relative_to(base.resolve()).parts))


def getChunkData(chunk: Chunk, base: Path = BASE_PATH) -> bytes:
    with open(base / "/".join(chunk.location.path), "rb") as f:
        f.seek(o := chunk.range.start.offset)
        return f.read(chunk.range.end.offset - o)


# This seemingly over-complicated function actually does a naive parsing
# of a text file, and chunking it splitting based on empty lines blocks (more
# than one line required). It's not as easy to implement as it seems,
# try asking GPT-4!
def iterChunks(path: Path, base: Path = BASE_PATH) -> Iterator[Chunk]:
    """Yields chunks detected in the file, alternating chunks with content
    and empty chunks."""
    loc = getLocation(path, base)
    sym = Symbol([makeID()])
    if isBinary(path):
        yield Chunk(
            location=loc,
            scope=sym,
            range=Range(Position(0), Position(path.stat().st_size)),
            signature=signature(path),
        )
    else:
        offset: int = 0
        line: int = 0
        column: int = 0
        TEXT = "-"
        NEWLINE = "N"
        EMPTY_LINE = "L"
        EMPTY_BLOCK = "B"
        state = TEXT
        start_position = TextPosition(0, 0, 0)
        last_block_end: Optional[TextPosition] = None
        last_eol: Optional[TextPosition] = None
        first_eol: Optional[TextPosition] = None
        with path.open("rb") as f:
            while True:
                c: bytes = f.read(1)
                if c == b"":
                    # That's the end of the stream
                    yield Chunk(
                        loc,
                        Symbol([makeID()]),
                        Range(
                            last_block_end or start_position,
                            TextPosition(offset, line, column),
                        ),
                        signature(path, (last_block_end or start_position).offset),
                    )
                    break
                elif c == b"\n":
                    # A newline will trigger a NEWLINE only if we're in the TEXT
                    # state, otherwise we're in an EMPTY_BLOCK.
                    state = NEWLINE if state == TEXT else EMPTY_BLOCK
                    line += 1
                    column = 0
                    # We have a new line. This is only going to be the end
                    # of a block if we have a least two newlines and spaces
                    # inbetween.
                    last_eol = TextPosition(offset + 1, line, column)
                    first_eol = first_eol or last_eol
                elif c == b"\r":
                    # CR characters don't do anythin
                    pass
                elif c in b"\t ":
                    # We have a space character. This may trigger an empty
                    # line if we're just after a NEWLINE
                    state = EMPTY_LINE if state == NEWLINE else state
                    # NOTE: We count tabs as one
                    column += 1
                else:
                    # If we're here, we're definitely in a TEXT state. If we
                    # had an EMPTY_BLOCK then we need to find t he EOL at the
                    # end of the previous block and the last EOL. This becomes
                    # our empty block.
                    if state == EMPTY_BLOCK:
                        assert first_eol
                        yield Chunk(
                            loc,
                            Symbol([makeID()]),
                            Range(
                                last_block_end or start_position,
                                first_eol,
                            ),
                            signature(
                                path,
                                (last_block_end or start_position).offset,
                                first_eol.offset,
                            ),
                        )
                        assert first_eol
                        assert last_eol
                        yield Chunk(
                            loc,
                            Symbol([makeID()]),
                            Range(
                                first_eol,
                                last_eol,
                            ),
                            signature(path, first_eol.offset, last_eol.offset),
                        )
                        last_block_end = last_eol
                    first_eol = None
                    state = TEXT
                offset += 1


for chunk in iterChunks(Path(__file__)):
    print("=== ", getChunkData(chunk))

# EOF
