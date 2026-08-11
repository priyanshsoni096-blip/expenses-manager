# Smart Expense Tracker

A personal expense tracker built with Streamlit. Log expenses by typing or
speaking (English or Hindi), get auto-categorization, and see your spending
through a dashboard, history log, and analytics charts — all backed by
Firebase Firestore's free tier, so data persists across restarts and
redeploys.

## Features

- **Add expenses two ways**
  - **Type**: free-text entry like `"500 at McDonald's and 200 for shopping"` — parses multiple expenses from one sentence.
  - **Speak**: record via mic, auto-detects English or Hindi, transcribes, then parses.
- **Auto-categorization** from merchant/description keywords (Food & Dining, Groceries, Transport, Travel, Shopping, Entertainment, Bills & Utilities, Health & Fitness, Education, Other), with manual override before saving.
- **Hindi number parsing** — handles spoken amounts like "पांच सौ" (500) or "एक हज़ार दो सौ" (1200), not just Hindi merchant names.
- **Dashboard** — monthly budget tracking, spending-by-category and monthly-trend charts (with full-screen expand), recent expenses, quick actions, and computed insights (e.g. "You spent ₹X more on Y than last month").
- **History** — full expense log with search, filters (date range / category / payment mode), pagination, inline edit and delete.
- **Analytics** — filterable stats, category/time/payment-mode breakdowns, top merchants, CSV export.
- **Categories** — add/remove custom categories, per-category breakdown and insights.
- Dark, terminal-styled UI (JetBrains Mono throughout).

## Tech stack

| Piece | Choice |
|---|---|
| UI framework | [Streamlit](https://streamlit.io) |
| Database | [Firebase Firestore](https://firebase.google.com/docs/firestore) (free "Spark" tier) |
| Charts | [Plotly](https://plotly.com/python/) |
| Voice transcription | `SpeechRecognition` (Google's free Web Speech API, no key needed) + `streamlit-mic-recorder` |
| Data handling | `pandas` |

## Project structure

```
.
├── app.py                       # Main Streamlit app — all pages/UI
├── categorizer.py                # Free-text expense parsing + auto-categorization
├── hindi_numbers.py               # Devanagari number-word → numeric conversion
├── storage.py                     # Firestore reads/writes (expenses, categories, budget)
├── voice_input.py                 # Audio → text transcription (English/Hindi auto-detect)
├── json_to_secrets.py             # One-time helper: Firebase JSON key → secrets.toml
├── test_firestore_connection.py    # Standalone script to verify Firestore read/write works
├── requirements.txt
└── .streamlit/
    ├── config.toml               # Theme config
    └── secrets.toml              # Firebase service account (you create this — not committed)
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a Firebase project (free)

1. Go to the [Firebase Console](https://console.firebase.google.com) and create a project (any personal Google account, free Spark plan — no billing required).
2. Enable **Firestore Database** for that project (start in production or test mode — either is fine for a single-user app).
3. Go to **Project Settings → Service Accounts → Generate new private key**. This downloads a JSON key file.

### 3. Turn the key into `secrets.toml`

Run the included helper instead of copy-pasting the key by hand:

```bash
python3 json_to_secrets.py path/to/downloaded-key.json
```

This writes `.streamlit/secrets.toml` with owner-only file permissions and
never prints the private key to your terminal. It refuses to run if
`secrets.toml` already exists, so if you're rotating a key, delete the old
file first.

If deploying to **Streamlit Community Cloud** instead of running locally,
paste the same `[firebase_service_account]` block into the app's **Secrets**
panel in the dashboard rather than committing a `secrets.toml` file.

### 4. (Optional) Verify the connection

```bash
python3 test_firestore_connection.py
```

This writes a test document, reads it back, then deletes it — confirming
your credentials and Firestore setup actually work before you rely on them
inside the app.

### 5. Run the app

```bash
streamlit run app.py
```

## Notes

- `requirements.txt` pins exact versions deliberately — `app.py` styles
  Streamlit's internal DOM via `data-testid` / `st-key-*` selectors, which
  shift between Streamlit releases. If you bump a version on purpose,
  re-check the sidebar nav and expense table layout afterward.
- Voice transcription uses Google's free, unofficial Web Speech endpoint via
  `SpeechRecognition` — it's rate-limited, so occasional transient failures
  are expected and surfaced as a retry prompt rather than a crash.
- Never commit `.streamlit/secrets.toml` or the downloaded Firebase JSON key
  to version control.
