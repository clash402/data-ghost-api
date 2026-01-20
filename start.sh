#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Start the FastAPI app with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
