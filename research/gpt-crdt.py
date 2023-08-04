# --
# Prompt: I'm looking at implementing a CRDT structure to manage changes to
# text chunk. A text chunk is a contiguous set of lines of text, typically of
# less than 100 lines of code. What would the high-level interface of such a
# structure be like in Python?

# --
# That's a good start, can you:
# 1) Use `camelCase` for all method names and parameters (you can use `snake_case` for local variables)
# 2) Add typing annotation, as they bring clarity
# 3) Define primitives as NamedTuple subclasses or `@dataclass` decorated classes.
# 4) Implement each operation, and illustrate how you would apply changes to a chunk


from dataclasses import dataclass
from typing import List, Optional, Union
from uuid import uuid4


@dataclass
class TextLine:
    content: str
    position: int
    uniqueID: str

    def __str__(self) -> str:
        return self.content


class TextChunkCRDT:
    def __init__(self) -> None:
        self.lines: List[TextLine] = []

    def insert(self, content: str, position: int) -> None:
        uniqueID = str(uuid4())
        newLine = TextLine(content, position, uniqueID)
        self.lines.append(newLine)
        self.lines.sort(key=lambda line: line.position)

    def delete(self, uniqueID: str) -> None:
        self.lines = [line for line in self.lines if line.uniqueID != uniqueID]

    def update(self, uniqueID: str, newContent: str) -> None:
        for line in self.lines:
            if line.uniqueID == uniqueID:
                line.content = newContent
                break

    def merge(self, otherCRDT: "TextChunkCRDT") -> None:
        for line in otherCRDT.lines:
            if line.uniqueID not in [
                existingLine.uniqueID for existingLine in self.lines
            ]:
                self.lines.append(line)
        self.lines.sort(key=lambda line: line.position)

    def toString(self) -> str:
        return "\n".join([str(line) for line in self.lines])

    def fromString(self, textString: str) -> None:
        lines = textString.split("\n")
        for idx, line in enumerate(lines):
            self.insert(line, idx)

    def getLine(self, uniqueID: str) -> Optional[TextLine]:
        for line in self.lines:
            if line.uniqueID == uniqueID:
                return line
        return None

    def getLines(self) -> List[TextLine]:
        return self.lines

    # Initialize two CRDT instances (representing two replicas)


crdt1 = TextChunkCRDT()
crdt2 = TextChunkCRDT()

# Populate CRDT1 with a sample text
sampleText = "Hello, world!\nThis is a text chunk."
crdt1.fromString(sampleText)

# Insert a line in CRDT1
crdt1.insert("New line in the middle", 1)

# Merge changes from CRDT1 to CRDT2
crdt2.merge(crdt1)

# Update a line in CRDT2
uniqueID = crdt2.getLines()[0].uniqueID
crdt2.update(uniqueID, "Hello, CRDT!")

# Delete a line in CRDT2
uniqueID = crdt2.getLines()[2].uniqueID
crdt2.delete(uniqueID)

# Merge changes back to CRDT1
crdt1.merge(crdt2)

# Print the final state of CRDT1
print(crdt1.toString())

# EOF
