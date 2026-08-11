"""
test_firestore_connection.py
Run this locally (not in Claude's sandbox) to verify Firestore is
actually reachable and read/write works end-to-end.

Usage (from inside the expense_manager folder, with .streamlit/secrets.toml
already in place):

    pip install firebase-admin streamlit toml --break-system-packages
    python3 test_firestore_connection.py
"""

import toml
import firebase_admin
from firebase_admin import credentials, firestore

# Load secrets the same way Streamlit would
secrets = toml.load(".streamlit/secrets.toml")
sa = dict(secrets["firebase_service_account"])

cred = credentials.Certificate(sa)
firebase_admin.initialize_app(cred)
db = firestore.client()

print("Connected to Firebase project:", sa["project_id"])

# Write a test document
doc_ref = db.collection("expenses").add({
    "date": "2026-08-09",
    "raw_text": "TEST connection check",
    "merchant": "Test",
    "amount": 1.0,
    "category": "Other",
    "source": "test_script",
})
print("Write successful. Document ID:", doc_ref[1].id)

# Read it back
docs = db.collection("expenses").stream()
print("\nCurrent documents in 'expenses' collection:")
for d in docs:
    print(" -", d.id, ":", d.to_dict())

# Clean up the test doc so it doesn't pollute real data
doc_ref[1].delete()
print("\nTest document deleted. Connection verified successfully!")
