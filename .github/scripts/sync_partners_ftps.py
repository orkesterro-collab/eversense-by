#!/usr/bin/env python3
"""Upload ONLY partners page files into the verified hoster.by Eversense root.

FTP credential is read from a private GitHub Actions secret. Trust is pinned
to the verified hoster.by FTPS certificate. Never touches other hosted sites.
"""
from pathlib import Path
import ftplib
import hashlib
import io
import os
import re
import secrets
import ssl
import subprocess
import time

HOST = "vh108.hoster.by"
IP = "87.232.64.108"
DOMAINS = ("eversense.by", "www.eversense.by")
PIN_SHA256 = "25327D62994712DD70353A3F2C3B7F35666073CCC950A04785A37D4E5E8EC9BB"
PATHS = ["assets/partners.js", "assets/partners.css", "where-to-buy.html"]
CANDIDATES = [".", "../eversense.by", "/eversense.by", "eversense.by",
              "/www/eversense.by", "www/eversense.by",
              "../../eversense.by", "../../www/eversense.by"]

for path in PATHS:
    if not Path(path).is_file():
        raise SystemExit("Required website file missing: " + path)

probe = subprocess.run(
    ["openssl", "s_client", "-connect", HOST + ":21", "-starttls", "ftp",
     "-servername", HOST, "-showcerts"],
    text=True, input="", capture_output=True, timeout=20)
match = re.search(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----",
                  probe.stdout, re.S)
if not match:
    raise SystemExit("Hoster FTPS certificate unavailable; refusing credentials")
pem = match.group(0)
hash_value = hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest().upper()
if hash_value != PIN_SHA256:
    raise SystemExit("Hoster FTPS certificate is different from pinned certificate")
context = ssl.create_default_context(cadata=pem)

def connect(target="."):
    ftp = ftplib.FTP_TLS(context=context, timeout=55)
    ftp.connect(HOST, 21)
    ftp.login("eversense-deploy", os.environ["EVERSENSE_FTP_SECRET"])
    ftp.prot_p()
    ftp.cwd("/")
    ftp.cwd(target)
    return ftp

ftp = connect()
chosen = None
try:
    marker = "partners-probe-" + secrets.token_hex(10) + ".txt"
    body = ("partners-root-" + secrets.token_hex(24)).encode()
    for candidate in CANDIDATES:
        try:
            ftp.cwd("/")
            ftp.cwd(candidate)
            ftp.storbinary("STOR " + marker, io.BytesIO(body))
        except ftplib.all_errors:
            continue
        try:
            passed = []
            for domain in DOMAINS:
                checked = subprocess.run(
                    ["curl", "-ksSL", "--max-time", "20", "--resolve",
                     domain + ":443:" + IP,
                     "https://" + domain + "/" + marker],
                    capture_output=True, timeout=28)
                if checked.returncode == 0 and checked.stdout == body:
                    passed.append(domain)
            if len(passed) == len(DOMAINS):
                chosen = candidate
                break
        finally:
            ftp.delete(marker)
    if chosen is None:
        raise SystemExit("FTP directory not verified for both Eversense domains; nothing uploaded")
    print("Verified webroot", chosen, flush=True)

    for name in PATHS:
        for attempt in range(3):
            try:
                with Path(name).open("rb") as f:
                    ftp.storbinary("STOR " + name, f, blocksize=65536)
                print("Uploaded:", name, Path(name).stat().st_size, "bytes", flush=True)
                break
            except ftplib.all_errors + (OSError, EOFError):
                if attempt == 2:
                    raise
                try:
                    ftp.close()
                except OSError:
                    pass
                time.sleep(1 + attempt)
                ftp = connect(chosen)

    for domain in DOMAINS:
        for name in PATHS:
            target = "https://" + domain + "/" + name
            actual = subprocess.run(
                ["curl", "-ksSL", "--max-time", "30", "--resolve",
                 domain + ":443:" + IP, target],
                capture_output=True, timeout=40)
            if actual.returncode != 0 or actual.stdout != Path(name).read_bytes():
                raise SystemExit("Published file differs from source: " + target)
            print("Verified:", target, flush=True)
    print("PASS: Eversense partner map/list files published and verified", flush=True)
finally:
    try:
        ftp.quit()
    except ftplib.all_errors + (OSError, EOFError):
        ftp.close()
