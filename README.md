![pymutantic](logo.png)

User-friendly tool for combining [pycrdt](https://github.com/jupyter-server/pycrdt) and [pydantic](https://docs.pydantic.dev/latest/).

## Overview

* `pymutantic.MutantModel` - A type safe `pycrdt.Doc` ⟷ pydantic `pydantic.BaseModel` mapping with granular editing.
* `pymutantic.JsonPathMutator` - Make edits using json path.

## Installation

```bash
pip install pycrdt-utils
```

## Usage

### `MutantModel`

Given a pydantic schema...

```python
from pydantic import BaseModel, Field
from typing import List

class Author(BaseModel):
    id: str
    name: str

class Comment(BaseModel):
    id: str
    author: Author
    content: str

class Post(BaseModel):
    id: str
    title: str
    content: str
    author: Author
    comments: List[Comment] = Field(default_factory=list)

class BlogPageConfig(BaseModel):
    collection: str
    posts: List[Post] = Field(default_factory=list)
```

Create pycrdt documents from instances of that schema using the `state` constructor parameter:

```python
from pycrdt_utils import MutantModel

# Define the initial state
initial_state = BlogPageConfig(
    collection="tech",
    posts=[
        Post(
            id="post1",
            title="First Post",
            content="This is the first post.",
            author=Author(id="author1", name="Author One"),
            comments=[],
        )
    ]
)

# Create a CRDT document with the initial state
doc = MutantModel[BlogPageConfig](state=initial_state)
```

Get a binary update blob from the CRDT, for example for sending over the wire to other peers:

```python
uri = "ws://example.com/websocket"
async with websockets.connect(uri) as websocket:
    await websocket.send(doc.update)
```

Instantiate documents from a binary update blob (or multiple using the `updates` parameter which accepts a list of update blobs):

```python
uri = "ws://example.com/websocket"
async with websockets.connect(uri) as websocket:
    doc = MutantModel[BlogPageConfig](update=websocket.recv())
```

Make granular edits with the `mutate` function (applied within a transaction):

```python
# Mutate the document
with doc.mutate() as state:
    state.posts[0].comments.append(Comment(
        id="comment1",
        author=Author(id="author2", name="Author Two"),
        content="Nice post!",
    ))
    state.posts[0].title = "First Post (Edited)"
```

There is also a JsonPathMutator class which can be used to make edits to the document using json path:

```python
# Mutate the document
from pycrdt_utils import JsonPathMutator
with doc.mutate() as state:
    mutator = JsonPathMutator(state=state)
    mutator.set("$.posts[0].title", "Updated First Post")
```