"""Link the Russian homepage's strength claims to the laminate test guide.

Patch only the text inside existing Tilda atoms so the carousel geometry and
native swipe controls remain untouched. Reapplying the function is safe.
"""
from html import escape
from pathlib import Path
import re


TARGETS = {
    '1003959231': {
        '1742550593945': ('classes', '34 класс: таблица классов ламината'),
    },
    '1028577716': {
        '1742902620650': ('classes', 'Стойкость к износу: классы и испытания ламината'),
        '1742902620666': ('classes', '34 класс: классы применения и испытания ламината'),
        '1746691721257': ('classes', '34 класс: классы применения и испытания ламината'),
    },
    '1028577721': {
        '1742902620650': ('impact-resistance', 'Способность держать удар: как проверяют ударопрочность'),
        '1742902620663': ('impact-resistance', 'Высокая ударная прочность: метод и результат испытания'),
        '1746692581724': ('impact-resistance', 'Высокая ударная прочность: метод и результат испытания'),
    },
}


def make_home_article_links(source):
    if 'id="rec1028577716"' not in source:
        return source  # The English homepage has its own copy and record IDs.
    asset_match = re.search(r'''(?:src|href)=["']((?:\.\./)*assets/)''', source)
    if not asset_match:
        raise ValueError('Cannot resolve homepage relative asset path')
    prefix = asset_match[1][:-len('assets/')]
    for record, fields in TARGETS.items():
        pattern = r'<div id="rec' + record + r'"\s.*?(?=<div id="rec\d+"\s)'
        match = re.search(pattern, source, re.S)
        if not match:
            raise ValueError('Missing Russian homepage record: ' + record)
        block = match[0]
        for field, (fragment, label) in fields.items():
            atom = re.compile(r'(<h[23]\b[^>]*\bfield=["\']tn_text_' + field + r'["\'][^>]*>)(.*?)(</h[23]>)', re.S)
            def link_text(found):
                text = found[2]
                if 'class="ev-home-article-link"' in text:
                    return found[0]
                target = prefix + 'laminate-classes.html#' + fragment
                return (found[1] + '<a class="ev-home-article-link" href="' + target +
                        '" aria-label="' + escape(label, quote=True) + '">' + text + '</a>' + found[3])
            block, count = atom.subn(link_text, block)
            if count != 1:
                raise ValueError(f'Expected one text atom {record}/{field}, found {count}')
        source = source[:match.start()] + block + source[match.end():]
    if 'id="ev-home-article-links-css"' not in source:
        source = source.replace('</head>', '<link id="ev-home-article-links-css" rel="stylesheet" href="' +
                                prefix + 'assets/home-article-links.css?v=20261115"></head>', 1)
    return source


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    for relative in ('index.html', 'ru/index.html'):
        path = root / relative
        original = path.read_text(encoding='utf-8')
        updated = make_home_article_links(original)
        path.write_text(updated, encoding='utf-8')
        print(relative, 'updated' if updated != original else 'already linked')
