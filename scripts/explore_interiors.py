"""Curated, original manufacturer interiors with progressive comparison controls."""

from html import escape


STORIES = [
    {
        'id': 'interior-tone',
        'nav': 'Оттенок дерева',
        'title': 'Один интерьер. Два оттенка дуба.',
        'lead': 'Светлый или более насыщенный? В этой гостиной удобно сравнить близкие декоры: мебель, стены и ракурс остаются теми же.',
        'sample': 'Приложите к обоим образцам ткань дивана или кресла. Посмотрите, какой пол лучше связывает ваши материалы в одну палитру.',
        'variants': [
            ('EL2151', 'Светлее', 'Светлый пол поддерживает мягкую палитру',
             'Взгляните на границу дивана и пола: близкие светлые тона создают спокойное сочетание. На их фоне тёмный стол и дальняя стена выглядят заметнее.'),
            ('EL2152', 'Насыщеннее', 'Древесный оттенок становится выразительнее',
             'Здесь пол сильнее отличается от светлого дивана. Сравните открытый участок перед столом: на большой площади разница между оттенками виднее, чем на маленьком образце.'),
        ],
    },
    {
        'id': 'interior-contrast',
        'nav': 'Светло и темно',
        'title': 'Светлая спальня: фон или контраст?',
        'lead': 'Белёный и более тёмный древесный декор дают разное впечатление даже рядом с одной и той же мебелью.',
        'sample': 'Сравните образец со стеной и плинтусом. Затем отойдите на несколько шагов: важен общий вид, а не только рисунок вблизи.',
        'variants': [
            ('EL1040', 'Светлый фон', 'Пол продолжает светлую палитру',
             'Светлая поверхность близка по тону к стенам и обивке. Древесный рисунок остаётся частью фона, а внимание легче переходит к мебели и растениям.'),
            ('EL2190', 'Контраст', 'Мебель выделяется на древесном фоне',
             'Более тёмный пол подчёркивает силуэт кровати и светлый текстиль. Посмотрите на рисунок у изножья: заметные волокна добавляют ещё один акцент в спокойную комнату.'),
        ],
    },
    {
        'id': 'interior-pattern',
        'nav': 'Дерево и мрамор',
        'title': 'Синие фасады. Два характера пола.',
        'lead': 'Рисунок мрамора и коричневый дуб рядом с одинаковыми фасадами. Здесь меняется не только цвет, но и формат панели.',
        'sample': 'Возьмите с собой образец фасада или столешницы. Сравните, какие рисунки поддерживают друг друга, а какие начинают спорить за внимание.',
        'variants': [
            ('EL1002', 'Мрамор', 'Серый рисунок собирает прохладную палитру',
             'Серый пол перекликается с рисунком фартука и синими фасадами. Заметьте ширину панелей и линии стыков: они тоже участвуют в общем рисунке комнаты.'),
            ('EL2153', 'Дерево', 'Коричневый дуб добавляет тёплый акцент',
             'На фоне синих фасадов древесный оттенок заметно меняет настроение кухни. Сравните не только цвет, но и направленные волокна на открытом участке пола.'),
        ],
    },
]


def render_interiors(page, products, href):
    """Return static stories; optional JS progressively selects exact SKU scenes."""
    by_sku = {product['sku']: product for product in products}

    def e(value):
        return escape(str(value), quote=True)

    def url(target):
        return e(href(target, page))

    pieces = [
        '<div class="ev-interior-stories" data-interior-stories>',
        '<section class="ev-section ev-interior-intro"><div class="ev-wrap">',
        '<nav class="ev-interior-nav" aria-label="Три идеи для интерьера">',
    ]
    for number, story in enumerate(STORIES, 1):
        pieces.append(f'<a href="#{story["id"]}"><span aria-hidden="true">0{number}</span>{e(story["nav"])}<span aria-hidden="true">↓</span></a>')
    pieces.append('</nav><p class="ev-interior-source">Оригинальные изображения производителя. Оттенок и фактуру проверяйте по образцу.</p></div></section>')

    for number, story in enumerate(STORIES, 1):
        story_id = story['id']
        scenes = story['variants']
        skus = [variant[0] for variant in scenes]
        pieces.append(f'<section class="ev-section ev-interior-story" id="{story_id}" data-interior-story aria-labelledby="{story_id}-title"><div class="ev-wrap">')
        pieces.append(f'<header class="ev-interior-heading"><div><span class="ev-eyebrow">0{number} / {e(story["nav"])}</span><h2 id="{story_id}-title">{e(story["title"])}</h2></div><p>{e(story["lead"])}</p></header>')
        pieces.append(f'<div class="ev-interior-controls"><div class="ev-interior-options" data-story-options role="group" aria-label="Выбрать декор: {e(story["nav"])}" hidden>')
        for index, (sku, short_label, _, _) in enumerate(scenes):
            product = by_sku[sku]
            pieces.append(f'<button type="button" data-story-select="{sku}" aria-pressed="{"true" if index == 0 else "false"}" aria-controls="{story_id}-{sku}"><img src="{url(product["productImage"])}" alt="" width="60" height="60" loading="lazy"><span><b>{e(short_label)}</b><span>{sku} · {e(product["name"])}</span></span></button>')
        pieces.append('</div>')
        pieces.append(f'<div class="ev-interior-view" data-story-view-controls role="group" aria-label="Вид изображения: {e(story["nav"])}" hidden><button type="button" data-story-view="room" aria-pressed="true">Интерьер</button><button type="button" data-story-view="detail" aria-pressed="false">Рисунок</button></div></div>')
        pieces.append('<p class="ev-interior-status" data-story-status role="status" aria-live="polite" aria-atomic="true"></p>')

        for sku, _, observation_title, observation in scenes:
            product = by_sku[sku]
            room_alt = f'Интерьер производителя с декором {product["name"]}, {sku}'
            detail_alt = f'Рисунок декора {product["name"]}, {sku}'
            pieces.append(f'<article class="ev-interior-scene" id="{story_id}-{sku}" data-story-scene="{sku}" aria-labelledby="{story_id}-{sku}-title">')
            pieces.append(f'<figure class="ev-interior-photo"><a href="{url(product["canonicalPath"])}" aria-label="Открыть {e(product["name"])}, {sku}"><img data-story-photo src="{url(product["interiorImage"])}" data-room-src="{url(product["interiorImage"])}" data-detail-src="{url(product["productImage"])}" data-room-alt="{e(room_alt)}" data-detail-alt="{e(detail_alt)}" alt="{e(room_alt)}" width="1680" height="1261" loading="lazy"></a><figcaption>{sku} · {e(product["name"])}</figcaption></figure>')
            pieces.append('<div class="ev-interior-reading">')
            pieces.append(f'<span class="ev-eyebrow">{e(product["collectionName"])}</span><h3 id="{story_id}-{sku}-title">{e(product["name"])}</h3><p class="ev-interior-size">{sku} · {product["lengthMM"]} × {product["widthMM"]} × {product["thicknessMM"]} мм</p>')
            pieces.append(f'<div class="ev-interior-observation"><span>Что заметить</span><h4>{e(observation_title)}</h4><p>{e(observation)}</p></div>')
            pieces.append(f'<div class="ev-interior-actions"><a class="ev-button" data-story-product href="{url(product["canonicalPath"])}">Смотреть декор</a><button class="ev-text-link" type="button" data-ev-favorite="{sku}" aria-pressed="false">В избранное</button></div></div></article>')

        pieces.append(f'<div class="ev-interior-next"><p><strong>Проверьте на образце.</strong> {e(story["sample"])}</p><a class="ev-text-link" href="{url("compare.html?items=" + ",".join(skus))}">Сравнить характеристики пары <span aria-hidden="true">↗</span></a></div>')
        if story_id == 'interior-pattern':
            pieces.append(f'<p class="ev-interior-source">Для кухни заранее проверьте условия применения и требования к монтажу. <a href="{url("installation.html")}">Укладка и контакт с водой</a>.</p>')
        pieces.append('</div></section>')

    pieces.append('<section class="ev-section ev-interior-finish"><div class="ev-wrap"><span class="ev-eyebrow">От впечатления к выбору</span><div><h2>Теперь — ваши материалы и ваш свет</h2><p>Выберите два-три декора, сохраните подборку и посмотрите образцы рядом с отделкой своей комнаты. Изображения помогают найти направление; окончательное сочетание складывается дома.</p></div><div class="ev-actions">')
    pieces.append(f'<a href="{url("catalog-ru/")}" class="ev-button">Все 30 декоров</a><a href="{url("choose.html#sample")}" class="ev-text-link">Как оценить образец</a>')
    pieces.append('</div></div></section></div>')
    return ''.join(pieces)
