# MUEEN AI V2 — مُعين

- CSV assessment upload and transparent skill mastery analysis.
- AI-generated learning support plans via OpenAI Responses API.
- CSV report and TXT plan downloads.

## Deploy
Upload `app.py` and `requirements.txt` to the root of the GitHub repository used by Streamlit.
In Streamlit Community Cloud: App → Settings → Secrets, add:

```toml
OPENAI_API_KEY = "your-real-api-key"
```

Never commit API keys to GitHub or share them in chat. ChatGPT subscription and API billing are separate.

Required CSV columns: `Student`, `Skill`, `Score`, `MaxScore`.

Use synthetic or anonymized data only. Teacher review is required.
