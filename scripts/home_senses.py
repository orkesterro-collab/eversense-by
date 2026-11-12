#!/usr/bin/env python3
"""Replace the three full-screen sensory records with one accessible image accordion."""
from html import escape
import re

RECORDS = {
    'ru': ('1002600021', '1016123106', '1016123126'),
    'en': ('1040271676', '1040271681', '1040271686'),
}
CONTENT = {
    'ru': (
        ('Видеть', 'Вы видите дерево', 'Матовая поверхность, натуральные текстуры, естественные декоры.'),
        ('Чувствовать', 'Вы чувствуете дерево', 'Бархатистый рельеф, тепло древесных волокон.'),
        ('Слышать', 'Вы слышите дерево', 'Шелест ветра, шуршание листьев, шорох осенних паутинок.'),
    ),
    'en': (
        ('See', 'You see the wood', 'Matt surface, natural textures, authentic decors.'),
        ('Feel', 'You feel the wood', 'Velvety feel, warmth of wood fibres.'),
        ('Hear', 'You hear the wood', 'The rustle of the wind, the sound of leaves, the whisper of autumn cobwebs.'),
    ),
}


def make_home_senses(source):
    if 'id="ev-senses"' in source:
        return source
    language = 'en' if 'id="rec1040271676"' in source else 'ru'
    records = RECORDS[language]
    sections = []
    images = []
    for record in records:
        match = re.search(r'<div id="rec' + record + r'"\s.*?(?=<div id="rec\d+"\s)', source, re.S)
        if not match:
            return source
        image = re.search(r'data-original="([^"]+\.(?:webp|jpg|png))"', match[0])
        if not image:
            raise ValueError('Sensory record has no original photograph: ' + record)
        sections.append(match)
        images.append(image[1])
    asset_path = images[0].split('original-tilda/')[0]
    label = 'Ощущения от дерева' if language == 'ru' else 'The senses of wood'
    panels = []
    for index, ((short, title, description), record, image) in enumerate(zip(CONTENT[language], records, images)):
        selected = index == 0
        panels.append(f'''<article id="rec{record}" class="ev-sense-panel" data-sense="{index}">
  <img class="ev-sense-image" src="{escape(image, quote=True)}" alt="" loading="lazy" decoding="async" width="1680" height="1120">
  <svg class="ev-sense-curve" viewBox="0 0 800 600" preserveAspectRatio="xMaxYMid slice" aria-hidden="true"><path d="M610 -120C260 60 260 330 710 690"/></svg>
  <div class="ev-sense-copy" id="ev-sense-copy-{index}">
    <h2>{escape(title)}</h2><p>{escape(description)}</p>
  </div>
  <span class="ev-sense-label" aria-hidden="true">{escape(short)}</span>
  <button class="ev-sense-toggle" type="button" aria-label="{escape(title)}" aria-expanded="{str(selected).lower()}" aria-controls="ev-sense-copy-{index}"></button>
</article>''')
    section = ('<section id="ev-senses" class="ev-senses" data-active="0" aria-label="' + label + '">\n' +
               '\n'.join(panels) + '\n</section><!-- /ev-senses -->')
    for index, match in reversed(list(enumerate(sections))):
        source = source[:match.start()] + (section if index == 0 else '') + source[match.end():]
    assets = (f'<link id="ev-senses-css" rel="stylesheet" href="{asset_path}home-senses.css">'
              f'<script id="ev-senses-js" defer src="{asset_path}home-senses.js"></script>')
    return source.replace('</head>', assets + '</head>', 1)
