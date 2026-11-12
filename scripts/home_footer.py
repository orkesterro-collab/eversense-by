"""Replace the duplicated homepage footer content, preserving cookie controls."""
from html.parser import HTMLParser
import re


def make_home_footer(source):
    if 'id="ev-home-footer"' in source:
        return source
    language = 'en' if 'id="rec1040271676"' in source else 'ru'
    asset = re.search(r'href="([^"]*assets/)belarus-footer\.css"', source)
    if not asset or 'id="t-footer"' not in source:
        raise ValueError('Homepage footer or local asset path missing')
    prefix = asset[1][:-len('assets/')]
    offsets, position = [], 0
    for line in source.splitlines(keepends=True):
        offsets.append(position)
        position += len(line)
    spans = []

    class Blocks(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.stack = []

        def handle_starttag(self, tag, attrs):
            if tag not in ('div', 'section'):
                return
            values = dict(attrs)
            remove = (values.get('id') in ('rec1128306611', 'rec1128311571')
                      or 'ev-belarus-legal' in values.get('class', '').split()
                      or values.get('aria-labelledby') == 'ev-belarus-contact-title')
            line, column = self.getpos()
            start = offsets[line - 1] + column
            if remove and not source[offsets[line - 1]:start].strip():
                start = offsets[line - 1]
            self.stack.append((tag, start, remove))

        def handle_endtag(self, tag):
            if tag not in ('div', 'section') or not self.stack:
                return
            opened, start, remove = self.stack.pop()
            if opened != tag:
                raise ValueError('Unbalanced homepage footer markup')
            if remove:
                line, column = self.getpos()
                spans.append((start, offsets[line - 1] + column + len('</' + tag + '>')))

    Blocks().feed(source)
    for start, end in sorted(spans, reverse=True):
        source = source[:start] + source[end:]
    source = re.sub(r'<link\b[^>]*href="[^"]*(?:belarus-footer|home-footer-trim)\.css"[^>]*>', '', source)
    if language == 'en':
        labels = ('Catalogue', 'Where to buy', 'Documents', 'Contacts', 'Privacy policy')
        company = 'Belarus representative — Florstock LLC · UNP 192608003'
        address = '220062, Belarus, Minsk, Pobediteley Ave. 129, office 358'
        nav_label, home_label = 'Footer navigation', 'EVERSENSE home'
        catalog, home = 'catalog-en/', 'en/'
    else:
        labels = ('Каталог', 'Где купить', 'Документы', 'Контакты', 'Конфиденциальность')
        company = 'Представитель в Беларуси — ООО «Флорсток» · УНП 192608003'
        address = '220062, г. Минск, пр. Победителей, д. 129, пом. 358'
        nav_label, home_label = 'Навигация внизу страницы', 'EVERSENSE, на главную'
        catalog, home = 'catalog-ru/', 'index.html'
    targets = (catalog, 'where-to-buy.html', 'downloads.html', 'contacts.html')
    links = ''.join(f'<a href="{prefix}{target}">{label}</a>' for label, target in zip(labels, targets))
    footer = f'''<div id="ev-home-footer" class="ev-home-footer">
  <div class="ev-home-footer__inner">
    <div class="ev-home-footer__top">
      <a class="ev-home-footer__brand" href="{prefix}{home}" aria-label="{home_label}"><img src="{asset[1]}original-tilda/44ef8387add2-Frame_784.svg" alt="EVERSENSE" width="176" height="64" loading="lazy"></a>
      <nav class="ev-home-footer__nav" aria-label="{nav_label}">{links}</nav>
      <a class="ev-home-footer__phone" href="tel:+375296713971">+375 29 671-39-71</a>
    </div>
    <div class="ev-home-footer__bottom">
      <div class="ev-home-footer__legal"><p>{company}</p><p>{address}</p></div>
      <a href="{prefix}privacy.html">{labels[4]}</a>
    </div>
  </div>
</div>'''
    source = source.replace('</footer>', footer + '</footer>', 1)
    return source.replace('</head>', f'<link rel="stylesheet" href="{asset[1]}home-footer.css"></head>', 1)
