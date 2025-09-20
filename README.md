# Django template

[![License: MIT](https://img.shields.io/github/license/vintasoftware/django-react-boilerplate.svg)](LICENSE)

## About

A [Django](https://www.djangoproject.com/) project template with a multitude of state-of-the-art libraries and tools:

-   [ruff](https://github.com/astral-sh/ruff) with [pre-commit](https://pre-commit.com/) for automated quality assurance

-   [uv](https://github.com/astral-sh/uv) for fast Python dependency management and environment isolation

-   [Celery](https://docs.celeryq.dev/en/stable/), for background worker tasks

For continuous integration, a [Github Action](https://github.com/features/actions) configuration `.github/workflows/main.yml` is included.

-   PostgreSQL, for DB
-   Redis, for Celery

## Features Catalogue

### Backend

-   `celery` for background worker tasks
-   `django` for building backend logic using Python
-   `djangorestframework` for building a REST API on top of Django
-   `django-csp` for setting the draft security HTTP header Content-Security-Policy
-   `django-permissions-policy` for setting the draft security HTTP header Permissions-Policy
-   `django-celery-results` for storing Celery task results in the Django database
-   `django-celery-beat` for managing periodic Celery tasks and schedules in the database
-   `django-defender` for blocking brute force attacks against login
-   `psycopg2-binary` for using PostgreSQL database
-   `redis` for message brokering and caching (used by Celery and Django)
-   `python-dotenv` for loading environment variables from `.env` files
-   `pre-commit` for managing Git hooks for code formatting, linting, and automated checks

## Project bootstrap [![main](https://github.com/preobart/template/actions/workflows/main.yml/badge.svg)](https://github.com/preobart/template/actions/workflows/main.yml) 

-   [ ] Make sure you have Python 3.13 installed
-   [ ] Install Django with `pip install django`, to have the `django-admin` command available
-   [ ] Open the command line and go to the directory you want to start your project in
-   [ ] Start your project using (replace `project_name` with your project name and remove the curly braces):
    ```
    django-admin startproject brvjeoCloud . --extension py,json,yaml,toml,lock --name Dockerfile,README.md,.env.example,.gitignore,Makefile,LICENSE,.env,main.yml,docker-compose.yml --template=https://github.com/preobart/mono-template/archive/refs/heads/master.zip
    ```
In the next steps, always remember to replace brvjeoCloud with your project's name (in case it isn't yet):
-   [ ] Above: don't forget the `--extension` and `--name` params!
-   [ ] Go into project's root directory: `cd brvjeoCloud`
-   [ ] Change the first line of README to the name of the project

After completing ALL of the above, clear the README. Then follow `Running` below.

## Running

### If you are using Docker, you can:

-   Create the migrations for app:
    `make makemigrations`
-   Run the migrations:
    `make migrate`
-   Run the project:
    `make up`
-   To access the logs for each service, run:
    `make logs <service name>` (either `app`, `db`, etc)
-   To stop the project, run:
    `make down`
-   Run the tests:
    `make test someapp.tests.test_views`

#### Adding new dependencies

-   Open a new command line window and go to the project's directory
-   Update the dependencies management files by performing any number of the following steps:
-   To add a new dependency, run `docker compose run --rm app bash` to open an interactive shell and then run `uv add {dependency}` to add the dependency. 
-   After updating the desired file(s), run `make update_dependencies` to update the containers with the new dependencies
    > The above command will stop and re-build the containers in order to make the new dependencies effective

### Pre-commit hooks

-   On project root, run `pre-commit install` to enable the hook into your git repo. The hook will run automatically for each commit.

### Github Actions

-   To enable **GitHub Actions**, you need to make sure the folder is named `.github` instead of `github`.  
    ```bash
    mv github .github