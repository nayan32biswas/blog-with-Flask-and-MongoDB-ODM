# Blog project in Flask and MongoDB-ODM

This is a **Blog** API project using <a href="https://mongodb-odm.readthedocs.io" class="external-link" target="_blank">MongoDB-ODM</a> in <a href="https://flask.palletsprojects.com" class="external-link" target="_blank">Flask</a>

## Start project

### First

Clone the repository and navigate to the project.

```bash
git clone https://github.com/nayan32biswas/blog-with-Flask-and-MongoDB-ODM.git
cd blog-with-Flask-and-MongoDB-ODM
```

### [Install Poetry](https://python-poetry.org/docs/#installation)

We are using poetry to manage our python package.

So we need to install poetry to start project.

### Install Dependency

Install all dependency.

```bash
poetry install
```

### Start Mongodb Server

#### [Install MongoDB](https://www.mongodb.com/docs/manual/installation/)

Install mongodb by following there official doc.

Start mongodb server.

### Export env key

```bash
export SECRET_KEY=your-secret-key
export MONGO_URL=<mongodb-connection-url>
export DEBUG=True
```

### Create Indexes

Before start backend server create indexes with:

```bash
poetry run python -m app.main create-indexes
```

### Run Server

Run backend server with `unicorn`.

```bash
poetry run flask --app app.app run --host 0.0.0.0 --port 8000 --reload
```

### Populate Database

## Run with Docker

Make sure you have docker installed and active.

- `docker-compose build api` Build docker image.
- `docker-compose run --rm api python -m app.main create-indexes` Create Indexes
- `docker-compose up api` Run the server.

### Populate Database with Docker

- `docker-compose run --rm api python -m app.main populate-data --total-user 1000 --total-post 1000` Populate database with 100 user and 100 post with others necessary information
- `docker-compose run --rm api python -m app.main delete-data` Clean database if necessary.

## Visit API Documentation

Use api testing tools like Postman to test and play with the APIs.

## Test

- Start Mongodb server
- Export env key
- `poetry run scripts/test.sh` run the test.

## Test with Docker

Run project unittest with single command:

```bash
docker-compose run --rm api ./scripts/test.sh
```

## Contribute

Developers are welcome to improve this project by contributing.

If you found some bug or if you can improve code we welcome you to make change.

It's better to create an issue first. Or create a discussions.

### Before create PR

Before creating PR make sure you follow those steps:

- Write test on your change.
- `poetry run scripts/test.sh` Run unittest and make sure everything pass.
- `poetry run scripts/lint.sh` Run linting script.
- `poetry run scripts/format.sh` Run format test if any formatting required.

## Load Test

### Create new Docker network

```bash
docker network create blog-database
```

### Run Mongodb service

`mkdir ~/mongo_blog_data` Create volume directory

```bash
docker run -d --name blog_db --hostname db \
    --network blog-database -p 27017:27017 --expose 27017 \
    -e MONGO_INITDB_ROOT_USERNAME=root -e MONGO_INITDB_ROOT_PASSWORD=password \
    -v ~/mongo_blog_data:/data/db \
    mongo:6
```

Additional command for the database container

The connection URL will be

- `mongodb://root:password@localhost:27017/blog_db?authSource=admin` for mongodb compass.
- `mongodb://root:password@db:27017/blog_db?authSource=admin` for application instance.

### Configure and Run Instance

Build the image:
`docker build -t nayanbiswas/flask_blog:loadtest -f Dockerfile.loadtest .`

Run the newly create image with proper tagging

```bash
docker run -d --name flask_blog_api \
    --network blog-database -p 8000:8000 --env-file .env \
    nayanbiswas/flask_blog:loadtest
```

#### Run application script

- `docker exec -it flask_blog_api python -m app.main populate-data` Populate data.
- `docker exec -it flask_blog_api ./scripts/test.sh` Run unit-test.

### Container related command

- `docker start <name>` stop the service if it's stopped.
- `docker stop <name>` Stop the service.
- `docker rm <name>` Remove the service.
