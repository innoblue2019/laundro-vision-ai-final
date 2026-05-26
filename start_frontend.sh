#!/bin/bash
exec uv run streamlit run src/laundro_vision_ai/ui/app.py \
  --server.port ${PORT:-8501} \
  --server.address 0.0.0.0 \
  --server.headless true
