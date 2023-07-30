from typing import Iterator
import re
from pathlib import Path
from ..utils.files import isBinary
from ..model import (
    Chunk,
    Range,
    Position,
    TextPosition,
    Location,
    Signature,
    signatureFromFile,
)

# NOTE: We probably want to implement per-file-format chunk iterator. We
# should have simple ones like this one, then use ctypes, then use tree
# sitter, then use AST like `python.ast`.
RE_SEPARATOR_BYTES = re.compile(b"\r?\n([\t ]*\r?\n)+")


class BlockParser:
    @staticmethod
    def Chunks(path: Path, base: Path = Path.cwd()) -> Iterator[Chunk]:

        """Iterates on the chunks available at the given `path`. This is typically
        what would be specialized with specific parsers to extract the structure."""
        loc = Location.Get(path, base)
        if isBinary(path):
            yield Chunk(
                location=loc,
                range=Range(Position(0), Position(path.stat().st_size)),
                signature=signatureFromFile(path),
            )
        else:
            offset: int = 0
            line: int = 0
            column: int = 0

            def makeChunk(
                offset: int, line: int, column: int, text: bytes
            ) -> tuple[Chunk, int, int, int]:
                n: int = len(text)
                l: int = line + text.count(b"\n")
                c: int = len(text) - max(0, text.rfind(b"\n"))
                o: int = offset + n
                return (
                    Chunk(
                        location=loc,
                        range=Range(
                            TextPosition(offset, line, column),
                            TextPosition(o, l, c),
                        ),
                        signature=signatureFromFile(path, offset, o),
                    ),
                    o,
                    l,
                    c,
                )

            with open(path, "rb") as f:
                for match in RE_SEPARATOR_BYTES.finditer(text := f.read()):
                    # We generate the previous chunk
                    if (o := match.start()) > offset:
                        chunk, offset, line, column = makeChunk(
                            offset, line, column, text[offset:o]
                        )
                        yield chunk
                        assert offset == o  # nosec: B101
                    chunk, offset, line, column = makeChunk(
                        offset, line, column, text[o : match.end()]
                    )
                    assert offset == match.end()  # nosec: B101
                    yield chunk
                if offset < len(text):
                    chunk, offset, line, column = makeChunk(
                        offset, line, column, text[offset:]
                    )
                    yield chunk

    # EOF
