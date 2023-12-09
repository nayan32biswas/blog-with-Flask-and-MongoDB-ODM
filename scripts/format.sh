#!/usr/bin/env bash

set -x

ruff app scripts --fix
ruff format app scripts
