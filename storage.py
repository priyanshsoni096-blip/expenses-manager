
Claude finished the response
the edit prifile thign is gone can u jsut add that]


Ran a command
Ran a command
Right — this is the old pre-deploy file, which uses a hardcoded USER_NAME = "Priyansh" and has no name-editing feature. That's why "Edit" is gone — this version never had it. Let me add the editable-name feature back (the profile name saved to Firestore + the Edit button), same as we built earlier.

First let me check storage.py has the name functions — I need to confirm whether the deployed storage.py has them:


Ran a command
Ran a command
My storage.py in the workdir has the name functions, but I need to confirm what's actually deployed. The safest approach: make the profile name feature work without requiring storage.py changes, OR include the updated storage.py too.

Let me ask myself — does the deployed repo have the name functions in storage.py? Unknown. To be safe, I'll add the feature to app.py AND give you the matching storage.py, so both go together. Let me add the editable name to the working app.py:


View the profile block and CSS in the working file
View the profile block and CSS in the working file
Now let me add the CSS for the edit button and replace the static profile block with the editable version. First, add the edit-button CSS right before </style>:

Claude’s response was interrupted.

storage.py
239 lines

py

ill giv eu storage oy

Thanks — this confirms your deployed storage.py does not have the name functions (get_user_name/set_user_name). So to add the editable profile name, I need to update both files. Let me do both.

First, add the name functions to storage.py:


Ran a command, edited a file
Ran a command, edited a file
Now app.py. First add the CSS for the edit button (before </style> in the profile block):


Editing file
Editing file
Now update the greeting that still uses USER_NAME:


Editing file
Editing file
Now USER_NAME is only defined but unused (line 28). Leave it defined to avoid breaking anything else that might reference it — let me check nothing else uses it:


Ran a command
Ran a command
Line 28 is now unused (line 33 is a comment, 740 is my new comment). Harmless to leave, but let me remove the dead constant for cleanliness:


Viewed a file, edited a file
Viewed a file, edited a file
Claude’s response was interrupted.
can u add a popup when it starts it asks for ur name uses it and then u can edit it ayer for, hhat thingy that we had put


Ran a command
Ran a command
Good — Streamlit 1.41.1 supports st.dialog (a real modal popup). Let me replace the sidebar-inline name editing with a proper popup dialog on first launch, plus keep the "Edit" button in the sidebar to reopen it later.

Let me view the current profile block I just added:


View the current profile block with inline editing
View the current profile block with inline editing
Now let me replace the inline-editing logic with a st.dialog popup. The dialog function needs to be defined at module level (decorated with @st.dialog), then called when the name-edit flag is set:


Editing file
Editing file
Now define the name_dialog() function at module level. Let me put it right after _initials (near the top, before it's used). Let me find a good spot:


Viewed a file, edited a file
Viewed a file, edited a file
Now the sidebar CSS still references the inline edit approach — but the profile_edit_trigger button CSS is still valid (the Edit link stays). Let me remove the now-unused inline-edit references. Actually, the editing_profile_name state key is no longer used. That's harmless. Let me compile-check:


Ran 2 commands
Ran 2 commands
Clean — no stale editing_profile_name references, dialog properly wired. Now let me verify the name_dialog() call is placed at the right indentation level (it needs to be inside the sidebar with block or at module level after it). Let me check:


Check indentation of name_dialog call relative to sidebar block
Check indentation of name_dialog call relative to sidebar block
The name_dialog() call at line 803 is indented 4 spaces — inside the with st.sidebar: block (which is good; the dialog still renders as a centered modal regardless). Let me confirm it's within the sidebar with block by checking the indentation context:


Ran a command
Ran a command
Good — it's inside with st.sidebar: (line 634), which is fine since st.dialog renders a centered modal over the whole app regardless of where it's called from. Now normalize both files and ship:


Ran a command, read a file
Ran a command, read a file
Added the popup. Here's how it works now — both files need to go up together (app.py + storage.py):

On first launch (no name saved yet), a centered popup appears: "👋 Welcome — What should we call you?" with a text box and Save/Cancel. Whatever they enter is saved to Firestore and shown on the dashboard greeting + sidebar.

Later, the "✏️ Edit" link in the sidebar profile card reopens the same popup so they can change it anytime.

The name persists in Firestore (via the get_user_name/set_user_name functions I added to storage.py), so it's remembered across restarts, and since it's per-database, you and sachi each get your own name on your own setups.

Two things to note:

Push both app.py and storage.py — the popup calls the new storage functions, so deploying only one will error.
This uses st.dialog, which needs Streamlit ≥ 1.37 — you're on 1.41.1, so you're fine.

App
PY 

Storage
PY 





Claude is AI and can make mistakes. Please double-check responses.
Storage · PY
"""
storage.py
Persists expenses to Firebase Firestore (free "Spark" tier — no billing
required). Data is instant and persistent across Streamlit Cloud
restarts/redeploys, since it lives outside the app's filesystem.

Setup required (one-time, done outside this code):
    1. Create a project at https://console.firebase.google.com (any
       personal Google account, free Spark plan).
    2. Enable "Firestore Database" for that project (start in
       production or test mode, either works for a single-user app).
    3. Project Settings -> Service Accounts -> Generate new private key.
       This downloads a JSON file.
    4. Put its contents into .streamlit/secrets.toml (local) or the
       Streamlit Cloud "Secrets" panel (deployed), under the key
       [firebase_service_account], e.g.:

        [firebase_service_account]
        type = "service_account"
        project_id = "..."
        private_key_id = "..."
        private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
        client_email = "...@....iam.gserviceaccount.com"
        client_id = "..."
        token_uri = "https://oauth2.googleapis.com/token"

Exposes the same interface as the previous SQLite version, so app.py
doesn't need to change:
    load_expenses() -> pandas.DataFrame
    save_expense(expense: dict) -> None
    delete_expense(doc_id: str) -> None
    month_total(df, year, month) -> float
    category_totals(df) -> pandas.Series
"""

import datetime
import pandas as pd
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

COLLECTION = "expenses"
CATEGORIES_COLLECTION = "categories"
SETTINGS_COLLECTION = "settings"
BUDGET_DOC_ID = "monthly_budget"

DEFAULT_CATEGORIES = [
    {"name": "Food & Dining", "icon": "🍽️", "color": "#A78BFA"},
    {"name": "Transport", "icon": "🚗", "color": "#60A5FA"},
    {"name": "Groceries", "icon": "🛒", "color": "#34D399"},
    {"name": "Shopping", "icon": "🛍️", "color": "#F87171"},
    {"name": "Entertainment", "icon": "🎬", "color": "#F472B6"},
    {"name": "Bills & Utilities", "icon": "🧾", "color": "#FBBF24"},
    {"name": "Health & Fitness", "icon": "💊", "color": "#22D3EE"},
    {"name": "Education", "icon": "📚", "color": "#818CF8"},
    {"name": "Travel", "icon": "✈️", "color": "#FB923C"},
    {"name": "Other", "icon": "•", "color": "#9CA3AF"},
]


@st.cache_resource(show_spinner=False)
def _get_client():
    """Initialize the Firebase app once per session and return a Firestore client."""
    if not firebase_admin._apps:
        cred_dict = dict(st.secrets["firebase_service_account"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def load_expenses() -> pd.DataFrame:
    """Fetch all expenses as a DataFrame, newest first."""
    db = _get_client()
    docs = db.collection(COLLECTION).order_by(
        "date", direction=firestore.Query.DESCENDING
    ).stream()

    rows = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        rows.append(data)

    columns = ["id", "date", "raw_text", "merchant", "amount", "category",
               "source", "payment_mode", "account", "notes"]
    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in columns:
        if col not in df.columns:
            df[col] = "" if col not in ("amount",) else 0.0
    df["payment_mode"] = df["payment_mode"].fillna("Cash").replace("", "Cash")
    df["notes"] = df["notes"].fillna("")
    return df


def save_expense(expense: dict) -> str:
    """
    Add one expense document.
    Expected keys: raw_text, merchant, amount, category, source,
    payment_mode, account, notes (all optional except amount/category).
    'date' is stamped automatically as today unless explicitly provided.
    Returns the new document's ID.
    """
    db = _get_client()
    doc = {
        "date": expense.get("date", datetime.date.today().isoformat()),
        "raw_text": expense.get("raw_text", ""),
        "merchant": expense.get("merchant", "Unknown"),
        "amount": float(expense.get("amount") or 0),
        "category": expense.get("category", "Other"),
        "source": expense.get("source", "text"),
        "payment_mode": expense.get("payment_mode", "Cash"),
        "account": expense.get("account", ""),
        "notes": expense.get("notes", ""),
    }
    _, ref = db.collection(COLLECTION).add(doc)
    return ref.id


def delete_expense(doc_id: str) -> None:
    db = _get_client()
    db.collection(COLLECTION).document(doc_id).delete()


def update_expense(doc_id: str, updates: dict) -> None:
    """
    Update specific fields of an existing expense document.
    """
    db = _get_client()
    allowed_fields = {"merchant", "amount", "category", "raw_text", "source",
                       "date", "payment_mode", "account", "notes"}
    clean_updates = {k: v for k, v in updates.items() if k in allowed_fields}
    if "amount" in clean_updates:
        clean_updates["amount"] = float(clean_updates["amount"] or 0)
    if clean_updates:
        db.collection(COLLECTION).document(doc_id).update(clean_updates)


def month_total(df: pd.DataFrame, year: int, month: int) -> float:
    """Sum of amounts for a given year/month."""
    if df.empty:
        return 0.0
    mask = (df["date"].dt.year == year) & (df["date"].dt.month == month)
    return float(df.loc[mask, "amount"].sum())


def category_totals(df: pd.DataFrame) -> pd.Series:
    """Total spend per category, sorted descending."""
    if df.empty:
        return pd.Series(dtype=float)
    return df.groupby("category")["amount"].sum().sort_values(ascending=False)


def payment_mode_totals(df: pd.DataFrame) -> pd.Series:
    """Total spend per payment mode, sorted descending."""
    if df.empty:
        return pd.Series(dtype=float)
    return df.groupby("payment_mode")["amount"].sum().sort_values(ascending=False)


def top_merchants(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Top N merchants by total spend, with transaction counts.

    Grouping is case- and whitespace-insensitive. Rows saved before merchant
    normalisation was fixed contain spellings like "Mcdonald'S" alongside
    "McDonald's"; grouping on the raw string split one real merchant across two
    rows and understated both. The display name shown is the most common
    spelling for that merchant.
    """
    if df.empty:
        return pd.DataFrame(columns=["merchant", "amount", "count"])

    working = df.copy()
    working["merchant"] = working["merchant"].fillna("Unknown").astype(str)
    working["_merchant_key"] = working["merchant"].str.strip().str.casefold()

    def _display_name(names: pd.Series) -> str:
        # .strip() so a stray-whitespace variant does not become the label shown.
        cleaned = names.str.strip()
        modes = cleaned.mode()
        return modes.iat[0] if not modes.empty else cleaned.iat[0]

    grouped = working.groupby("_merchant_key").agg(
        merchant=("merchant", _display_name),
        amount=("amount", "sum"),
        count=("amount", "size"),
    ).reset_index(drop=True)

    return grouped.sort_values("amount", ascending=False).head(n)


# --- Categories (custom categories, merged with defaults) ---

def load_categories() -> list:
    """
    Returns the full category list: built-in defaults plus any custom
    categories the user has added, merged and deduplicated by name.
    """
    db = _get_client()
    docs = db.collection(CATEGORIES_COLLECTION).stream()
    custom = [doc.to_dict() | {"id": doc.id} for doc in docs]

    result = list(DEFAULT_CATEGORIES)
    existing_names = {c["name"] for c in result}
    for c in custom:
        if c.get("name") and c["name"] not in existing_names:
            result.append(c)
            existing_names.add(c["name"])
    return result


def add_category(name: str, icon: str = "🏷️", color: str = "#9CA3AF") -> None:
    db = _get_client()
    db.collection(CATEGORIES_COLLECTION).add({"name": name, "icon": icon, "color": color})


def delete_category(doc_id: str) -> None:
    db = _get_client()
    db.collection(CATEGORIES_COLLECTION).document(doc_id).delete()


# --- Budget ---

def get_budget() -> float:
    """Returns the monthly budget goal, or 0.0 if not set."""
    db = _get_client()
    doc = db.collection(SETTINGS_COLLECTION).document(BUDGET_DOC_ID).get()
    if doc.exists:
        return float(doc.to_dict().get("amount", 0))
    return 0.0


def set_budget(amount: float) -> None:
    db = _get_client()
    db.collection(SETTINGS_COLLECTION).document(BUDGET_DOC_ID).set({"amount": float(amount)})


# --- Profile name ---
# Stored the same way as the budget goal - one doc in the same settings
# collection - so each person's own Firestore project remembers their own
# display name instead of it being hardcoded in app.py.

NAME_DOC_ID = "profile"


def get_user_name() -> str:
    """Returns the saved display name, or "" if never set."""
    db = _get_client()
    doc = db.collection(SETTINGS_COLLECTION).document(NAME_DOC_ID).get()
    if doc.exists:
        return str(doc.to_dict().get("name", "") or "")
    return ""


def set_user_name(name: str) -> None:
    db = _get_client()
    db.collection(SETTINGS_COLLECTION).document(NAME_DOC_ID).set({"name": name.strip()})
































