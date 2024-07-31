import pytest

from pydantic import Field, BaseModel

from pymutantic import MutantModel


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


def test_empty_initial_state():
    empty_state = BlogPageConfig.model_validate({"collection": "empty", "posts": []})
    doc = MutantModel[BlogPageConfig](state=empty_state)
    assert doc.state.collection == "empty"
    assert len(doc.state.posts) == 0


def test_initial_state():
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
    assert doc.state.collection == "tech"
    assert len(doc.state.posts) == 1
    assert doc.state.posts[0].title == "First Post"


def test_single_post_initial_state():
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
    assert doc.state.collection == "tech"
    assert len(doc.state.posts) == 1
    assert doc.state.posts[0].title == "First Post"
    assert doc.state.posts[0].author.name == "Author One"


def test_add_post():
    initial_state = BlogPageConfig.model_validate({"collection": "tech", "posts": []})
    doc = MutantModel[BlogPageConfig](state=initial_state)
    with doc.mutate() as state:
        state.posts.append(
            Post(
                id="post1",
                title="New Post",
                content="This is a new post.",
                author=Author(id="author1", name="Author One"),
                comments=[],
            )
        )
    assert len(doc.state.posts) == 1
    assert doc.state.posts[0].title == "New Post"
    assert doc.state.posts[0].author.name == "Author One"


def test_add_comment():
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
        state.posts[0].comments.append(
            Comment(
                id="comment1",
                author=Author(id="author2", name="Author Two"),
                content="Nice post!",
            )
        )
    assert len(doc.state.posts[0].comments) == 1
    assert doc.state.posts[0].comments[0].content == "Nice post!"
    assert doc.state.posts[0].comments[0].author.name == "Author Two"


def test_update_title():
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
        state.posts[0].title = "Updated First Post"
    assert doc.state.posts[0].title == "Updated First Post"


def test_mutual_exclusivity_check():
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
    update = MutantModel[BlogPageConfig](state=initial_state).update
    with pytest.raises(ValueError):
        MutantModel[BlogPageConfig](state=initial_state, update=update)
    with pytest.raises(ValueError):
        MutantModel[BlogPageConfig](updates=(update,), state=initial_state)


def test_update_state():
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

    doc1 = MutantModel[BlogPageConfig](state=initial_state)
    update = doc1.update

    doc2 = MutantModel[BlogPageConfig](update=update)
    with doc2.mutate() as state:
        state.posts[0].comments.append(
            Comment(
                id="comment1",
                author=Author(id="author2", name="Author Two"),
                content="Nice post!",
            )
        )
        state.posts[0].title = "First Post (Edited)"

    assert doc2.state.posts[0].title == "First Post (Edited)"
    assert len(doc2.state.posts[0].comments) == 1
    assert doc2.state.posts[0].comments[0].content == "Nice post!"


def test_merge_updates():
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

    doc1 = MutantModel[BlogPageConfig](state=initial_state)
    update1 = doc1.update

    # First independent edit
    doc2 = MutantModel[BlogPageConfig](update=update1)
    with doc2.mutate() as state:
        state.posts[0].comments.append(
            Comment(
                id="comment1",
                author=Author(id="author2", name="Author Two"),
                content="Nice post!",
            )
        )

    # Second independent edit
    doc3 = MutantModel[BlogPageConfig](update=update1)
    with doc3.mutate() as state:
        state.posts.append(
            Post(
                id="post2",
                title="Second Post",
                content="This is the second post.",
                author=Author(id="author1", name="Author One"),
                comments=[],
            )
        )

    # Merge edits
    doc4 = MutantModel[BlogPageConfig](updates=(doc2.update, doc3.update))

    assert len(doc4.state.posts) == 2
    assert len(doc4.state.posts[0].comments) == 1
    assert doc4.state.posts[0].comments[0].content == "Nice post!"
    assert doc4.state.posts[1].title == "Second Post"


def test_array_append():
    initial_state = BlogPageConfig.model_validate({"collection": "tech", "posts": []})

    doc = MutantModel[BlogPageConfig](state=initial_state)
    with doc.mutate() as state:
        state.posts.append(
            Post(
                id="post1",
                title="First Post",
                content="This is the first post.",
                author=Author(id="author1", name="Author One"),
                comments=[],
            )
        )

    assert len(doc.state.posts) == 1
    assert doc.state.posts[0].title == "First Post"


def test_array_setitem():
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
        state.posts[0] = Post(
            id="post1",
            title="Updated Post",
            content="This is the updated post.",
            author=Author(id="author1", name="Author One"),
            comments=[],
        )

    assert doc.state.posts[0].title == "Updated Post"


def test_array_extend():
    initial_state = BlogPageConfig.model_validate({"collection": "tech", "posts": []})

    doc = MutantModel[BlogPageConfig](state=initial_state)
    with doc.mutate() as state:
        state.posts.extend(
            [
                Post(
                    id="post1",
                    title="First Post",
                    content="This is the first post.",
                    author=Author(id="author1", name="Author One"),
                    comments=[],
                ),
                Post(
                    id="post2",
                    title="Second Post",
                    content="This is the second post.",
                    author=Author(id="author2", name="Author Two"),
                    comments=[],
                ),
            ]
        )

    assert len(doc.state.posts) == 2
    assert doc.state.posts[1].title == "Second Post"


def test_array_clear():
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
        state.posts.clear()

    assert len(doc.state.posts) == 0


def test_array_insert():
    initial_state = BlogPageConfig.model_validate({"collection": "tech", "posts": []})

    doc = MutantModel[BlogPageConfig](state=initial_state)
    with doc.mutate() as state:
        state.posts.insert(
            0,
            Post(
                id="post1",
                title="First Post",
                content="This is the first post.",
                author=Author(id="author1", name="Author One"),
                comments=[],
            ),
        )

    assert len(doc.state.posts) == 1
    assert doc.state.posts[0].title == "First Post"


def test_array_pop():
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
        state.posts.pop()

    assert len(doc.state.posts) == 0


def test_array_delitem():
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
        del state.posts[0]

    assert len(doc.state.posts) == 0


if __name__ == "__main__":
    pytest.main([__file__])
