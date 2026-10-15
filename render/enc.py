"""Password-protected brief payloads (AES-256-GCM, PBKDF2-HMAC-SHA256) for the gated PDF / PowerPoint download.

The public site never contains the brief pages or slide XML in clear text: each item is stored as site/enc/<id>.json
({"v":1,"iter":N,"salt":b64,"iv":b64,"data":b64}) and decrypted in the browser with the download password (site/download.js).
The password comes from the environment (GitHub secret DOWNLOAD_PASSWORD) and is never written to the repository.
"""
import base64
import json
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ITER = 150_000
DEV_PASSWORD = "dev-only-password"


def get_password():
    pw = os.environ.get("DOWNLOAD_PASSWORD")
    if not pw:
        if os.environ.get("REQUIRE_DOWNLOAD_PASSWORD") == "1":
            raise SystemExit("DOWNLOAD_PASSWORD is required for this build (set the repository secret)")
        pw = DEV_PASSWORD
    return pw


def _key(password, salt, iterations=ITER):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations).derive(password.encode("utf-8"))


def b64(b):
    return base64.b64encode(b).decode("ascii")


def encrypt(payload, password):
    salt, iv = os.urandom(16), os.urandom(12)
    ct = AESGCM(_key(password, salt)).encrypt(iv, json.dumps(payload, ensure_ascii=False).encode("utf-8"), None)
    return {"v": 1, "iter": ITER, "salt": b64(salt), "iv": b64(iv), "data": b64(ct)}


def decrypt(blob, password):
    key = _key(password, base64.b64decode(blob["salt"]), blob["iter"])
    return json.loads(AESGCM(key).decrypt(base64.b64decode(blob["iv"]), base64.b64decode(blob["data"]), None).decode("utf-8"))
