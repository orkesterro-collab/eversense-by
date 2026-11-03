#!/usr/bin/env python3
"""Publish only HTML pages whose internal links were normalized by the site audit.

Uses a pinned FTPS certificate, verifies the FTP root via the live domain,
and leaves unrelated files untouched.
"""
import ftplib
import hashlib
import io
import json
import os
import re
import secrets
import ssl
import subprocess
import time
from pathlib import Path

HOST = "vh108.hoster.by"
IP = "87.232.64.108"
DOMAIN = "eversense.by"
PIN = "25327D62994712DD70353A3F2C3B7F35666073CCC950A04785A37D4E5E8EC9BB"
ROOT = Path("_deploy")
candidates = [".", "../eversense.by", "/eversense.by", "eversense.by",
              "/www/eversense.by", "www/eversense.by",
              "../../eversense.by", "../../www/eversense.by"]

changes = json.loads(Path("site-changed-html.json").read_text(encoding="utf-8"))
if not changes:
    raise SystemExit("No HTML pages require a link update")
for rel in changes:
    if not rel.endswith(".html") or ".." in Path(rel).parts or not (ROOT / rel).is_file():
        raise SystemExit("Unsafe or missing staged HTML path: " + str(rel))

res = subprocess.run(
    ["openssl", "s_client", "-connect", HOST + ":21", "-starttls", "ftp",
     "-servername", HOST, "-showcerts"],
    input="", text=True, capture_output=True, timeout=16)
match = re.search(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", res.stdout, re.S)
if not match:
    raise SystemExit("Missing FTPS certificate")
pem = match.group(0)
fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest().upper()
if fingerprint != PIN:
    raise SystemExit("FTPS certificate changed; refusing credentials")
context = ssl.create_default_context(cadata=pem)

def connect(candidate):
    ftp = ftplib.FTP_TLS(context=context, timeout=45)
    ftp.connect(HOST, 21)
    ftp.login("eversense-deploy", os.environ["FTP_PASSWORD"])
    ftp.prot_p()
    ftp.cwd("/")
    ftp.cwd(candidate)
    return ftp

ftp = connect(".")
target = None
try:
    marker = "eversense-directory-check-" + secrets.token_hex(12) + ".txt"
    token = secrets.token_hex(32).encode()
    for candidate in candidates:
        try:
            ftp.cwd("/")
            ftp.cwd(candidate)
            ftp.storbinary("STOR " + marker, io.BytesIO(token))
        except ftplib.all_errors:
            continue
        try:
            resp = subprocess.run(
                ["curl", "-ksSL", "--max-time", "15", "--resolve",
                 DOMAIN + ":443:" + IP, "https://" + DOMAIN + "/" + marker],
                capture_output=True, timeout=25)
            if resp.returncode == 0 and resp.stdout == token:
                target = candidate
                break
        finally:
            ftp.delete(marker)
    if target is None:
        raise SystemExit("Could not verify FTP root for eversense.by")
    print("Verified FTP directory:", target, flush=True)
    for n, rel in enumerate(changes, 1):
        for attempt in range(3):
            try:
                with (ROOT / rel).open("rb") as handle:
                    ftp.storbinary("STOR " + rel, handle, blocksize=131072)
                break
            except (ftplib.all_errors + (OSError, EOFError)) as exc:
                if attempt == 2:
                    raise RuntimeError(f"Failed to upload {rel}: {exc}") from exc
                try:
                    ftp.close()
                except OSError:
                    pass
                time.sleep((attempt + 1) * 2)
                ftp = connect(target)
        if n % 15 == 0 or n == len(changes):
            print(f"HTML updates uploaded: {n}/{len(changes)}", flush=True)
finally:
    try:
        ftp.quit()
    except (ftplib.all_errors + (OSError, EOFError)):
        ftp.close()

for rel in ["index.html", "catalog-ru/index.html", "catalog-ru/quiet-luxury-ru/index.html"]:
    if rel not in changes:
        continue
    url = "https://" + DOMAIN + "/" + rel
    result = subprocess.run(
        ["curl", "-ksSL", "--max-time", "30", "--resolve",
         DOMAIN + ":443:" + IP, url],
        capture_output=True, timeout=40)
    if result.returncode or result.stdout != (ROOT / rel).read_bytes():
        raise SystemExit("Live HTML mismatch after update: " + rel)
    print("Verified updated page:", rel, flush=True)
print(f"PASS: {len(changes)} link-corrected HTML pages published to {DOMAIN}", flush=True)
