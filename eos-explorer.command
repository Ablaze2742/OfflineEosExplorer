#!/bin/bash
source .venv/bin/activate
python3 scripts/app.py &> debug.log
