import logging
import multiprocessing
import random
from datetime import datetime
from typing import Dict

from faker import Faker
from mongodb_odm import InsertOne, apply_indexes
from mongodb_odm.connection import db
from werkzeug.security import generate_password_hash

from app.base.utils.decorator import timing
from app.post.models import Comment, EmbeddedReply, Post, Reaction, Tag
from app.user.models import User

fake = Faker()
log = logging.getLogger(__name__)

users = [
    {"username": "username_1", "full_name": fake.name(), "password": "password-one"},
    {"username": "username_2", "full_name": fake.name(), "password": "password-two"},
]


def get_hash_password(_):
    return generate_password_hash(fake.password())


@timing
def create_users(N: int) -> None:
    write_users = [
        InsertOne(
            User.to_mongo(
                User(
                    username=user["username"],
                    full_name=user["full_name"],
                    password=generate_password_hash(user["password"]),
                    random_str=User.new_random_str(),
                    joining_date=datetime.utcnow(),
                )
            )
        )
        for user in users
    ]

    pool = multiprocessing.Pool(processes=8)
    hash_passwords = pool.map(get_hash_password, range(N))
    pool.close()
    pool.join()

    for i in range(max(N - 2, 0)):
        write_users.append(
            InsertOne(
                User.to_mongo(
                    User(
                        username=f"{i+11}_username",
                        full_name=fake.name(),
                        password=hash_passwords[i],
                        random_str=User.new_random_str(),
                        joining_date=datetime.utcnow(),
                    )
                )
            )
        )
    User.bulk_write(requests=write_users)
    log.info(f"{N} user created")


def create_tags(N: int) -> None:
    data_set = {fake.word() for _ in range(N)}

    write_tags = [InsertOne(Tag.to_mongo(Tag(name=value))) for value in data_set]
    Tag.bulk_write(requests=write_tags)
    log.info(f"{len(data_set)} tag created")


def get_post() -> Dict:
    return {
        "title": fake.sentence(),
        "publish_at": datetime.utcnow(),
        "short_description": None,
        "description": fake.text(),
        "cover_image": None,
    }


@timing
def create_posts(N: int) -> None:
    user_ids = [user["_id"] for user in User.find_raw(projection={"_id": 1})]
    tag_ids = [tag["_id"] for tag in Tag.find_raw(projection={"_id": 1})]

    write_posts = []
    for _ in range(N):
        write_posts.append(
            InsertOne(
                Post.to_mongo(
                    Post(
                        **get_post(),
                        author_id=random.sample(user_ids, 1)[0],
                        tag_ids=random.sample(tag_ids, random.randint(1, 3))[::],
                    )
                )
            )
        )
    Post.bulk_write(requests=write_posts)

    log.info(f"{N} post inserted")


@timing
def create_reactions() -> None:
    user_ids = [user["_id"] for user in User.find_raw(projection={"_id": 1})]
    post_ids = [post["_id"] for post in Post.find_raw(projection={"_id": 1})]

    write_reactions = []
    total_post = len(post_ids)
    total_post_reaction = min(total_post, total_post // 3)

    for post_id in random.sample(post_ids, total_post_reaction):
        write_reactions.append(
            InsertOne(
                Reaction.to_mongo(
                    Reaction(
                        post_id=post_id,
                        user_ids=random.sample(
                            user_ids, random.randint(1, min(len(user_ids), 99))
                        ),
                    )
                )
            )
        )
    Reaction.bulk_write(requests=write_reactions)

    log.info(f"{len(write_reactions)} reaction inserted")


@timing
def create_comments() -> None:
    user_ids = [user["_id"] for user in User.find_raw(projection={"_id": 1})]
    post_ids = [post["_id"] for post in Post.find_raw(projection={"_id": 1})]

    write_comments = []
    total_post = len(post_ids)
    total_post_comment = min(total_post, total_post // 3)

    for post_id in random.sample(post_ids, total_post_comment):
        for _ in range(random.randint(1, 100)):
            replies = [
                EmbeddedReply(
                    user_id=random.sample(user_ids, 1)[0], description=fake.text()
                )
                for _ in range(random.randint(1, 20))
            ]
            write_comments.append(
                InsertOne(
                    Comment.to_mongo(
                        Comment(
                            user_id=random.sample(user_ids, 1)[0],
                            post_id=post_id,
                            description=fake.text(),
                            replies=replies,
                        )
                    )
                )
            )
    Comment.bulk_write(requests=write_comments)
    log.info(f"{len(write_comments)} comment inserted")


@timing
def populate_dummy_data(total_user: int = 10, total_post: int = 10) -> None:
    apply_indexes()

    log.info("Inserting data...")
    create_users(total_user)
    create_tags(min(max(total_post // 10, 10), 1000))
    create_posts(total_post)
    create_reactions()
    create_comments()
    log.info("Data insertion complete")


def clean_data() -> None:
    db().command("dropDatabase")
