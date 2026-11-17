#!/usr/bin/env python3
"""Keep the Russian homepage history teaser immediately before its footer."""
from pathlib import Path
import re

START = '<!-- EVERSENSE HISTORY BANNER START -->'
END = '<!-- EVERSENSE HISTORY BANNER END -->'
CSS = '<link rel="stylesheet" href="assets/history-banner.css?v=20261117brand2">'

BANNER = '''<section id="ev-history-banner" aria-labelledby="ev-history-banner-title">
  <img class="ev-history-banner__image" src="assets/history/production-hall.jpg" alt="Оборудование производственного комплекса в Гагарине" width="800" height="533" loading="lazy" decoding="async">
  <div class="ev-history-banner__inner">
    <p class="ev-history-banner__eyebrow">Наша история</p>
    <h2 id="ev-history-banner-title">За EVERSENSE —<br>большое производство.</h2>
    <p class="ev-history-banner__lead">Европейская школа, полный цикл в Гагарине и внимание к каждой детали — от древесной основы до рельефа поверхности.</p>
    <a class="ev-history-banner__link" href="history.html">Познакомиться с производством <span aria-hidden="true">→</span></a>
    <p class="ev-history-banner__credit">Производственная площадка в Гагарине</p>
  </div>
</section>'''


def make_history_banner(source):
    """Replace only our marked content and keep the existing footer intact."""
    source = re.sub(re.escape(START) + r'.*?' + re.escape(END) + r'\s*',
                    '', source, flags=re.S)
    source = re.sub(r'<link\b[^>]*href=["\']assets/history-banner\.css(?:\?[^"\']*)?["\'][^>]*>\s*',
                    '', source)
    marker = '<div id="ev-home-footer"'
    if marker not in source:
        raise ValueError('Russian homepage navigation footer was not found')
    source = source.replace(marker, START + '\n' + BANNER + '\n' + END + '\n' + marker, 1)
    return source.replace('</head>', CSS + '\n</head>', 1)


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    path = root / 'index.html'
    original = path.read_text(encoding='utf-8')
    updated = make_history_banner(original)
    path.write_text(updated, encoding='utf-8')
    print('index.html:', 'updated' if updated != original else 'already current')
