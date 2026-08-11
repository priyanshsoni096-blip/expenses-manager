"""
json_to_secrets.py
One-time helper: converts a downloaded Firebase service account JSON key
into the .streamlit/secrets.toml format Streamlit expects.

Usage:
    python3 json_to_secrets.py path/to/downloaded-key.json

Safety behaviour (differs from the original version of this script):
  * The generated TOML is NEVER printed to the terminal. The private key
    would otherwise sit in your scrollback, ready to be copied into a
    chat, email or screenshot by accident. Only non-secret metadata is
    shown.
  * Refuses to append to an existing secrets.toml. Appending produced a
    file with two [firebase_service_account] tables, which is invalid
    TOML and fails at runtime with a confusing duplicate-key error.
    Delete the old file first, deliberately.
  * Writes the file with owner-only permissions (chmod 600).
  * Reminds you to delete the source JSON afterwards.
"""

import json
import os
import stat
import sys

SECRETS_DIR = ".streamlit"
SECRETS_PATH = os.path.join(SECRETS_DIR, "secrets.toml")

# Fields safe to echo to the terminal. Anything not listed here is treated
# as sensitive and never printed.
_SAFE_TO_DISPLAY = {
    "type", "project_id", "private_key_id", "client_email", "client_id",
    "auth_uri", "token_uri", "auth_provider_x509_cert_url",
    "client_x509_cert_url", "universe_domain",
}

_REQUIRED_KEYS = {"type", "project_id", "private_key", "client_email", "token_uri"}


def convert(json_path: str):
    """Returns (toml_text, parsed_dict)."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    missing = _REQUIRED_KEYS - data.keys()
    if missing:
        raise ValueError(
            "This does not look like a Firebase service account key. "
            f"Missing field(s): {', '.join(sorted(missing))}"
        )

    lines = ["[firebase_service_account]"]
    for key, value in data.items():
        if isinstance(value, str):
            escaped = (
                value.replace("\\", "\\\\")
                .replace("\n", "\\n")
                .replace('"', '\\"')
            )
            lines.append(f'{key} = "{escaped}"')
        else:
            lines.append(f"{key} = {json.dumps(value)}")

    return "\n".join(lines) + "\n", data


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 json_to_secrets.py path/to/downloaded-key.json")
        sys.exit(1)

    json_path = sys.argv[1]
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        print("\nTip: let the shell fill in the name for you, e.g.")
        print("    python3 json_to_secrets.py ~/Downloads/*-firebase-adminsdk-*.json")
        print("    python3 json_to_secrets.py ~/Downloads/<your-project-id>-*.json")
        sys.exit(1)

    # Refuse to append. Two [firebase_service_account] tables in one file is
    # invalid TOML, and silent appending made that easy to do by accident.
    if os.path.exists(SECRETS_PATH):
        print(f"{SECRETS_PATH} already exists - refusing to modify it.")
        print("\nIf you are rotating a key, remove the old file first:")
        print(f"    rm {SECRETS_PATH}")
        print("\nIf it contains other sections you need, back it up first.")
        sys.exit(1)

    try:
        toml_block, data = convert(json_path)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: {json_path} is not valid JSON.")
        sys.exit(1)

    os.makedirs(SECRETS_DIR, exist_ok=True)
    with open(SECRETS_PATH, "w", encoding="utf-8") as f:
        f.write(toml_block)

    os.chmod(SECRETS_PATH, stat.S_IRUSR | stat.S_IWUSR)  # owner read/write only

    print(f"Wrote {SECRETS_PATH} (permissions: owner read/write only)")
    print("\nNon-secret metadata, for your records:")
    for key in ("project_id", "private_key_id", "client_email"):
        if key in data and key in _SAFE_TO_DISPLAY:
            print(f"    {key} = {data[key]}")

    print("\nThe private key was written to the file but deliberately NOT")
    print("printed here. Do not open, copy, paste or screenshot that file.")
    print("\nNext steps:")
    print(f"    rm {json_path}")
    print(f"    grep -c '\\[firebase_service_account\\]' {SECRETS_PATH}   # must print 1")


if __name__ == "__main__":
    main()
