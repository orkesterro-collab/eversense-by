#!/usr/bin/env python3
"""Verify/sync one critical Eversense price campaign script after full deployment.

Uses the same pinned FTPS server identity and webroot probe as main deployment.
Never publishes to unverified FTP directories.
"""
import ftplib
import hashlib
import io
import os
import re
import secrets
import ssl
import subprocess

HOST = "vh108.hoster.by"
IP = "87.232.64.108"
DOMAIN = "eversense.by"
PIN = "25327D62994712DD70353A3F2C3B7F35666073CCC950A04785A37D4E5E8EC9BB"
ASSET = "assets/black-friday.js"
candidates = [".", "../eversense.by", "/eversense.by", "eversense.by",
              "/www/eversense.by", "www/eversense.by",
              "../../eversense.by", "../../www/eversense.by"]

res = subprocess.run(
    ["openssl", "s_client", "-connect", HOST + ":21", "-starttls", "ftp",
     "-servername", HOST, "-showcerts"],
    input="", text=True, capture_output=True, timeout=16)
match = re.search(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", res.stdout, re.S)
if not match:
    raise SystemExit("No FTPS server certificate: refusing credentials")
pem = match.group(0)
fingerprint = hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest().upper()
if fingerprint != PIN:
    raise SystemExit("FTPS server identity changed: refusing credentials")
context = ssl.create_default_context(cadata=pem)
with ftplib.FTP_TLS(context=context, timeout=35) as ftp:
    ftp.connect(HOST, 21)
    ftp.login("eversense-deploy", os.environ["FTP_PASSWORD"])
    ftp.prot_p()
    match_dir = None
    marker = "eversense-verify-" + secrets.token_hex(12) + ".txt"
    token = secrets.token_hex(30)
    for target in candidates:
        try:
            ftp.cwd("/")
            ftp.cwd(target)
            ftp.storbinary("STOR " + marker, io.BytesIO(token.encode()))
        except ftplib.all_errors:
            continue
        try:
            resp = subprocess.run(
                ["curl", "-ksSL", "--max-time", "15", "--resolve",
                 DOMAIN + ":443:" + IP, "https://" + DOMAIN + "/" + marker],
                capture_output=True, timeout=25)
            if resp.returncode == 0 and resp.stdout == token.encode():
                match_dir = target
                break
        finally:
            ftp.delete(marker)
    if match_dir is None:
        raise SystemExit("FTP path does not serve eversense.by: nothing changed")
    data = open(ASSET, "rb").read()
    current = subprocess.run(
        ["curl", "-ksSL", "--max-time", "25", "--resolve",
         DOMAIN + ":443:" + IP, "https://" + DOMAIN + "/" + ASSET],
        capture_output=True, timeout=35)
    if current.returncode == 0 and current.stdout == data:
        print("Promo script is already current on " + DOMAIN)
    else:
        ftp.storbinary("STOR " + ASSET, io.BytesIO(data))
        print("Updated " + ASSET + " on verified " + DOMAIN)
    check = subprocess.run(
        ["curl", "-ksSL", "--max-time", "25", "--resolve",
         DOMAIN + ":443:" + IP, "https://" + DOMAIN + "/" + ASSET],
        capture_output=True, timeout=35)
    if check.returncode or check.stdout != data:
        raise SystemExit("Promo script served bytes do not match committed source")
    print("PASS: Campaign price script matches GitHub on eversense.by")
