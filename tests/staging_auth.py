
"""Obtain fresh Supabase staging access tokens for CI tests."""
import json
import os
import urllib.error
import urllib.request

base = os.environ["MUEEN_STAGING_URL"].rstrip("/")
key = os.environ["MUEEN_PUBLISHABLE_KEY"]

roles = ("PRINCIPAL", "TEACHER", "COORDINATOR")

for role in roles:
    email = os.environ[f"MUEEN_{role}_EMAIL"]
    password = os.environ[f"MUEEN_{role}_PASSWORD"]

    req = urllib.request.Request(
        base + "/auth/v1/token?grant_type=password",
        data=json.dumps({
            "email": email,
            "password": password
        }).encode("utf-8"),
        headers={
            "apikey": key,
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Staging login failed for {role}: HTTP {exc.code}"
        ) from None

    token = result.get("access_token")
    if not token:
        raise RuntimeError(f"No access token returned for {role}")

    # Mask tokens in GitHub Actions logs.
    print(f"::add-mask::{token}")

    # Share fresh tokens with subsequent workflow steps.
    with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as env:
        env.write(f"MUEEN_{role}_JWT={token}\n")

    print(f"{role}: staging authentication successful")
