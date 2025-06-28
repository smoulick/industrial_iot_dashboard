#!/bin/bash
set -e

# Start data generation in the background
uv run python main_data_generator.py &

# Start Streamlit app
uv run streamlit run streamlit_app/app.py
