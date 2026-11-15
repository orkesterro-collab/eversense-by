"""Render the laminate classification article from structured editorial content."""
from html import escape


def _e(value):
    return escape(str(value), quote=True)


def _paragraphs(items):
    return ''.join('<p>' + _e(item) + '</p>' for item in items)


def _downloads(items, page, href):
    return '<div class="ev-class-documents" aria-label="Скачать официальные документы">' + ''.join(
        '<a href="' + _e(href(item['url'], page)) + '" download><span>' + _e(item['label']) + '</span><span class="ev-class-document-meta">Скачать · ' + _e(item['meta']) + ' <span aria-hidden="true">↓</span></span></a>'
        for item in items
    ) + '</div>'


def _table(table, section_id):
    columns = table['columns']
    rows = []
    for row in table['rows']:
        highlight = ' class="ev-class-highlight"' if section_id == 'classes' and row[0] == '34' else ''
        cells = '<th scope="row" role="rowheader">' + _e(row[0]) + '</th>'
        cells += ''.join('<td role="cell"><span class="ev-install-table-label" aria-hidden="true">' + _e(columns[index]) + '</span><span>' + _e(value) + '</span></td>' for index, value in enumerate(row[1:], 1))
        rows.append('<tr role="row"' + highlight + '>' + cells + '</tr>')
    return '<div class="ev-install-table-wrap"><table class="ev-install-table ev-class-table" role="table" aria-labelledby="' + _e(section_id) + '-heading"><caption>' + _e(table['caption']) + '</caption><thead role="rowgroup"><tr role="row">' + ''.join('<th scope="col" role="columnheader">' + _e(column) + '</th>' for column in columns) + '</tr></thead><tbody role="rowgroup">' + ''.join(rows) + '</tbody></table></div>'


def render_laminate_classes(guide, page, href):
    sections = guide['sections']
    toc = '<nav class="ev-install-toc" aria-label="Содержание статьи"><h2>В этой статье</h2><ul>' + ''.join('<li><a href="#' + _e(section['id']) + '">' + _e(section['title']) + '</a></li>' for section in sections) + '</ul></nav>'
    article = []
    for section in sections:
        section_id = section['id']
        body = _paragraphs(section.get('paragraphs', []))
        body += ''.join('<div class="ev-class-subsection"><h3>' + _e(item['title']) + '</h3><p>' + _e(item['text']) + '</p></div>' for item in section.get('subsections', []))
        if section.get('table'):
            body += _table(section['table'], section_id)
        if section.get('downloads'):
            body += _downloads(guide['downloads'], page, href)
        body += _paragraphs(section.get('after', []))
        if section.get('links'):
            body += '<ul class="ev-class-sources">' + ''.join('<li><a href="' + _e(item['url']) + '" target="_blank" rel="noopener noreferrer">' + _e(item['label']) + ' <span aria-hidden="true">↗</span></a></li>' for item in section['links']) + '</ul>'
        article.append('<section id="' + _e(section_id) + '" aria-labelledby="' + _e(section_id) + '-heading"><h2 id="' + _e(section_id) + '-heading">' + _e(section['title']) + '</h2>' + body + '</section>')
    related = '<div class="ev-class-related"><a href="' + _e(href('catalog-ru/', page)) + '">Выбрать декор <span aria-hidden="true">↗</span></a><a href="' + _e(href('installation.html', page)) + '">Условия укладки</a><a href="' + _e(href('care.html', page)) + '">Уход за покрытием</a></div>'
    return '<div class="ev-install-guide ev-laminate-guide"><div class="ev-wrap ev-install-layout">' + toc + '<article class="ev-prose ev-install-article">' + ''.join(article) + related + '</article></div></div>'
