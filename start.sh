#!/bin/bash

source venv/bin/activate
uvicorn backend.src.main:app --reload --host 0.0.0.0 --port 8000
