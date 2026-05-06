# Q — Virtual Dining Assistant for ICB

A Streamlit chat app powered by Claude (Anthropic) that simulates the Q dining assistant for ICB's menu.

## Quick Start (local)

```bash
cd q-assistant-icb
pip3 install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501 in your browser. Enter your Anthropic API key in the sidebar.

---

## Share with colleagues (free, 5 minutes)

### Option A — Streamlit Cloud (recommended, permanent URL)

1. Push this folder to a GitHub repo:
   ```bash
   git init
   git add .
   git commit -m "Q assistant for ICB"
   gh repo create q-assistant-icb --public --source=. --push
   ```

2. Go to **https://share.streamlit.io** → "New app"
   - Repo: `your-username/q-assistant-icb`
   - Branch: `main`
   - Main file: `app.py`

3. Add your API key as a secret:
   - App settings → Secrets → add:
     ```
     ANTHROPIC_API_KEY = "sk-ant-..."
     ```

4. Deploy → share the URL with your team. They don't need an API key.

### Option B — ngrok (quick, local tunnel)

```bash
# In terminal 1: run the app
streamlit run app.py

# In terminal 2: expose publicly
brew install ngrok
ngrok http 8501
```

Share the ngrok URL — it's active as long as both terminals are running.

---

## Add popularity scores

Upload an Excel/CSV file via the sidebar with columns:
- `item_id` — the item ID from the menu JSON
- `score` — popularity/order count

The assistant will use these to surface the most popular dishes in recommendations.

---

## Files

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit chat app |
| `menu_loader.py` | Parses menu JSON + popularity scores |
| `system_prompt.py` | Builds the Q system prompt |
| `menu.json` | ICB menu (source of truth) |
| `requirements.txt` | Python dependencies |
