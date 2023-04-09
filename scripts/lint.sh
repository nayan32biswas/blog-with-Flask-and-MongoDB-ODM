#!/usr/bin/env bash

set -e
set -x

# mypy app
flake8 app
black app --check
isort app scripts --check-only
