#!/usr/bin/env bash

set -e
set -x

mypy app
flake8 app tests
black app tests --check
isort app tests scripts --check-only
