# MUEEN AI V1 — مُعين

A browser-deployable educational prototype built with Streamlit.

## Features
- Upload CSV assessment results.
- Analyze mastery by skill using transparent calculations.
- Suggest rule-based learning support activities.
- Compare before/after mastery values.
- Download a skill summary report.

## Required CSV columns
`Student`, `Skill`, `Score`, `MaxScore`

Example:
```csv
Student,Skill,Score,MaxScore
Student 1,Algorithm concepts,4,5
Student 1,Sequencing steps,2,5
```

## Run locally (optional)
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy
Push `app.py` and `requirements.txt` to a GitHub repository, then create a Streamlit Community Cloud app pointing to `app.py`.

## Important
This is an early prototype, not yet an autonomous LLM agent. It uses transparent rule-based analysis. Use synthetic or anonymized data only, and have educators review all recommendations.
