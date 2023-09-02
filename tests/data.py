import logging
import multiprocessing
import random
import string
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Tuple
from uuid import uuid4

from bson import ObjectId
from faker import Faker
from mongodb_odm import InsertOne, apply_indexes
from mongodb_odm.connection import db
from slugify import slugify

from app.base.utils.decorator import timing
from app.post.models import Comment, EmbeddedReply, Post, Reaction, Topic
from app.user.auth import Auth
from app.user.models import User

fake = Faker()
log = logging.getLogger(__name__)

PROCESSORS = max(multiprocessing.cpu_count() - 2, 2)

users = [
    {"username": "username_1", "full_name": fake.name(), "password": "password-one"},
    {"username": "username_2", "full_name": fake.name(), "password": "password-two"},
]


def rand_str(N: int = 12) -> str:
    return "".join(
        random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits)
        for _ in range(N)
    )


def get_range(N: int) -> List[int]:
    block_size = N // PROCESSORS
    val = [block_size for _ in range(PROCESSORS)]

    for i in range(N % PROCESSORS):
        val[i] += 1

    return val


def get_random_range(total: int, min_item: int, max_item: int) -> Tuple[int, int]:
    total -= 1
    lo = random.randint(0, total)
    hi = min(lo + random.randint(min_item, max_item), total)
    return lo, hi


def get_hash_password(_: Any) -> str:
    return Auth.get_password_hash(fake.password())


@lru_cache
def get_user_ids() -> List[Any]:
    return [user["_id"] for user in User.find_raw(projection={"_id": 1})]


@lru_cache
def get_topic_ids() -> List[Any]:
    return [topic["_id"] for topic in Topic.find_raw(projection={"_id": 1})]


@lru_cache
def get_post_ids() -> List[Any]:
    return [post["_id"] for post in Post.find_raw(projection={"_id": 1})]


def _create_users(total_user: Any) -> bool:
    hash_passwords = []
    for _ in range(10):
        hash_passwords.append(get_hash_password(0))

    write_users = []
    for i in range(total_user):
        write_users.append(
            InsertOne(
                User.to_mongo(
                    User(
                        username=f"i{uuid4()}",
                        full_name=fake.name(),
                        password=hash_passwords[i % len(hash_passwords)],
                        random_str=User.new_random_str(),
                        joining_date=datetime.utcnow(),
                    )
                )
            )
        )
    if write_users:
        User.bulk_write(requests=write_users)
    return True


@timing
def create_users(N: int) -> None:
    for user in users:
        if User.exists({"username": user["username"]}) is False:
            User(
                username=user["username"],
                full_name=user["full_name"],
                password=Auth.get_password_hash(user["password"]),
                random_str=User.new_random_str(),
                joining_date=datetime.utcnow(),
            ).create()
    N -= 2

    numbers = get_range(N)
    with multiprocessing.Pool(processes=PROCESSORS) as pool:
        _ = pool.map(_create_users, numbers)

    log.info(f"{N} user created")


def create_topics(N: int) -> None:
    data_set = {" ".join(fake.words(random.randint(1, 3))) for _ in range(N)}
    if Topic.exists() is True:
        log.info("Topic already exists")
        return

    write_topics = [
        InsertOne(Topic.to_mongo(Topic(name=value)))
        for idx, value in enumerate(data_set)
    ]
    if write_topics:
        Topic.bulk_write(requests=write_topics)
    log.info(f"{len(data_set)} topic created")


def get_post() -> Dict[str, Any]:
    title = fake.sentence()
    description = fake.text(random.randint(1000, 10000))
    return {
        "title": title,
        "publish_at": datetime.utcnow(),
        "short_description": description[:200],
        "description": description,
        "cover_image": None,
    }


def _create_posts(total_post: Any) -> bool:
    user_ids = get_user_ids()
    topic_ids = [topic["_id"] for topic in Topic.find_raw(projection={"_id": 1})]

    random.shuffle(user_ids)
    random.shuffle(topic_ids)
    total_user, total_topic = len(user_ids), len(topic_ids)

    write_posts = []
    for i in range(total_post):
        topic_lo, topic_hi = get_random_range(total_topic, 5, 10)
        post_data = get_post()
        write_posts.append(
            InsertOne(
                Post.to_mongo(
                    Post(
                        **post_data,
                        slug=f"{slugify(post_data['title'])}-{ObjectId()}",
                        author_id=user_ids[i % total_user],
                        topic_ids=topic_ids[topic_lo:topic_hi],
                    )
                )
            )
        )
    if write_posts:
        Post.bulk_write(requests=write_posts)
    return True


@timing
def create_posts(N: int) -> None:
    numbers = get_range(N)
    with multiprocessing.Pool(processes=PROCESSORS) as pool:
        _ = pool.map(_create_posts, numbers)

    log.info(f"{N} post inserted")


def _create_reactions(total_reaction: Any) -> None:
    user_ids = get_user_ids()
    post_ids = get_post_ids()

    total_post, total_user = len(post_ids), len(user_ids)
    random.shuffle(post_ids)
    random.shuffle(user_ids)

    write_reactions = []
    for i in range(total_reaction):
        lo, hi = get_random_range(total_user, 20, 100)
        write_reactions.append(
            InsertOne(
                Reaction.to_mongo(
                    Reaction(
                        post_id=post_ids[i % total_post],
                        user_ids=user_ids[lo:hi],
                    )
                )
            )
        )
    if write_reactions:
        Reaction.bulk_write(requests=write_reactions)


@timing
def create_reactions() -> None:
    N = Post.count_documents()

    numbers = get_range(N)
    with multiprocessing.Pool(processes=PROCESSORS) as pool:
        _ = pool.map(_create_reactions, numbers)

    log.info(f"{N} reaction inserted")


def _create_comments(total_comment: Any) -> None:
    user_ids = get_user_ids()
    post_ids = get_post_ids()

    total_post, total_user = len(post_ids), len(user_ids)
    random.shuffle(post_ids)
    random.shuffle(user_ids)

    write_comments = []
    for i in range(total_comment):
        post_id = post_ids[i % total_post]
        total_comment = random.randint(1, random.randint(1, random.randint(1, 100)))
        for j in range(total_comment):
            replies = [
                EmbeddedReply(
                    user_id=user_ids[(i + k) % total_user], description=fake.text()
                )
                for k in range(random.randint(1, random.randint(1, 20)))
            ]
            write_comments.append(
                InsertOne(
                    Comment.to_mongo(
                        Comment(
                            user_id=user_ids[(i + j) % total_user],
                            post_id=post_id,
                            description=fake.text(),
                            replies=replies,
                        )
                    )
                )
            )
    if write_comments:
        Comment.bulk_write(requests=write_comments)


@timing
def create_comments() -> None:
    total_post = Post.count_documents()
    N = total_post // 3

    numbers = get_range(N)
    for num in numbers:
        with multiprocessing.Pool(processes=PROCESSORS) as pool:
            _ = pool.map(_create_comments, get_range(num))

    log.info(f"{N} comment inserted")


@timing
def populate_dummy_data(total_user: int = 100, total_post: int = 100) -> None:
    apply_indexes()

    log.info("Inserting data...")
    create_users(total_user)
    create_topics(min(max(total_post // 10, 10), 100000))
    create_posts(total_post)
    create_reactions()
    create_comments()
    log.info("Data insertion complete")


def clean_data() -> None:
    db().command("dropDatabase")
    log.info("Database deleted")
