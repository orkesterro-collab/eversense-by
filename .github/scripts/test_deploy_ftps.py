"""Verify incremental selection without any remote writes or credentials."""
import ftplib
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location('deploy_ftps', Path(__file__).with_name('deploy_ftps.py'))
DEPLOY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEPLOY)


def write(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


class DeltaTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.current = self.root / 'current'
        self.previous = self.root / 'previous'
        for root in (self.current, self.previous):
            write(root, 'index.html', b'old homepage')
            write(root, '.htaccess', b'same hidden configuration')
            write(root, 'assets/same.webp', b'identical bytes')
            write(root, 'assets/changed.js', b'old')
        write(self.current, 'index.html', b'new homepage')
        write(self.current, 'assets/changed.js', b'new')  # same size and mtime do not prove equality
        for root in (self.current, self.previous):
            os.utime(root / 'assets/changed.js', (1000, 1000))
        write(self.current, 'assets/new.webp', b'new image')

    def test_exact_homepage_proof_skips_only_identical_bytes(self):
        files, proven = DEPLOY.select_files(self.current, self.previous, b'old homepage')
        self.assertTrue(proven)
        self.assertEqual([p.relative_to(self.current).as_posix() for p in files],
                         ['assets/changed.js', 'assets/new.webp', 'index.html'])

    def test_unproven_homepage_falls_back_to_all_files(self):
        for remote in (b'different homepage', None):
            files, proven = DEPLOY.select_files(self.current, self.previous, remote)
            self.assertFalse(proven)
            self.assertEqual(files, DEPLOY.ordered_files(self.current))
            self.assertEqual(files[-1].name, 'index.html')

    def test_local_price_revision_is_strict(self):
        for url in ('assets/prices.js?v=123456abcdef', '/assets/prices.js?v=123456abcdef'):
            self.assertEqual(DEPLOY.release_revision(f'<script src="{url}"></script>'.encode()), '123456abcdef')
        for html in (b'<script src="https://elsewhere/assets/prices.js?v=123456abcdef"></script>',
                     b'<script src="assets/prices.js?v=123456abcdef&x=1"></script>',
                     b'<script src="assets/prices.js?v=123456abcdef0"></script>',
                     b'<script src="assets/prices.js?v=123456abcdef"></script>' * 2,
                     b'<script src="assets/prices.js"></script>', b'<script src></script>', b'\xff'):
            self.assertIsNone(DEPLOY.release_revision(html))

    def test_remote_read_is_bounded(self):
        ftp = Mock()
        def retrieve(command, receive, blocksize):
            self.assertEqual(command, 'RETR index.html')
            receive(b'12345678')
            receive(b'901')
        ftp.retrbinary.side_effect = retrieve
        with patch.object(DEPLOY, 'MAX_REMOTE_HOMEPAGE', 10):
            self.assertRaises(ValueError, DEPLOY.read_remote_homepage, ftp)

    def test_failed_retr_closes_reconnects_and_uploads_everything(self):
        ftp, replacement = Mock(), Mock()
        with patch.object(DEPLOY, 'read_remote_homepage', side_effect=ftplib.error_temp('read failed')), \
             patch.object(DEPLOY, 'connect', return_value=replacement) as connect:
            selected_ftp, files = DEPLOY.plan_upload(ftp, self.current, self.root)
        ftp.close.assert_called_once()
        connect.assert_called_once()
        self.assertIs(selected_ftp, replacement)
        self.assertEqual(files, DEPLOY.ordered_files(self.current))

    def test_unknown_ancestor_falls_back_without_reconstruction(self):
        ftp = Mock()
        with patch.object(DEPLOY, 'read_remote_homepage', return_value=b'old homepage'), \
             patch.object(DEPLOY, 'known_ancestor', return_value=None), \
             patch.object(DEPLOY, 'reconstruct_release') as reconstruct:
            selected_ftp, files = DEPLOY.plan_upload(ftp, self.current, self.root)
        self.assertIs(selected_ftp, ftp)
        reconstruct.assert_not_called()
        self.assertEqual(files, DEPLOY.ordered_files(self.current))

    def test_reconstruction_failure_falls_back_without_remote_writes(self):
        ftp = Mock()
        for failure in (ValueError('not reproducible'), subprocess.TimeoutExpired('staging', 90)):
            with patch.object(DEPLOY, 'read_remote_homepage', return_value=b'old homepage'), \
                 patch.object(DEPLOY, 'known_ancestor', return_value='a' * 40), \
                 patch.object(DEPLOY, 'reconstruct_release', side_effect=failure):
                selected_ftp, files = DEPLOY.plan_upload(ftp, self.current, self.root)
            self.assertIs(selected_ftp, ftp)
            self.assertEqual(files, DEPLOY.ordered_files(self.current))
        ftp.storbinary.assert_not_called()

    def test_plan_requires_proof_even_with_known_ancestor(self):
        ftp = Mock()
        for remote, expected_count in ((b'old homepage', 3), (b'edited homepage', 5)):
            with patch.object(DEPLOY, 'read_remote_homepage', return_value=remote), \
                 patch.object(DEPLOY, 'known_ancestor', return_value='a' * 40), \
                 patch.object(DEPLOY, 'reconstruct_release', return_value=self.previous):
                _, files = DEPLOY.plan_upload(ftp, self.current, self.root)
            self.assertEqual(len(files), expected_count)
            self.assertEqual(files[-1].relative_to(self.current).as_posix(), 'index.html')


class GitProofTests(unittest.TestCase):
    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, text=True,
                                       stderr=subprocess.DEVNULL).strip()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.git('init', '-b', 'main')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Deployment proof test')
        write(self.root, 'index.html', b'original')
        write(self.root, 'README.md', b'not public')
        write(self.root, '.github/scripts/prepare_hoster_site.py',
              b'import os\nfrom pathlib import Path\n'
              b'assert "FTP_PASSWORD" not in os.environ and "GITHUB_TOKEN" not in os.environ\n'
              b'Path("_deploy/index.html").write_text("old transform:" + os.environ["GITHUB_SHA"])\n')
        self.git('add', '.')
        self.git('commit', '-m', 'previous')
        self.previous_sha = self.git('rev-parse', 'HEAD')
        write(self.root, '.github/scripts/prepare_hoster_site.py', b'raise RuntimeError("current code must not run")\n')
        self.git('add', '.')
        self.git('commit', '-m', 'current')

    def test_only_known_ancestors_are_accepted(self):
        self.assertEqual(DEPLOY.known_ancestor(self.root, self.previous_sha[:12]), self.previous_sha)
        self.git('checkout', '-b', 'other', self.previous_sha)
        write(self.root, 'other.txt', b'other branch')
        self.git('add', '.')
        self.git('commit', '-m', 'unrelated descendant')
        other = self.git('rev-parse', 'HEAD')
        self.git('checkout', 'main')
        self.assertIsNone(DEPLOY.known_ancestor(self.root, other[:12]))
        self.assertIsNone(DEPLOY.known_ancestor(self.root, '0' * 12))

    def test_reconstruction_uses_ancestor_transform_and_full_sha(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {'FTP_PASSWORD': 'fake-password', 'GITHUB_TOKEN': 'fake-token'}):
                staged = DEPLOY.reconstruct_release(self.root, self.previous_sha, temporary)
            self.assertEqual((staged / 'index.html').read_text(), 'old transform:' + self.previous_sha)
            self.assertFalse((staged / '.github').exists())
            self.assertFalse((staged / 'README.md').exists())


if __name__ == '__main__':
    unittest.main()
