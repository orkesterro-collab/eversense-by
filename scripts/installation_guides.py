"""Render EVERSENSE installation articles from structured editorial content.

The shared buyer-page builder supplies the title, hero, header and footer.
This module deliberately contains no product requirements or installation rules.
"""
from html import escape


def _e(value):
    return escape(str(value), quote=True)


def _list(items, css=''):
    if not items:
        return ''
    attr = f' class="{_e(css)}"' if css else ''
    return '<ul' + attr + '>' + ''.join('<li>' + _e(item) + '</li>' for item in items) + '</ul>'


def _notice(notice, heading='h3', prominent=False):
    if not notice:
        return ''
    css = 'ev-install-notice' + (' ev-install-notice--prominent' if prominent else '')
    title = '<' + heading + '>' + _e(notice['title']) + '</' + heading + '>' if notice.get('title') else ''
    text = '<p>' + _e(notice['text']) + '</p>' if notice.get('text') else ''
    return '<aside class="' + css + '">' + title + text + '</aside>'


def _link(item, page, href, css='', current=False):
    target = str(item.get('url', ''))
    is_external = target.startswith(('https://', 'http://'))
    attrs = ' class="' + _e(css) + '"' if css else ''
    if current:
        attrs += ' aria-current="page"'
    if is_external:
        attrs += ' target="_blank" rel="noopener noreferrer"'
    return '<a href="' + _e(href(target, page)) + '"' + attrs + '>' + _e(item.get('label', '')) + '</a>'


def _table(table, title):
    columns = table.get('columns', [])
    rows = table.get('rows', [])
    if not columns or not rows:
        return ''
    head = '<thead role="rowgroup"><tr role="row">' + ''.join(
        '<th scope="col" role="columnheader">' + _e(column) + '</th>' for column in columns
    ) + '</tr></thead>'
    body = []
    for row in rows:
        cells = []
        for index, value in enumerate(row):
            if index == 0:
                cells.append('<th scope="row" role="rowheader">' + _e(value) + '</th>')
            else:
                label = columns[index] if index < len(columns) else ''
                cells.append('<td role="cell"><span class="ev-install-table-label" aria-hidden="true">' + _e(label) + '</span><span>' + _e(value) + '</span></td>')
        body.append('<tr role="row">' + ''.join(cells) + '</tr>')
    caption = '<caption>' + _e(table['caption']) + '</caption>' if table.get('caption') else ''
    return '<div class="ev-install-table-wrap"><table class="ev-install-table" role="table" aria-label="' + _e(title) + '">' + caption + head + '<tbody role="rowgroup">' + ''.join(body) + '</tbody></table></div>'


def _steps(steps):
    if not steps:
        return ''
    result = []
    for step in steps:
        title = '<h3>' + _e(step['title']) + '</h3>' if step.get('title') else ''
        text = '<p>' + _e(step['text']) + '</p>' if step.get('text') else ''
        result.append('<li>' + title + text + _list(step.get('bullets', [])) + '</li>')
    return '<ol class="ev-install-steps">' + ''.join(result) + '</ol>'


def _pros_cons(section):
    groups = []
    for key, title in [('pros', 'Преимущества'), ('cons', 'Ограничения')]:
        if section.get(key):
            groups.append('<div class="ev-install-tradeoffs-group"><h3>' + title + '</h3>' + _list(section[key]) + '</div>')
    return '<div class="ev-install-tradeoffs">' + ''.join(groups) + '</div>' if groups else ''


def render_installation_guide(guide, page, href):
    """Return the article body using the site's existing relative-link helper.

    Expected fields are navigation, quick_checks, notice, sections and related.
    Sections accept paragraphs, bullets, steps, table, notice, links, pros and cons.
    Every text value is escaped; editorial content cannot inject markup.
    """
    navigation = ''
    if guide.get('navigation'):
        navigation = '<nav class="ev-install-navigation" aria-label="Инструкции и сравнение">' + ''.join(
            _link(item, page, href, current=item.get('url', '').lstrip('/') == page.lstrip('/'))
            for item in guide['navigation']
        ) + '</nav>'

    checks = ''
    if guide.get('quick_checks'):
        checks = '<dl class="ev-install-checks">' + ''.join(
            '<div><dt>' + _e(check.get('label', '')) + '</dt><dd>' + _e(check.get('value', '')) + '</dd></div>'
            for check in guide['quick_checks']
        ) + '</dl>'

    sections = guide.get('sections', [])
    toc = '<nav class="ev-install-toc" aria-label="Содержание статьи"><h2>На этой странице</h2><ul>' + ''.join(
        '<li><a href="#' + _e(section['id']) + '">' + _e(section['title']) + '</a></li>'
        for section in sections
    ) + '</ul></nav>' if sections else ''

    article = []
    for section in sections:
        section_id = section['id']
        section_body = ''.join('<p>' + _e(paragraph) + '</p>' for paragraph in section.get('paragraphs', []))
        section_body += _notice(section.get('notice'))
        section_body += _list(section.get('bullets', []))
        section_body += _table(section.get('table', {}), section['title'])
        section_body += _steps(section.get('steps', []))
        section_body += _pros_cons(section)
        if section.get('links'):
            section_body += '<div class="ev-install-links">' + ''.join(
                _link(item, page, href, 'ev-install-text-link') for item in section['links']
            ) + '</div>'
        article.append('<section id="' + _e(section_id) + '" aria-labelledby="' + _e(section_id) + '-heading"><h2 id="' + _e(section_id) + '-heading">' + _e(section['title']) + '</h2>' + section_body + '</section>')

    related = ''
    if guide.get('related'):
        related = '<section class="ev-install-related"><div class="ev-wrap"><h2>Дальше об укладке</h2><nav aria-label="Другие материалы об укладке">' + ''.join(
            _link(item, page, href) for item in guide['related']
        ) + '</nav></div></section>'

    intro = navigation + _notice(guide.get('notice'), 'h2', True) + checks
    return '<div class="ev-install-guide"><div class="ev-wrap ev-install-intro">' + intro + '</div><div class="ev-wrap ev-install-layout">' + toc + '<article class="ev-prose ev-install-article">' + ''.join(article) + '</article></div>' + related + '</div>'
