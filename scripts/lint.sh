#!/usr/bin/env bash

set -e
set -x

mypy app
ruff app scripts
ruff format app --check
