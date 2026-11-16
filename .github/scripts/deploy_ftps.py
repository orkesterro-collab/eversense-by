#!/usr/bin/env python3
"""Deploy Eversence static files to verified hoster.by FTPS root.

The GitHub workflow must verify that this FTP root is web-served by eversense.by
before invoking this uploader. This script does not delete remote files.
"""
import ftplib
import hashlib
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import sys
import tarfile
import tempfile
import time

BASE = Path("_deploy")
SERVER = "vh108.hoster.by"
USERNAME = "eversense-deploy"
NETWORK_ERRORS = ftplib.all_errors + (OSError, EOFError)
MAX_REMOTE_HOMEPAGE = 4 * 1024 * 1024
PUBLIC_EXCLUDES = {'.git', '.github', 'scripts', 'reference', 'README.md', '_deploy', 'buyer-qa'}


def release_revision(homepage):
    """Accept exactly one local, release-versioned price client in the homepage."""
    sources = []
    class Scripts(HTMLParser):
        def handle_starttag(self, tag, attrs):
            src = dict(attrs).get('src') or ''
            if tag == 'script' and re.match(r'^/?assets/prices\.js(?:[?#]|$)', src):
                sources.append(src)
    try:
        Scripts().feed(homepage.decode('utf-8'))
    except (UnicodeError, ValueError):
        return None
    if len(sources) != 1:
        return None
    match = re.fullmatch(r'/?assets/prices\.js\?v=([0-9a-f]{12})', sources[0])
    return match.group(1) if match else None


def known_ancestor(repository, revision):
    """Resolve only a locally available commit proven to be an ancestor of HEAD."""
    if not revision or not re.fullmatch(r'[0-9a-f]{12}', revision):
        return None
    resolved = subprocess.run(['git', 'rev-parse', '--verify', revision + '^{commit}'],
                              cwd=repository, capture_output=True, text=True)
    sha = resolved.stdout.strip()
    if resolved.returncode or not re.fullmatch(r'[0-9a-f]{40}', sha):
        return None
    ancestor = subprocess.run(['git', 'merge-base', '--is-ancestor', sha, 'HEAD'],
                              cwd=repository, capture_output=True)
    return sha if ancestor.returncode == 0 else None


def reconstruct_release(repository, sha, temporary):
    """Run the proven commit's own staging transform, never the current one."""
    source = Path(temporary) / 'source'
    source.mkdir()
    with subprocess.Popen(['git', 'archive', '--format=tar', sha], cwd=repository,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        try:
            with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
                archive.extractall(source, filter='data')
        except BaseException:
            process.kill()
            process.communicate()
            raise
        process.communicate()
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, 'git archive')
    staged = source / '_deploy'
    staged.mkdir()
    for entry in source.iterdir():
        if entry.name in PUBLIC_EXCLUDES:
            continue
        target = staged / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target, symlinks=True)
        else:
            shutil.copy2(entry, target, follow_symlinks=False)
    # Historical staging is offline and needs no deployment/GitHub credentials.
    environment = {key: value for key, value in os.environ.items()
                   if key in {'PATH', 'LANG', 'TZ', 'TMP', 'TEMP', 'TMPDIR'} or key.startswith('LC_')}
    environment['GITHUB_SHA'] = sha
    subprocess.run([sys.executable, '.github/scripts/prepare_hoster_site.py'], cwd=source,
                   env=environment, check=True, timeout=90,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return staged


def ordered_files(base):
    return sorted((path for path in base.rglob('*') if path.is_file()),
                  key=lambda path: (path.relative_to(base).as_posix() == 'index.html',
                                    path.relative_to(base).as_posix()))


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').digest()


def select_files(base, previous=None, remote_homepage=None):
    """Skip bytes only after exact homepage proof; size and mtime are irrelevant."""
    files = ordered_files(base)
    if previous is None or remote_homepage != (previous / 'index.html').read_bytes():
        return files, False
    return [path for path in files
            if not (previous / path.relative_to(base)).is_file()
            or digest(path) != digest(previous / path.relative_to(base))], True


def read_remote_homepage(ftp):
    homepage = bytearray()
    def receive(block):
        if len(homepage) + len(block) > MAX_REMOTE_HOMEPAGE:
            raise ValueError('Remote homepage exceeds proof limit')
        homepage.extend(block)
    ftp.retrbinary('RETR index.html', receive, blocksize=65536)
    return bytes(homepage)


def plan_upload(ftp, base, repository):
    files = ordered_files(base)
    try:
        homepage = read_remote_homepage(ftp)
    except NETWORK_ERRORS + (ValueError,):
        # A failed RETR can leave the control channel out of sync. Reconnect
        # before the safe full upload, including when the size guard fired.
        try:
            ftp.close()
        except OSError:
            pass
        print('Remote release could not be read; reconnecting for full upload.', flush=True)
        return connect(), files
    try:
        sha = known_ancestor(repository, release_revision(homepage))
        if sha is None:
            print('No known deployed ancestor; using full upload.', flush=True)
            return ftp, files
        with tempfile.TemporaryDirectory(prefix='eversense-deployed-') as temporary:
            previous = reconstruct_release(repository, sha, temporary)
            selected, proven = select_files(base, previous, homepage)
        if proven:
            print(f'Exact deployed homepage verified at {sha[:12]}; '
                  f'uploading {len(selected)} changed/new files, skipping {len(files) - len(selected)} identical files.', flush=True)
            return ftp, selected
        print('Remote homepage does not match reconstructed release; using full upload.', flush=True)
    except (OSError, ValueError, tarfile.TarError, subprocess.SubprocessError):
        # Failure to establish the proof may cost time, never missing files.
        print('Previous release reconstruction failed; using full upload.', flush=True)
    return ftp, files


def connect():
    context = ssl.create_default_context(cafile=os.environ["FTP_CA"])
    ftp = ftplib.FTP_TLS(context=context, timeout=55)
    ftp.connect(SERVER, 21)
    ftp.login(USERNAME, os.environ["FTP_PASSWORD"])
    ftp.prot_p()
    ftp.cwd(os.environ["FTP_TARGET_DIR"])
    return ftp


def main():
    if not (BASE / "index.html").is_file():
        raise SystemExit("Missing staged index.html")
    if not os.environ.get("FTP_TARGET_DIR"):
        raise SystemExit("No verified FTP_TARGET_DIR; refusing upload")
    created = set()
    ftp = connect()
    try:
        ftp, files = plan_upload(ftp, BASE, Path.cwd())
        total = len(files)
        print(f"Uploading {total} static files to independently verified eversense.by web directory", flush=True)
        print("Uploading into independently verified directory:", ftp.pwd(), flush=True)
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
