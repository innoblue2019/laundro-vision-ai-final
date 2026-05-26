#!/bin/bash
exec uv run uvicorn laundro_vision_ai.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
