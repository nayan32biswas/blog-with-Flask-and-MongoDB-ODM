from datetime import datetime
from typing import Tuple

from faker import Faker

from app.post.models import Comment, EmbeddedReply, Post, Reaction, Topic
from app.user.models import User

from .conftest import get_header, get_user

fake = Faker()


def get_published_filter():
    return {"publish_at": {"$ne": None, "$lte": datetime.now()}}


def test_get_topics(client):
    response = client.get("/api/v1/topics")
    assert response.status_code == 200

    assert "results" in response.json

    response = client.get("/api/v1/topics?q=abc")
    assert response.status_code == 200


def test_create_topics(client):
    payload = {"name": fake.word()}

    response = client.post("/api/v1/topics", json=payload)
    assert response.status_code == 401

    response = client.post("/api/v1/topics", json=payload, headers=get_header(client))
    assert response.status_code == 201


def test_get_posts(client):
    response = client.get("/api/v1/posts")
    assert response.status_code == 200

    assert "results" in response.json

    # Get posts with valid credentials
    response = client.get("/api/v1/posts", headers=get_header(client))
    assert response.status_code == 200

    user = get_user()
    tag = Topic.get({})
    response = client.get(f"/api/v1/posts?p=abc&topics={tag.id}&author_id={user.id}")
    assert response.status_code == 200


def test_get_user_posts(client) -> None:
    user = get_user()
    response = client.get(f"/api/v1/posts?username={user.username}")
    assert response.status_code == 200

    assert "results" in response.json


def test_get_user_own_posts(client) -> None:
    user = get_user()
    response = client.get(
        f"/api/v1/posts?username={user.username}", headers=get_header(client)
    )
    assert response.status_code == 200

    assert "results" in response.json


def test_create_posts(client):
    payload = {
        "title": fake.sentence(),
        "publish_now": True,
        "short_description": None,
        "description": fake.text(),
        "cover_image": None,
        "topics": [],
    }

    response = client.post("/api/v1/posts", json=payload)
    assert response.status_code == 401

    response = client.post("/api/v1/posts", json=payload, headers=get_header(client))
    assert response.status_code == 201


def test_get_post_details(client):
    post = Post.get(get_published_filter())
    response = client.get(f"/api/v1/posts/{post.slug}")
    assert response.status_code == 200


def test_update_post(client):
    user = get_user()
    post = Post.get({"author_id": user.id})
    payload = {"title": fake.sentence(), "short_description": None, "cover_image": None}
    response = client.patch(f"/api/v1/posts/{post.slug}", json=payload)
    assert response.status_code == 401

    # Testing patch
    response = client.patch(
        f"/api/v1/posts/{post.slug}", json={"title": "new"}, headers=get_header(client)
    )
    assert response.status_code == 200
    assert Post.get({"_id": post.id}).title == "new"

    # Try to update others post
    post = Post.get({"author_id": {"$ne": user.id}})
    response = client.patch(
        f"/api/v1/posts/{post.slug}",
        json={"title": fake.sentence()},
        headers=get_header(client),
    )
    assert response.status_code == 403


def test_delete_post(client):
    user = get_user()
    post = Post.get({"author_id": user.id})
    response = client.delete(f"/api/v1/posts/{post.slug}", headers=get_header(client))
    assert response.status_code == 200

    # Try to delete others post
    post = Post.get({"author_id": {"$ne": user.id}})
    response = client.delete(f"/api/v1/posts/{post.slug}", headers=get_header(client))
    assert response.status_code == 403


def test_get_comments(client):
    post = Post.get({})

    response = client.get(f"/api/v1/posts/{post.slug}/comments")
    assert response.status_code == 200


def test_create_comment_on_any_post(client):
    user = get_user()
    post = Post.get_random_one({"author_id": user.id, **get_published_filter()})
    response = client.post(
        f"/api/v1/posts/{post.slug}/comments",
        json={"description": fake.text()},
        headers=get_header(client),
    )
    assert response.status_code == 201

    # Comment on others post valid action
    post = Post.get_random_one({"author_id": {"$ne": user.id}})
    response = client.post(
        f"/api/v1/posts/{post.slug}/comments",
        json={"description": fake.text()},
        headers=get_header(client),
    )
    assert response.status_code == 201


def test_update_comment(client):
    user = get_user()
    comment = Comment.get_random_one({"user_id": user.id})
    post = Post.get({"_id": comment.post_id})
    response = client.put(
        f"/api/v1/posts/{post.slug}/comments/{comment.id}",
        json={"description": fake.text()},
        headers=get_header(client),
    )
    assert response.status_code == 200

    # Try to update others comment should get 403
    comment = Comment.get_random_one({"user_id": {"$ne": user.id}})
    post = Post.get({"_id": comment.post_id})
    response = client.put(
        f"/api/v1/posts/{post.slug}/comments/{comment.id}",
        json={"description": fake.text()},
        headers=get_header(client),
    )
    assert response.status_code == 403


def test_delete_comment(client):
    user = get_user()
    comment = Comment.get_random_one({"user_id": user.id})
    post = Post.get({"_id": comment.post_id})
    response = client.delete(
        f"/api/v1/posts/{post.slug}/comments/{comment.id}",
        headers=get_header(client),
    )
    assert response.status_code == 200

    # Try to delete others comment should get 403
    comment = Comment.get_random_one({"user_id": {"$ne": user.id}})
    post = Post.get({"_id": comment.post_id})
    response = client.delete(
        f"/api/v1/posts/{post.slug}/comments/{comment.id}",
        headers=get_header(client),
    )
    assert response.status_code == 403


def test_create_replies(client):
    user = get_user()
    comment = Comment.get_random_one({"user_id": user.id})
    post = Post.get({"_id": comment.post_id})
    response = client.post(
        f"/api/v1/posts/{post.slug}/comments/{comment.id}/replies",
        json={"description": fake.text()},
        headers=get_header(client),
    )
    assert response.status_code == 201

    # Reply on others comment
    comment = Comment.get_random_one({"user_id": {"$ne": user.id}})
    post = Post.get({"_id": comment.post_id})
    response = client.post(
        f"/api/v1/posts/{post.slug}/comments/{comment.id}/replies",
        json={"description": fake.text()},
        headers=get_header(client),
    )
    assert response.status_code == 201


def get_my_reply(user: User) -> Tuple[Comment, EmbeddedReply]:
    comment = Comment.get({"replies.user_id": user.id})
    reply: EmbeddedReply
    for reply in comment.replies:
        if reply.user_id == user.id:
            reply = reply
            return comment, reply
    raise Exception("Reply not found")


def get_others_reply(user: User) -> Tuple[Comment, EmbeddedReply]:
    comment = Comment.get({"replies.user_id": {"$ne": user.id}})
    reply: EmbeddedReply
    for reply in comment.replies:
        if reply.user_id != user.id:
            reply = reply
            return comment, reply
    raise Exception("Reply not found")


def test_update_replies(client):
    user = get_user()
    comment, reply = get_my_reply(user)
    post = Post.get({"_id": comment.post_id})
    response = client.put(
        f"/api/v1/posts/{post.slug}/comments/{comment.id}/replies/{reply.id}",
        json={"description": fake.text()},
        headers=get_header(client),
    )
    assert response.status_code == 200

    # Try to update others replies. Should get 403
    comment, reply = get_others_reply(user)
    response = client.put(
        f"/api/v1/posts/{post.slug}/comments/{comment.id}/replies/{reply.id}",
        json={"description": fake.text()},
        headers=get_header(client),
    )
    assert response.status_code == 403


def test_delete_replies(client):
    user = get_user()
    comment, reply = get_my_reply(user)
    post = Post.get({"_id": comment.post_id})
    response = client.delete(
        f"/api/v1/posts/{post.slug}/comments/{comment.id}/replies/{reply.id}",
        headers=get_header(client),
    )
    assert response.status_code == 200

    # Try to delete others replies. Should get 403
    comment, reply = get_others_reply(user)
    response = client.delete(
        f"/api/v1/posts/{post.slug}/comments/{comment.id}/replies/{reply.id}",
        headers=get_header(client),
    )
    assert response.status_code == 403


def test_reactions(client):
    user = get_user()
    post = Post.get({})
    response = client.post(
        f"/api/v1/posts/{post.slug}/reactions", headers=get_header(client)
    )
    assert response.status_code == 201
    assert Reaction.exists({"post_id": post.id, "user_ids": {"$in": [user.id]}}) is True

    # Delete reaction
    response = client.delete(
        f"/api/v1/posts/{post.slug}/reactions", headers=get_header(client)
    )
    assert response.status_code == 200
    assert (
        Reaction.exists({"post_id": post.id, "user_ids": {"$in": [user.id]}}) is False
    )


def test_reactions_auth(client):
    post = Post.get({})
    response = client.post(f"/api/v1/posts/{post.slug}/reactions")
    assert response.status_code == 401

    response = client.delete(f"/api/v1/posts/{post.slug}/reactions")
    assert response.status_code == 401
