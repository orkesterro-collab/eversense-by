import importlib.util
from pathlib import Path
import tempfile
import json
from html.parser import HTMLParser
import unittest

spec = importlib.util.spec_from_file_location('pages', Path(__file__).with_name('prepare_pages_site.py'))
pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pages)


class PagesNavigationTest(unittest.TestCase):
    def test_real_routes_only_and_idempotence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'catalog-ru').mkdir()
            (root / 'catalog-ru/index.html').touch()
            (root / 'index.html').touch()
            source = '''<a href="/">Home</a><a href='/catalog-ru?x=1&amp;y=2#top'>Catalog</a><a href="https://orkesterro-collab.github.io/catalog-ru/">Mirror</a><a href="https://eversense.by/catalog-ru/">Host</a><a href="/eversense-by/catalog-ru/">Ready</a><a href="/unknown">Missing</a><a href="//external.test/">External</a><a href="#top">Anchor</a><a href="tel:+123">Phone</a><script>var x='<a href="/">';</script><link rel="canonical" href="/">'''
            updated, count = pages.rewrite(source, root)
            self.assertEqual(count, 3)
            self.assertIn('href="/eversense-by/"', updated)
            self.assertIn("href='/eversense-by/catalog-ru/?x=1&amp;y=2#top'", updated)
            self.assertIn('https://orkesterro-collab.github.io/eversense-by/catalog-ru/', updated)
            for part in ['https://eversense.by/catalog-ru/', 'href="/unknown"', 'href="//external.test/"', 'href="#top"', 'href="tel:+123"', '<script>var x=\'<a href="/">\';</script>', '<link rel="canonical" href="/">']:
                self.assertIn(part, updated)
            self.assertEqual(pages.rewrite(updated, root), (updated, 0))

    def test_staged_el1052_navigation_and_source_unchanged(self):
        repo = Path(__file__).resolve().parents[2]
        product = next(p for p in json.loads((repo / 'assets/products-data.json').read_text()) if p['sku'] == 'EL1052')
        source = repo / product['sourcePath']
        original = source.read_text()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            # Build the real HTML route inventory in a separate mirror staging tree.
            for path in repo.rglob('*.html'):
                relative = path.relative_to(repo)
                if any(part.startswith(('.', '_')) for part in relative.parts):
                    continue
                staged = root / relative
                staged.parent.mkdir(parents=True, exist_ok=True)
                staged.touch()
            staged = root / product['sourcePath']
            updated, count = pages.rewrite(original, root)
            staged.write_text(updated)
            self.assertGreater(count, 0)
            class Anchors(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.hrefs = []
                def handle_starttag(self, tag, attrs):
                    if tag == 'a':
                        self.hrefs.extend(value for key, value in attrs if key == 'href')
            anchors = Anchors()
            anchors.feed(staged.read_text())
            self.assertIn('/eversense-by/', anchors.hrefs)
            self.assertIn('/eversense-by/catalog-ru/', anchors.hrefs)
            self.assertNotIn('/', anchors.hrefs)
            self.assertNotIn('/catalog-ru', anchors.hrefs)
            self.assertEqual(pages.rewrite(updated, root), (updated, 0))
        self.assertEqual(source.read_text(), original)


if __name__ == '__main__':
    unittest.main()
