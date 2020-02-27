#!/usr/bin/env bash

uvicorn api.server:app --host 0.0.0.0 --port 2433
