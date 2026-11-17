"""Build the source-backed, magazine-style history article.

The editorial HTML is kept separately from the site shell so copy edits survive
regeneration. No remote requests or publication are performed by this builder.
"""
import json


def write_history_page(root, footer_html):
    title = 'Наша история: от EGGER к EVERSENSE'
    description = ('Как десятилетия работы с деревом привели к EVERSENSE: '
                   'история EGGER, развитие завода в Гагарине и технологии ламината '
                   'в обратной хронологии с официальными фотографиями.')
    url = 'https://eversense.by/history.html'
    body = (root / 'content/history-article.html.in').read_text(encoding='utf-8')
    schema = {'@context': 'https://schema.org', '@type': 'Article',
              'headline': title, 'description': description,
              'mainEntityOfPage': url, 'inLanguage': 'ru',
              'image': 'https://eversense.by/assets/history/gagarin.jpg'}
    html = f'''<!doctype html>
<html lang="ru" data-buyer-static="true"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#343333"><meta name="robots" content="noindex,nofollow">
<title>{title} — EVERSENSE Беларусь</title><meta name="description" content="{description}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article"><meta property="og:locale" content="ru_RU">
<meta property="og:title" content="{title}"><meta property="og:description" content="{description}">
<meta property="og:url" content="{url}"><meta property="og:image" content="https://eversense.by/assets/history/gagarin.jpg">
<link rel="stylesheet" href="assets/vendor/fonts/manrope.css">
<link rel="stylesheet" href="assets/buyer.css" data-ev-buyer-css>
<link rel="stylesheet" href="assets/history.css?v=20261117">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
<script src="assets/products-data.js" defer></script>
<script src="assets/buyer-core.js" defer></script>
<script src="assets/prices.js" defer></script>
<script src="assets/buyer.js" defer></script>
<script src="assets/history.js?v=20261117" defer></script>
</head><body class="ev-buyer ev-history-page" data-buyer-page="history">
<a class="ev-skip-link" href="#main">Перейти к содержанию</a>
<div class="reading-progress" aria-hidden="true"></div>
<main id="main"><div class="wrap">
<div class="history-masthead"><nav aria-label="Хлебные крошки"><a href="index.html">Главная</a><span aria-hidden="true">/</span><span>Наша история</span></nav><span class="eyebrow">Материалы · Люди · Технологии</span></div>
{body}
</div></main>{footer_html}
</body></html>
'''
    (root / 'history.html').write_text(html, encoding='utf-8')
