# SRCS Model

The following model shows the representation that SRCS makes of a tree
of files. The breaking down of files into chunks and symbols is done
through specialized backends, typically per file format, defaulting to
generic text and binary backends.

    [ Symbol ]
    | name   |
    | parent |
    |
    |
    V
    [ Chunk     ]<------[File]<----[Tree]
    | location  |
    | range     | 
    | signature | 
    |
    |
    V
    [ Range ]
    | start |
    | end   |

Semantic level:

- Symbol: the representation of a semantic element, typically a module,
  class, function, etc. However, these could be pieces of data, assets,
  etc. A symbol's name is unique, and symbols together form a tree.

Filesystem level:

- File: composed of a set of contiguous chunks, along with metadata,
  such as owner and permissions.

- Tree: a collection of files.

Data level:

- Chunks: represent a fragment of a file, this chunk typically is
  associated with a symbol to define its semantic meaning (a function, a
  class, etc)

- Range: represents the subset of the content of file, ranges can be
  either binary, or text, in which case they have column/line.

## Revision Control

The revision control is made by detecting and managing changes between
these different elements.

At the data level, that means being able to determine the relationship
between two chunks:

- Do they share a common content?
- How different are they?
- What are the specific differences?

Knowing this information makes it possible to identify these scenario:

- A chunk got moved and potentially modified
- A chunk got duplicated and potentially modified
- A chunk got split into other chunks
- A chunk got (partially) removed
