"""Progressively enhanced manufacturer layer illustration for the buyer guide."""
from html import escape


LAYERS = [
    {
        'id': 'overlay', 'label': 'Защита', 'title': 'Защитный слой',
        'image': '603494132a85-1_overlay-min.webp',
        'role': 'То, с чем соприкасается повседневная жизнь.',
        'body': 'Оверлей находится над рисунком и принимает контакт с обувью, мебелью и уборкой. Стойкость поверхности не отменяет защиты от песка, острых предметов и перемещения тяжёлой мебели.',
        'look': 'Посмотрите на образец под углом: так легче заметить рельеф и характер блеска. Оцените поверхность рукой — фотография не передаёт это ощущение.',
        'link': 'care.html', 'link_label': 'Как сохранить поверхность',
    },
    {
        'id': 'decor', 'label': 'Рисунок', 'title': 'Декоративный слой',
        'image': 'c9f879219a4a-2_paper-min.webp',
        'role': 'Оттенок, волокна и настроение комнаты.',
        'body': 'Декоративный слой задаёт вид поверхности. Именно он передаёт рисунок древесины, мрамора или однотонного декора. В древесных декорах EVERSENSE рисунок создаёт декоративный слой.',
        'look': 'Разложите рядом несколько панелей. На большой площади важны не только цвет, но и чередование светлых и тёмных участков, выразительность рисунка.',
        'link': 'choose.html#sample', 'link_label': 'Что проверить на образце',
    },
    {
        'id': 'board', 'label': 'Основа', 'title': 'Древесная плита',
        'image': '9404692d9a29-3_board-min.webp',
        'role': 'Тело панели, на котором держится конструкция.',
        'body': 'Плита работает вместе с остальными слоями и соединениями. Результат после укладки зависит от всей системы пола: самой панели, основания, подложки и правильной сборки.',
        'look': 'Уточните у мастера, как он проверит ровность и влажность основания. Качественное покрытие не заменяет подготовку пола под ним.',
        'link': 'installation.html#subfloor', 'link_label': 'Как подготовить основание',
    },
    {
        'id': 'balance', 'label': 'Баланс', 'title': 'Стабилизирующий слой',
        'image': '9ecaa5080584-4_balancer-min.webp',
        'role': 'Нижняя часть общей конструкции.',
        'body': 'Нижний слой дополняет конструкцию и помогает сохранять форму панели. Все четыре слоя работают вместе; требования к монтажу относятся к покрытию целиком.',
        'look': 'Подложку подбирают отдельно по требованиям инструкции. Стабилизирующий слой внутри панели не заменяет предусмотренные материалы для монтажа.',
        'link': 'installation.html#underlay', 'link_label': 'Подложка и защита от влаги',
    },
]


def render_layers(page, href):
    """Return markup only; caller includes explore-product.css and .js once.

    Without JavaScript, controls are ordinary fragment links and all four
    explanations remain visible. JavaScript upgrades them to keyboard tabs.
    """
    e = lambda value: escape(str(value), quote=True)
    images = ''.join(
        '<img data-layer-image="' + layer['id'] + '" src="' +
        e(href('assets/original-tilda/' + layer['image'], page)) +
        '" alt="" width="1680" height="944" loading="lazy">'
        for layer in reversed(LAYERS)
    )
    controls = ''.join(
        '<a id="ev-layer-control-' + layer['id'] + '" data-layer-control="' +
        layer['id'] + '" href="#ev-layer-panel-' + layer['id'] + '">' +
        '<span class="ev-layer-number" aria-hidden="true">0' + str(i + 1) + '</span>' +
        '<span>' + e(layer['label']) + '</span></a>'
        for i, layer in enumerate(LAYERS)
    )
    panels = ''.join(
        '<div class="ev-layer-panel" id="ev-layer-panel-' + layer['id'] +
        '" data-layer-panel="' + layer['id'] + '">' +
        '<div class="ev-layer-copy"><span class="ev-layer-kicker">' +
        e(layer['role']) + '</span><h3>' + e(layer['title']) + '</h3><p>' +
        e(layer['body']) + '</p></div><div class="ev-layer-tip"><h4>Что это значит для вас</h4><p>' +
        e(layer['look']) + '</p><a class="ev-text-link" href="' +
        e(href(layer['link'], page)) + '">' + e(layer['link_label']) +
        ' <span aria-hidden="true">→</span></a></div></div>'
        for layer in LAYERS
    )
    return '''<div class="ev-layer-explorer" data-layer-explorer>
<p class="ev-layer-intro">Посмотрите, что скрывается под рисунком пола. У каждого слоя своя задача — и своё значение для вашего выбора.</p>
<figure class="ev-layer-figure"><div class="ev-layer-stage" role="img" aria-label="Конструкция сверху вниз: защитный слой, декор, древесная плита, стабилизирующий слой">''' + images + '''</div>
<figcaption>Схема конструкции EVERSENSE. Толщина слоёв показана условно.</figcaption></figure>
<div class="ev-layer-controls" data-layer-controls aria-label="Изучить слои панели">''' + controls + '''</div>
<div class="ev-layer-panels">''' + panels + '''</div></div>'''
