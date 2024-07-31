# 3rd party
import pytest
from pydantic import BaseModel, Field

# 1st party
from pymutantic.json_path import JsonPathMutator
from pymutantic.mutant import MutantModel


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
    comments: list[Comment] = Field(default_factory=list)


class BlogPageConfig(BaseModel):
    collection: str
    posts: list[Post] = Field(default_factory=list)


def test_json_path_set():
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
        ],
    )

    doc = MutantModel[BlogPageConfig](state=initial_state)
    with doc.mutate() as state:
        mutator = JsonPathMutator(state=state)
        mutator.set("$.posts[0].title", "Updated First Post")

    assert doc.state.posts[0].title == "Updated First Post"


def test_json_path_append():
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
        ],
    )

    doc = MutantModel[BlogPageConfig](state=initial_state)
    with doc.mutate() as state:
        mutator = JsonPathMutator(state=state)
        mutator.append(
            "$.posts[0].comments",
            Comment(
                id="comment1",
                author=Author(id="author2", name="Author Two"),
                content="Nice post!",
            ),
        )

    assert len(doc.state.posts[0].comments) == 1
    assert doc.state.posts[0].comments[0].content == "Nice post!"


def test_json_path_insert():
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
        ],
    )

    doc = MutantModel[BlogPageConfig](state=initial_state)
    with doc.mutate() as state:
        mutator = JsonPathMutator(state=state)
        mutator.insert(
            "$.posts[0].comments",
            0,
            Comment(
                id="comment0",
                author=Author(id="author3", name="Author Three"),
                content="First comment!",
            ),
        )

    assert len(doc.state.posts[0].comments) == 1
    assert doc.state.posts[0].comments[0].content == "First comment!"


def test_json_path_pop():
    initial_state = BlogPageConfig(
        collection="tech",
        posts=[
            Post(
                id="post1",
                title="First Post",
                content="This is the first post.",
                author=Author(id="author1", name="Author One"),
                comments=[
                    Comment(
                        id="comment1",
                        author=Author(id="author2", name="Author Two"),
                        content="Nice post!",
                    )
                ],
            )
        ],
    )

    doc = MutantModel[BlogPageConfig](state=initial_state)
    with doc.mutate() as state:
        mutator = JsonPathMutator(state=state)
        mutator.pop("$.posts[0].comments", 0)

    assert len(doc.state.posts[0].comments) == 0


def test_json_path_delete():
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
        ],
    )

    doc = MutantModel[BlogPageConfig](state=initial_state)
    with doc.mutate() as state:
        mutator = JsonPathMutator(state=state)
        mutator.delete("$.posts[0]")

    assert len(doc.state.posts) == 0


def test_multiple_json_path_edits():
    initial_state = BlogPageConfig.model_validate(
        {
            "collection": "tech",
            "posts": [
                {
                    "id": "post1",
                    "title": "First Post",
                    "content": "This is the first post.",
                    "author": {"id": "author1", "name": "Author One"},
                    "comments": [],
                }
            ],
        }
    )

    doc = MutantModel[BlogPageConfig](state=initial_state)
    with doc.mutate() as state:
        mutator = JsonPathMutator(state)
        mutator.set(
            "$.posts[0].comments",
            [
                {
                    "id": "comment1",
                    "author": {"id": "author2", "name": "Author Two"},
                    "content": "Nice post!",
                }
            ],
        )
        mutator.set("$.posts[0].title", "First Post (Edited)")

    assert len(doc.state.posts[0].comments) == 1
    assert doc.state.posts[0].comments[0].content == "Nice post!"
    assert doc.state.posts[0].title == "First Post (Edited)"


def test_invalid_json_path():
    initial_state = BlogPageConfig.model_validate(
        {
            "collection": "tech",
            "posts": [
                {
                    "id": "post1",
                    "title": "First Post",
                    "content": "This is the first post.",
                    "author": {"id": "author1", "name": "Author One"},
                    "comments": [],
                }
            ],
        }
    )

    doc = MutantModel[BlogPageConfig](state=initial_state)
    with pytest.raises(ValueError):
        with doc.mutate() as state:
            mutator = JsonPathMutator(state)
            mutator.set("$.invalid.path", "Invalid Edit")


def test_edit_nonexistent_field():
    initial_state = BlogPageConfig.model_validate(
        {
            "collection": "tech",
            "posts": [
                {
                    "id": "post1",
                    "title": "First Post",
                    "content": "This is the first post.",
                    "author": {"id": "author1", "name": "Author One"},
                    "comments": [],
                }
            ],
        }
    )

    doc = MutantModel[BlogPageConfig](state=initial_state)
    with pytest.raises(ValueError):
        with doc.mutate() as state:
            mutator = JsonPathMutator(state)
            mutator.set("$.posts[0].nonexistent", "Nonexistent Field Edit")


def test_multiple_edits_to_different_fields():
    initial_state = BlogPageConfig.model_validate(
        {
            "collection": "tech",
            "posts": [
                {
                    "id": "post1",
                    "title": "First Post",
                    "content": "This is the first post.",
                    "author": {"id": "author1", "name": "Author One"},
                    "comments": [],
                }
            ],
        }
    )

    doc = MutantModel[BlogPageConfig](state=initial_state)
    with doc.mutate() as state:
        mutator = JsonPathMutator(state)
        mutator.set("$.collection", "updated_collection")
        mutator.set("$.posts[0].content", "Updated content of the first post.")

    assert doc.state.collection == "updated_collection"
    assert doc.state.posts[0].content == "Updated content of the first post."


def test_merge_independent_edits():
    initial_state = BlogPageConfig.model_validate(
        {
            "collection": "tech",
            "posts": [
                {
                    "id": "post1",
                    "title": "First Post",
                    "content": "This is the first post.",
                    "author": {"id": "author1", "name": "Author One"},
                    "comments": [],
                }
            ],
        }
    )

    # Create the initial document
    doc1 = MutantModel[BlogPageConfig](state=initial_state)
    initial_update = doc1.update

    # First independent edit
    doc2 = MutantModel[BlogPageConfig](update=initial_update)
    with doc2.mutate() as state:
        mutator = JsonPathMutator(state)
        mutator.set(
            "$.posts[0].comments",
            [
                {
                    "id": "comment1",
                    "author": {"id": "author2", "name": "Author Two"},
                    "content": "Nice post!",
                }
            ],
        )

    # Second independent edit
    doc3 = MutantModel[BlogPageConfig](update=initial_update)
    with doc3.mutate() as state:
        mutator = JsonPathMutator(state)
        mutator.set("$.posts[0].title", "First Post (Edited)")

    # Merge the independent edits
    doc4 = MutantModel[BlogPageConfig](updates=(doc2.update, doc3.update))

    # Verify the merged state
    assert len(doc4.state.posts[0].comments) == 1
    assert doc4.state.posts[0].comments[0].content == "Nice post!"
    assert doc4.state.posts[0].title == "First Post (Edited)"


def test_edit_element_in_list():
    initial_state = BlogPageConfig.model_validate(
        {
            "collection": "tech",
            "posts": [
                {
                    "id": "post1",
                    "title": "First Post",
                    "content": "This is the first post.",
                    "author": {"id": "author1", "name": "Author One"},
                    "comments": [
                        {
                            "id": "comment1",
                            "author": {"id": "author2", "name": "Author Two"},
                            "content": "Nice post!",
                        }
                    ],
                }
            ],
        }
    )

    doc = MutantModel[BlogPageConfig](state=initial_state)
    with doc.mutate() as state:
        mutator = JsonPathMutator(state)
        mutator.set("$.posts[0].comments[0].content", "Edited comment content")

    assert len(doc.state.posts[0].comments) == 1
    assert doc.state.posts[0].comments[0].content == "Edited comment content"
    assert doc.state.posts[0].comments[0].author.name == "Author Two"


def test_edit_list_item_directly():
    initial_state = BlogPageConfig.model_validate(
        {
            "collection": "tech",
            "posts": [
                {
                    "id": "post1",
                    "title": "First Post",
                    "content": "This is the first post.",
                    "author": {"id": "author1", "name": "Author One"},
                    "comments": [
                        {
                            "id": "comment1",
                            "author": {"id": "author2", "name": "Author Two"},
                            "content": "Nice post!",
                        },
                        {
                            "id": "comment2",
                            "author": {"id": "author3", "name": "Author Three"},
                            "content": "Interesting perspective.",
                        },
                    ],
                }
            ],
        }
    )

    doc = MutantModel[BlogPageConfig](state=initial_state)
    with doc.mutate() as state:

        # Directly edit the second comment in the comments list
        mutator = JsonPathMutator(state)
        mutator.set(
            "$.posts[0].comments[1]",
            {
                "id": "comment2",
                "author": {"id": "author3", "name": "Author Three"},
                "content": "Updated comment content.",
            },
        )

    assert len(doc.state.posts[0].comments) == 2
    assert doc.state.posts[0].comments[1].content == "Updated comment content."
    assert doc.state.posts[0].comments[1].author.name == "Author Three"


if __name__ == "__main__":
    pytest.main([__file__])
