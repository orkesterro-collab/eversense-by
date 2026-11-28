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


def _diagram_link(diagram, page, href):
    src = _e(href(diagram['src'], page))
    alt = _e(diagram['alt'])
    width = int(diagram['width'])
    height = int(diagram['height'])
    return (
        f'<a href="{src}" target="_blank" rel="noopener noreferrer" aria-label="Увеличить: {alt}">'
        f'<img src="{src}" alt="{alt}" width="{width}" height="{height}" loading="lazy" decoding="async"></a>'
    )


def _extras(items):
    if not items:
        return ''
    notes = ''.join('<p><mark>' + _e(item) + '</mark></p>' for item in items)
    return '<div class="ev-install-extras"><span>Дополнение сайта</span>' + notes + '</div>'


def _illustrated(group, copy, page, href):
    figures = []
    diagrams = group.get('diagrams', [])
    if group.get('layers'):
        layers = ''.join('<li><i aria-hidden="true"></i><span>' + _e(layer) + '</span></li>' for layer in group['layers'])
        substrate = 'wood' if group['substrate'] == 'wood' else 'mineral'
        figures.append(
            '<figure class="ev-install-section-cut"><figcaption>Слои сверху вниз</figcaption>'
            f'<ol class="ev-install-layers ev-install-layers--{substrate}" role="list">{layers}</ol></figure>'
        )
    for diagram in diagrams:
        caption = diagram.get('caption')
        if not caption and len(diagrams) > 1:
            caption = diagram['alt']
        caption_html = '<figcaption>' + _e(caption) + '</figcaption>' if caption else ''
        figures.append('<figure>' + _diagram_link(diagram, page, href) + caption_html + '</figure>')
    if not figures:
        return copy
    gallery = '<div class="ev-install-figures">' + ''.join(figures) + '</div>'
    if not copy:
        return gallery
    if len(diagrams) > 1 or any(diagram['width'] > 3 * diagram['height'] for diagram in diagrams):
        return '<div class="ev-install-sequence">' + copy + gallery + '</div>'
    return '<div class="ev-install-illustrated">' + gallery + '<div class="ev-install-copy">' + copy + '</div></div>'


def _block(block, section_title, page, href):
    title = '<h3>' + _e(block['title']) + '</h3>' if block.get('title') else ''
    copy = ''.join('<p>' + _e(value) + '</p>' for value in block.get('paragraphs', []))
    copy += _list(block.get('bullets', []))
    body = _illustrated(block, copy, page, href)
    body += _table(block.get('table', {}), block.get('title', section_title))
    return '<div class="ev-install-block">' + title + body + _extras(block.get('extras', [])) + '</div>'


def _assembly_methods(methods, page, href):
    if not methods:
        return ''
    navigation = '<nav class="ev-install-method-nav" aria-label="Способы сборки CLIC it!">' + ''.join(
        '<a href="#' + _e(method['id']) + '">Способ ' + _e(method['code']) + '</a>'
        for method in methods
    ) + '</nav>'
    result = []
    for method in methods:
        method_id = _e(method['id'])
        title = 'Способ ' + _e(method['code']) + '. ' + _e(method['title'])
        images = [_diagram_link(diagram, page, href) for diagram in method['diagrams']]
        steps = '<ol class="ev-install-method-steps">' + ''.join('<li>' + _e(step) + '</li>' for step in method['steps']) + '</ol>'
        figure = '<figure class="ev-install-method-figure"><div class="ev-install-diagrams">' + ''.join(images) + '</div><figcaption>' + _e(method['caption']) + '</figcaption></figure>'
        layout = _block(method['layout'], title, page, href) if method.get('layout') else ''
        note = '<p class="ev-install-method-note">' + _e(method['note']) + '</p>' if method.get('note') else ''
        result.append('<div class="ev-install-method" id="' + method_id + '" role="group" aria-labelledby="' + method_id + '-heading"><h3 id="' + method_id + '-heading">' + title + '</h3><p>' + _e(method['description']) + '</p>' + layout + steps + figure + note + '</div>')
    return navigation + '<p class="ev-install-diagram-help">На схемах сохранены обозначения производителя. Нажмите на рисунок, чтобы открыть его крупнее в новой вкладке.</p>' + ''.join(result)


def _pros_cons(section):
    groups = []
    for key, title in [('pros', 'Преимущества'), ('cons', 'Ограничения')]:
        if section.get(key):
            groups.append('<div class="ev-install-tradeoffs-group"><h3>' + title + '</h3>' + _list(section[key]) + '</div>')
    return '<div class="ev-install-tradeoffs">' + ''.join(groups) + '</div>' if groups else ''


def _installation_hub(guide, page, href):
    assets = _e(href('assets/installation/hub/', page))
    arrow = '<span class="ev-hub-arrow" aria-hidden="true">→</span>'
    methods = []
    for method in guide['methods']:
        key = _e(method['id'])
        methods.append(f'''
<a class="ev-hub-method" id="{key}" href="{_e(href(method['url'], page))}" aria-labelledby="{key}-heading">
  <div class="ev-wrap ev-hub-row">
    <img class="ev-hub-img" src="{assets}installation-{key}.webp" alt="" width="478" height="291" decoding="async">
    <div class="ev-hub-copy">
      <h2 id="{key}-heading">{_e(method['title'])}</h2>
      <p>{_e(method['description'])}</p>
      <span class="ev-hub-link">{_e(method['label'])} {arrow}</span>
    </div>
  </div>
</a>''')
    comparison = guide['comparison']
    figures = ''.join(f'''
    <figure>
      <img src="{assets}{_e(section['image'])}" alt="{_e(section['alt'])}" width="498" height="144" loading="lazy" decoding="async">
      <figcaption>{_e(section['caption'])}</figcaption>
    </figure>''' for section in comparison['sections'])
    care = guide['care']
    return f'''<div class="ev-hub">
<div class="ev-wrap ev-hub-title"><h1>{_e(guide['title'])}</h1></div>
<nav class="ev-install-navigation ev-hub-nav" aria-label="Инструкции и сравнение">
{''.join(methods)}
<a class="ev-hub-compare" id="methods" href="{_e(href(comparison['url'], page))}" aria-labelledby="methods-heading methods-link">
  <div class="ev-wrap ev-hub-compare-inner">
    <h2 id="methods-heading">{_e(comparison['title'])}</h2>
    <div class="ev-hub-figures">{figures}</div>
    <span class="ev-hub-link" id="methods-link">{_e(comparison['label'])} {arrow}</span>
  </div>
</a>
</nav>
<a class="ev-hub-care" href="{_e(href(care['url'], page))}" aria-labelledby="care-heading">
  <div class="ev-wrap ev-hub-row">
    <img class="ev-hub-img" src="{assets}installation-care.webp" alt="" width="368" height="228" loading="lazy" decoding="async">
    <div class="ev-hub-copy"><h2 id="care-heading">{_e(care['title'])} {arrow}</h2></div>
  </div>
</a>
</div>'''


def render_installation_guide(guide, page, href, literal_html=None):
    """Return the article body using the site's existing relative-link helper.

    Sections optionally group text and drawings into blocks. Extras are separate
    editorial additions to a guide with a factory_pdf source.
    Every text value is escaped; editorial content cannot inject markup.
    """
    if page == 'installation.html':
        return _installation_hub(guide, page, href)

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
    contents = guide.get('contents', sections)
    toc_list = '<ul>' + ''.join(
        '<li><a href="#' + _e(section['id']) + '">' + _e(section.get('nav_title', section['title'])) + '</a></li>'
        for section in contents
    ) + '</ul>'
    toc_body = '<h2>На этой странице</h2>' + toc_list
    source = ''
    guide_css = 'ev-install-guide'
    if guide.get('factory_pdf'):
        guide_css += ' ev-install-guide--factory'
        pdf = _link(guide['factory_pdf'], page, href, 'ev-install-source-link')
        source = '<div class="ev-install-source">' + pdf + '</div>'
        toc_body = '<details open><summary>Содержание инструкции</summary>' + toc_list + '</details>'
    toc = '<nav class="ev-install-toc" aria-label="Содержание статьи">' + toc_body + '</nav>' if contents else ''

    article = []
    for section in sections:
        section_id = section['id']
        section_body = ''.join('<p>' + _e(paragraph) + '</p>' for paragraph in section.get('paragraphs', []))
        section_body += _notice(section.get('notice'))
        section_body += _list(section.get('bullets', []))
        section_body = _illustrated(section, section_body, page, href)
        section_body += _table(section.get('table', {}), section['title'])
        section_body += _steps(section.get('steps', []))
        section_body += ''.join(_block(block, section['title'], page, href) for block in section.get('blocks', []))
        section_body += _assembly_methods(section.get('assembly_methods', []), page, href)
        section_body += _pros_cons(section)
        section_body += _extras(section.get('extras', []))
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

    article_class = 'ev-prose ev-install-article'
    if literal_html is not None:
        article = [literal_html]
        article_class += ' ev-literal-content'

    intro = navigation + source + _notice(guide.get('notice'), 'h2', True) + checks
    return '<div class="' + guide_css + '"><div class="ev-wrap ev-install-intro">' + intro + '</div><div class="ev-wrap ev-install-layout">' + toc + '<article class="' + article_class + '">' + ''.join(article) + '</article></div>' + related + '</div>'
