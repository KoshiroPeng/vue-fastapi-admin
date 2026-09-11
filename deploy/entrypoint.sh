#!/bin/sh
set -e

nginx
exec python run.py
