#!/usr/bin/env python3
"""Deploy Eversence static files to verified hoster.by FTPS root.

The GitHub workflow must verify that this FTP root is web-served by eversense.by
before invoking this uploader. This script does not delete remote files.
"""
import ftplib
import os
from pathlib import Path
import ssl
import sys
import time

BASE = Path("_deploy")
SERVER = "vh108.hoster.by"
USERNAME = "eversense-deploy"
NETWORK_ERRORS = ftplib.all_errors + (OSError, EOFError)


def connect():
    context = ssl.create_default_context(cafile=os.environ["FTP_CA"])
    ftp = ftplib.FTP_TLS(context=context, timeout=55)
    ftp.connect(SERVER, 21)
    ftp.login(USERNAME, os.environ["FTP_PASSWORD"])
    ftp.prot_p()
    return ftp


def main():
    if not (BASE / "index.html").is_file():
        raise SystemExit("Missing staged index.html")
    files = sorted(p for p in BASE.rglob("*") if p.is_file())
    files.sort(key=lambda p: p.relative_to(BASE).as_posix() == "index.html")
    total = len(files)
    print(f"Uploading {total} static files to verified eversense.by FTP home", flush=True)
    created = set()
    ftp = connect()
    try:
        # Require the site's previously confirmed placeholder at the FTP root.
        # Prevents accidental upload to another user's FTP home.
        remote_names = ftp.nlst()
        if not any(name.rstrip("/").split("/")[-1] == "index.html" for name in remote_names):
            raise RuntimeError("index.html missing from FTP home; refusing upload")
        for n, path in enumerate(files, 1):
            rel = path.relative_to(BASE).as_posix()
            parts = rel.split("/")[:-1]
            prefix = ""
            for part in parts:
                prefix = f"{prefix}/{part}".lstrip("/")
                if prefix not in created:
                    try:
                        ftp.mkd(prefix)
                    except ftplib.error_perm as e:
                        if not str(e).startswith(("550", "521")):
                            raise
                    created.add(prefix)
            for attempt in range(1, 4):
                try:
                    with path.open("rb") as handle:
                        ftp.storbinary(f"STOR {rel}", handle, blocksize=131072)
                    break
                except NETWORK_ERRORS as exc:
                    if attempt == 3:
                        raise RuntimeError(f"Failed after 3 tries: {rel}: {exc}") from exc
                    print(f"Retrying {rel} after connection failure: {type(exc).__name__}", flush=True)
                    try:
                        ftp.close()
                    except OSError:
                        pass
                    time.sleep(attempt * 2)
                    ftp = connect()
            if n % 25 == 0 or n == total:
                print(f"Uploaded {n}/{total} files", flush=True)
        print("All static files uploaded. Old unrelated remote files were left intact.", flush=True)
    finally:
        try:
            ftp.quit()
        except NETWORK_ERRORS:
            ftp.close()


if __name__ == "__main__":
    main()
