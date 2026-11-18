"""Render the homepage's wood composition as a responsive text and image block."""
from html import escape
import re


RECORD = re.compile(r'<div id="rec(1002599976|1040271666)"\s[^>]*>\s*'
                    r'<!-- T396 -->.*?<!-- /T396 -->\s*</div>', re.S)
COPY = {
    '1002599976': (
        'Дерево в основе',
        'Основу EVERSENSE делают из волокон берёзы и осины, добавляя немного связующего.',
        'Как и паркет, такой пол помогает сглаживать перепады влажности в помещении.',
    ),
    '1040271666': (
        'Wood at the core',
        'The EVERSENSE core is made from birch and aspen fibres with a small amount of binder.',
        'Like parquet, the flooring helps moderate fluctuations in indoor humidity.',
    ),
}


def make_home_wood(source):
    match = RECORD.search(source)
    if not match:
        return source
    assets = re.search(r'''(?:src|href)=["']((?:\.\./)*assets/)''', source)
    if not assets:
        raise ValueError('Cannot resolve the homepage wood block asset path')
    asset_path = assets[1]
    title, lead, body = map(escape, COPY[match[1]])
    section = f'''<section id="rec{match[1]}" class="r t-rec ev-home-wood" aria-labelledby="ev-home-wood-title">
  <div class="ev-home-wood__copy">
    <h2 id="ev-home-wood-title">{title}</h2>
    <p class="ev-home-wood__lead">{lead}</p>
    <p>{body}</p>
  </div>
  <div class="ev-home-wood__visual">
    <img class="ev-home-wood__photo" src="{asset_path}original-tilda/06315fb1f0a1-Frame_795-min.webp" alt="" width="1680" height="578" loading="lazy" decoding="async">
    <img class="ev-home-wood__logo" src="{asset_path}original-tilda/f1f98a9a41e8-Frame_789.svg" alt="" width="330" height="133" loading="lazy" decoding="async">
  </div>
</section>'''
    source = source[:match.start()] + section + source[match.end():]
    return source.replace('</head>', f'<link rel="stylesheet" href="{asset_path}home-wood.css"></head>', 1)
