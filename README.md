# Assignment 2 — Automatic Faculty–Student Allocation System


## Overview
This Streamlit app implements the allocation algorithm described by your instructor: sort students by CGPA and allocate using modular indexing across preference columns.


## Run locally (without Docker)
1. python -m venv venv
2. source venv/bin/activate # Windows: venv\Scripts\activate
3. streamlit run app.py


## Run with Docker
1. docker build -t allocation-app .
2. docker run -p 8501:8501 allocation-app


Or use docker-compose:
1. docker compose up --build


## Inputs & outputs
- Input CSV: must contain a `CGPA` column and one or more preference columns after it.
- Outputs provided by the UI: `output_btp_mtp_allocation.csv` and `fac_preference_count.csv` (downloadable from the Streamlit UI).




