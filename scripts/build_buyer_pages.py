#!/usr/bin/env python3
"""Build small, readable buyer pages around the existing EVERSENSE catalog.

Run from any directory. Product facts come from extract_products.py, editorial
content from content/buyer-guides.json. No third-party build dependencies.
"""
from pathlib import Path
from html import escape
import json
import posixpath

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'assets/products-data.json').read_text())
PRODUCTS = DATA if isinstance(DATA, list) else DATA['products']
PRODUCTS.sort(key=lambda p: (['nature','luxury','minimal'].index(p['collectionID']), int(p['sku'][2:])))
GUIDES = json.loads((ROOT / 'content/buyer-guides.json').read_text())
VERSION = '20261110b'
COLLECTIONS = [
    ('nature', 'Природная эстетика', 'Спокойные древесные оттенки и выразительные рисунки дуба.'),
    ('luxury', 'Тихая роскошь', 'Натуральные и глубокие тона для интерьера с характером.'),
    ('minimal', 'Новый минимализм', 'Светлое дерево, однотонные поверхности и рисунок мрамора.'),
]
COLLECTION_PATHS = {c: next(p['canonicalPath'].rsplit('/', 2)[0] + '/' for p in PRODUCTS if p['collectionID'] == c) for c, _, _ in COLLECTIONS}

def e(value):
    return escape(str(value), quote=True)

def href(target, page):
    if target.startswith(('https://', 'http://', 'tel:', 'mailto:', '#')):
        return target
    target = target.lstrip('/')
    result = posixpath.relpath(target or '.', posixpath.dirname(page) or '.')
    if target.endswith('/') and not result.endswith('/'):
        result += '/'
    return result

def link(label, target, page, cls='', extra=''):
    return f'<a href="{e(href(target, page))}"' + (f' class="{e(cls)}"' if cls else '') + (f' {extra}' if extra else '') + f'>{label}</a>'

def actions(page):
    return '<div class="ev-actions">' + link('Избранное (<span data-favorites-count>0</span>)', 'favorites.html', page, 'ev-text-link') + link('Сравнение (<span data-compare-count>0</span>)', 'compare.html', page, 'ev-text-link', 'data-compare-link') + link('Рассчитать упаковки', 'calculator.html', page, 'ev-text-link') + '</div>'

def footer(page):
    groups = [
        ('Выбрать и купить', [('Все декоры', 'catalog-ru/'), ('Помощь с выбором', 'choose.html'), ('Интерьеры', 'projects.html'), ('Калькулятор', 'calculator.html'), ('Где купить', 'where-to-buy.html'), ('Контакты', 'contacts.html')]),
        ('Полезно знать', [('О продукте', 'about.html'), ('Укладка и тёплый пол', 'installation.html'), ('Уход', 'care.html'), ('Гарантия', 'warranty.html'), ('Ответы на вопросы', 'faq.html'), ('Документы', 'downloads.html')]),
    ]
    return '<footer class="ev-footer"><div class="ev-wrap"><div>' + link('EVERSENSE', 'index.html', page, 'ev-footer-brand') + '<p>Коллекция ощущений. Напольные покрытия на древесной основе.</p><p>Представитель в Беларуси — ООО «Флорсток».<br>УНП 192608003<br>220062, г. Минск, пр. Победителей, д. 129, пом. 358</p><p><a href="tel:+375296713971">+375 29 671-39-71</a></p></div>' + ''.join('<div><h2>'+title+'</h2><nav aria-label="'+title+'">'+''.join(link(label, url, page) for label, url in items)+'</nav></div>' for title, items in groups) + '<div class="ev-footer-bottom"><span>© EVERSENSE · Беларусь</span>'+link('Все страницы', 'sitemap.html', page)+link('Конфиденциальность', 'privacy.html', page)+'</div></div></footer>'

def write_page(page, title, lead, body, page_type='', collection='', hero_actions='', structured=None):
    canonical = 'https://eversense.by/' + (page[:-10] if page.endswith('index.html') else page)
    schema = structured or {'@context':'https://schema.org','@type':'WebPage','name':title,'description':lead,'url':canonical,'inLanguage':'ru'}
    html = f'''<!doctype html>
<html lang="ru" data-buyer-static="true"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#262b29"><meta name="robots" content="noindex,nofollow">
<title>{e(title)} — EVERSENSE Беларусь</title><meta name="description" content="{e(lead)}">
<link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:locale" content="ru_RU"><meta property="og:title" content="{e(title)} — EVERSENSE"><meta property="og:description" content="{e(lead)}"><meta property="og:url" content="{canonical}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="{href('assets/buyer.css',page)}?v={VERSION}" data-ev-buyer-css>
<script type="application/ld+json">{json.dumps(schema,ensure_ascii=False).replace('<',chr(92)+'u003c')}</script>
<script src="{href('assets/products-data.js',page)}?v={VERSION}" defer></script>
<script src="{href('assets/buyer-core.js',page)}?v={VERSION}" defer></script>
<script src="{href('assets/prices.js',page)}?v={VERSION}" defer></script>
<script src="{href('assets/buyer.js',page)}?v={VERSION}" defer></script>
</head><body class="ev-buyer" data-buyer-page="{e(page_type)}" data-collection="{e(collection)}">
<a href="#main" class="ev-skip-link">Перейти к содержанию</a>
<main id="main"><section class="ev-hero"><div class="ev-wrap"><nav class="ev-breadcrumb" aria-label="Хлебные крошки">{link('Главная','index.html',page)}<span aria-hidden="true">/</span><span>{e(title)}</span></nav><span class="ev-eyebrow">EVERSENSE · Коллекция ощущений</span><h1>{e(title)}</h1><p class="ev-lead">{e(lead)}</p>{hero_actions}</div></section>
{body}</main>{footer(page)}
<noscript><div class="ev-wrap ev-note">Для расчёта, фильтров, избранного и сравнения включите JavaScript. Страницы декоров и полезные материалы доступны по обычным ссылкам.</div></noscript>
</body></html>'''
    path = ROOT / page
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html + '\n')

def card(p, page):
    return f'''<article class="ev-card" data-product="{p['sku']}"><a class="ev-card-image" href="{e(href(p['canonicalPath'],page))}"><img src="{e(href(p['productImage'],page))}" alt="{e(p['name'])}" width="640" height="500" loading="lazy"><img class="ev-card-interior" src="{e(href(p['interiorImage'],page))}" alt="" width="640" height="500" loading="lazy"></a><div class="ev-card-body"><span class="ev-sku">{p['sku']}</span><h2 class="ev-card-title">{link(e(p['name']),p['canonicalPath'],page)}</h2><p class="ev-card-meta">{e(p['collectionName'])} · {p['lengthMM']} × {p['widthMM']} мм</p><div class="ev-price-box" data-buyer-price="{p['sku']}"><span class="ev-price-pending">Цена уточняется</span></div><div class="ev-card-actions"><button type="button" class="ev-button" data-ev-favorite="{p['sku']}" aria-pressed="false">В избранное</button><button type="button" class="ev-button" data-ev-compare="{p['sku']}" aria-pressed="false">Сравнить</button></div></div></article>'''

def field(label, name, options, value=''):
    return '<div class="ev-field"><label for="ev-'+name+'">'+label+'</label><select id="ev-'+name+'" name="'+name+'">'+''.join('<option value="'+e(v)+'"'+(' selected' if v==value else '')+'>'+e(t)+'</option>' for v,t in options)+'</select></div>'

TONE = [('', 'Все оттенки'), ('light', 'Светлые'), ('natural', 'Натуральные'), ('gray', 'Серые'), ('brown', 'Коричневые'), ('beige', 'Бежевые')]
DESIGN = [('', 'Любой рисунок'), ('wood', 'Дерево'), ('stone', 'Мрамор'), ('plain', 'Однотонный')]

def catalogs():
    for collection, title, lead, page in [('', 'Каталог декоров', '30 декоров EVERSENSE. Сравните рисунок, формат и цену, сохраните понравившиеся варианты и рассчитайте количество упаковок.', 'catalog-ru/index.html')] + [(c,t,d,COLLECTION_PATHS[c].lstrip('/')+'index.html') for c,t,d in COLLECTIONS]:
        items = [p for p in PRODUCTS if not collection or p['collectionID']==collection]
        nav = '<nav class="ev-inline-nav" aria-label="Коллекции">'+link('Все декоры', 'catalog-ru/', page, extra='aria-current="page"' if not collection else '')+''.join(link(t, COLLECTION_PATHS[c], page, extra='aria-current="page"' if c==collection else '') for c,t,_ in COLLECTIONS)+'</nav>'
        filters = '<form id="ev-catalog-filters" class="ev-toolbar" role="search"><div class="ev-filter-row"><div class="ev-field"><label for="ev-q">Поиск по названию или артикулу</label><input id="ev-q" name="q" type="search" placeholder="Например, EL1052 или дуб" autocomplete="off"></div>'
        if not collection:
            filters += field('Коллекция','collection',[('','Все коллекции')]+[(c,t) for c,t,_ in COLLECTIONS])
        filters += field('Оттенок','tone',TONE)+field('Рисунок','design',DESIGN)+field('Порядок','sort',[('','По коллекциям'),('name','По названию'),('price-up','Сначала дешевле'),('price-down','Сначала дороже')])+'</div><div class="ev-actions"><p id="ev-result-count" class="ev-count" role="status">Найдено декоров: '+str(len(items))+'</p><button type="button" class="ev-text-link" data-reset-filters>Сбросить фильтры</button></div></form>'
        body = '<section class="ev-section"><div class="ev-wrap">'+nav+filters+'<div class="ev-grid" id="ev-catalog-results">'+''.join(card(p,page) for p in items)+'</div></div></section><section class="ev-section"><div class="ev-wrap"><p class="ev-note">Оттенок на экране зависит от освещения и настроек устройства. Перед покупкой посмотрите реальный образец. Наличие нужного количества уточняйте у продавца.</p>'+link('Помочь с выбором', 'choose.html', page,'ev-button')+'</div></section>'
        write_page(page,title,lead,body,'catalog',collection,actions(page))

def finder(page):
    return '<section class="ev-section" id="finder"><div class="ev-wrap"><span class="ev-eyebrow">Три ориентира для начала</span><h2>Сузим круг выбора</h2><form id="ev-finder"><div class="ev-filter-row">'+field('Комната','room',[('living','Гостиная'),('bedroom','Спальня'),('kitchen','Кухня'),('hall','Прихожая')])+field('Оттенок','tone',TONE)+field('Рисунок','design',DESIGN)+'</div><button class="ev-button ev-button--primary" type="submit">Показать декоры</button></form><div id="ev-finder-results" class="ev-section" tabindex="-1" hidden></div></div></section>'

def guides():
    for key, page in [('product','about.html'),('choose','choose.html'),('faq','faq.html'),('installation','installation.html'),('care','care.html'),('warranty','warranty.html'),('downloads','downloads.html')]:
        g = GUIDES[key]
        toc = '<aside class="ev-toc"><strong>На этой странице</strong><ul>'+''.join('<li>'+link(e(s['title']),'#'+s['id'],page)+'</li>' for s in g['sections'])+'</ul></aside>'
        prose = ''
        for s in g['sections']:
            prose += '<section id="'+s['id']+'"><h2>'+e(s['title'])+'</h2>'+''.join('<p>'+e(t)+'</p>' for t in s.get('body',[]))
            if s.get('bullets'):
                prose += '<ul>'+''.join('<li>'+e(t)+'</li>' for t in s['bullets'])+'</ul>'
            for f in s.get('faqs',[]):
                target = None
                q = f['q'].lower()
                if 'упаковок' in q: target = ('Рассчитать упаковки', 'calculator.html')
                elif 'образец' in q: target = ('Найти магазин', 'where-to-buy.html')
                elif 'проблема' in q or 'сохранить' in q or 'коммерческ' in q: target = ('Гарантия и обращение', 'warranty.html')
                elif any(w in q for w in ['мыть','паровую','отциклевать','мебели','песка','животные']): target = ('Правила ухода', 'care.html')
                elif any(w in q for w in ['монтаж','подлож','зазор','кухню','расклад','ванной','кухни','тёплый']): target = ('Укладка и условия применения', 'installation.html')
                elif 'коллекц' in q or 'цвет' in q: target = ('Помощь с выбором', 'choose.html')
                else: target = ('Подробнее о продукте', 'about.html')
                prose += '<details><summary>'+e(f['q'])+'</summary><div><p>'+e(f['a'])+'</p>'+link(target[0],target[1],page,'ev-text-link')+'</div></details>'
            for l in s.get('links',[]):
                prose += link(e(l['label'])+' <span aria-hidden="true">↗</span>',l['url'],page,'ev-document', 'target="_blank" rel="noopener noreferrer"' if l['url'].startswith('https://') else '')
            if s['id'] in COLLECTION_PATHS:
                prose += link('Смотреть коллекцию',COLLECTION_PATHS[s['id']],page,'ev-text-link')
            prose += '</section>'
        extra = finder(page) if key=='choose' else ''
        if key=='product':
            p = PRODUCTS[0]
            extra = '<section class="ev-section"><div class="ev-wrap ev-article-visual"><img src="'+e(href(p['interiorImage'],page))+'" alt="'+e(p['name'])+' в интерьере" width="900" height="650"><div><span class="ev-eyebrow">Дерево · Мрамор · Однотонные декоры</span><h2>Три коллекции.<br>Ваш характер дома.</h2><p class="ev-lead">Выберите настроение, затем оцените материал вживую. Разница видна в рисунке, оттенке и формате.</p>'+link('Посмотреть все декоры','catalog-ru/',page,'ev-button')+'</div></div></section>'
        body = extra+'<section class="ev-section"><div class="ev-wrap ev-article-layout">'+toc+'<div class="ev-prose">'+prose+'</div></div></section><section class="ev-section"><div class="ev-wrap ev-favorites-bar"><p>Остались вопросы по вашему помещению или артикулу?</p><div class="ev-actions">'+link('Уточнить у представителя','contacts.html',page,'ev-button ev-button--primary')+link('Выбрать декор','catalog-ru/',page,'ev-text-link')+'</div></div></section>'
        write_page(page,g['title'],g['lead'],body,key,hero_actions='<div class="ev-actions">'+link('Каталог декоров','catalog-ru/',page,'ev-button ev-button--primary')+link('Где посмотреть образец','where-to-buy.html',page,'ev-button')+'</div>')

def tools_pages():
    page = 'calculator.html'
    opts = [(p['sku'],p['sku']+' · '+p['name']) for p in PRODUCTS]
    body = '<section class="ev-section"><div class="ev-wrap ev-calculator"><form id="ev-calc-form" novalidate>'+field('Декор','sku',opts)+'<div id="ev-calc-product"></div><div class="ev-filter-row"><div class="ev-field"><label for="ev-area">Площадь помещения, м²</label><input type="text" inputmode="decimal" id="ev-area" name="area" placeholder="Например, 20,5" required autocomplete="off"><small>Укажите площадь вместе с нишами и проходами.</small></div><div class="ev-field"><label for="ev-reserve">Запас на подрезку, %</label><input type="text" inputmode="decimal" id="ev-reserve" name="reserve" value="10" required><small>От 0 до 20%. Значение 10% — пример; нужный запас зависит от плана и раскладки.</small></div></div><button type="submit" class="ev-button ev-button--primary">Рассчитать</button><p class="ev-note">Расчёт округляет количество вверх до целых упаковок. Используется площадь упаковки выбранного артикула: 1,99 или 2,54 м².</p></form><section id="ev-calc-result" class="ev-result" aria-live="polite" tabindex="-1"><span class="ev-eyebrow">Ваш расчёт</span><h2>Сколько упаковок нужно?</h2><p>Выберите декор и введите площадь. Здесь появятся количество, площадь покупки и стоимость покрытия по текущей цене.</p></section></div></section>'
    write_page(page,'Рассчитать покупку','Площадь комнаты → запас → целые упаковки. Получите расчёт покрытия и сохраните ссылку для продавца.',body,'calculator')
    page='compare.html'
    body='<section class="ev-section"><div class="ev-wrap"><div class="ev-favorites-bar"><p>До трёх декоров в одном сравнении.</p><div class="ev-actions"><button type="button" class="ev-button" data-share-compare disabled>Скопировать ссылку</button><button type="button" class="ev-text-link" data-print>Распечатать</button></div></div><div id="ev-compare"><p>Добавьте декоры из каталога с помощью кнопки «Сравнить».</p>'+link('Открыть каталог','catalog-ru/',page,'ev-button')+'</div></div></section>'
    write_page(page,'Сравнение декоров','Рассмотрите выбранные варианты рядом: рисунок, формат, размеры, упаковку и текущую цену.',body,'compare',hero_actions=actions(page))
    page='favorites.html'
    body='<section class="ev-section"><div class="ev-wrap"><div class="ev-favorites-bar"><p>В подборке: <b id="ev-favorite-total">0</b></p><div class="ev-actions"><button type="button" class="ev-button" data-share-selection disabled>Скопировать ссылку</button><button type="button" class="ev-text-link" data-print>Распечатать</button></div></div><div id="ev-shared-note" class="ev-note" hidden><p>Вы открыли подборку по ссылке. Её можно сохранить в своём избранном.</p><button type="button" class="ev-button" data-save-shared>Добавить в моё избранное</button></div><div id="ev-favorites"><p>Отметьте понравившиеся декоры в каталоге.</p>'+link('Открыть каталог','catalog-ru/',page,'ev-button')+'</div><p class="ev-note">Избранное хранится в этом браузере. Чтобы открыть подборку на другом устройстве или показать продавцу, скопируйте ссылку.</p></div></section>'
    write_page(page,'Ваши избранные декоры','Соберите короткий список, сравните варианты и покажите подборку в магазине.',body,'favorites',hero_actions=actions(page))

def other_pages():
    page='contacts.html'
    body='<section class="ev-section"><div class="ev-wrap"><section id="ev-contact-selection" class="ev-note" hidden></section><div class="ev-article-layout"><div><span class="ev-eyebrow">Республика Беларусь</span><h2>ООО «Флорсток»</h2><p>Представитель торговой марки EVERSENSE в Беларуси.</p></div><div class="ev-prose"><section><h2>Обсудим вашу покупку</h2><p>Уточните наличие нужного декора, количество упаковок и возможность посмотреть образец. Если уже выбрали варианты, назовите артикулы или сохраните ссылку на подборку.</p><div class="ev-actions"><a class="ev-button ev-button--primary" href="tel:+375296713971">+375 29 671-39-71</a>'+link('Найти магазин','where-to-buy.html',page,'ev-button')+'</div></section><section><h2>Что подготовить к разговору</h2><ul><li>Артикул или два-три понравившихся декора.</li><li>Площадь помещения и ориентировочное время покупки.</li><li>Тип помещения, наличие подогрева и особенности основания.</li><li>Город, в котором удобно получить покупку или посмотреть образец.</li></ul></section><section><h2>Реквизиты</h2><p>ООО «Флорсток»<br>УНП 192608003<br>220062, Республика Беларусь, г. Минск,<br>пр. Победителей, д. 129, пом. 358</p><p>Перед визитом уточните адрес торговой точки и наличие экспозиции: адрес компании может отличаться от адреса магазина.</p></section></div></div></div></section>'
    write_page(page,'Контакты в Беларуси','Проверить наличие, найти образец и получить ответы по выбранному покрытию.',body,'contacts')
    page='projects.html'
    chosen=[]
    for c,_,_ in COLLECTIONS:
        chosen.extend([p for p in PRODUCTS if p['collectionID']==c][:4])
    body='<section class="ev-section"><div class="ev-wrap"><div class="ev-room-grid">'+''.join('<article class="ev-room-card">'+link('<img src="'+e(href(p['interiorImage'],page))+'" alt="'+e(p['name'])+' в интерьере" loading="lazy" width="900" height="700">',p['canonicalPath'],page)+'<span class="ev-sku">'+p['sku']+'</span><h2>'+e(p['name'])+'</h2><p>'+e(p['collectionName'])+'</p><div class="ev-actions">'+link('Смотреть декор',p['canonicalPath'],page,'ev-text-link')+'<button class="ev-button" type="button" data-ev-favorite="'+p['sku']+'">В избранное</button></div></article>' for p in chosen)+'</div><p class="ev-note">Интерьерные изображения из каталога производителя помогают оценить рисунок и настроение пола. Оттенок и фактуру выбранного декора уточняйте по реальному образцу.</p></div></section>'
    write_page(page,'EVERSENSE в интерьере','Посмотрите, как декор работает на большой площади и сочетается с мебелью, светом и цветом стен.',body,'projects',hero_actions=actions(page))
    page='privacy.html'
    body='<section class="ev-section"><div class="ev-wrap ev-prose"><section><h2>Избранное и сравнение</h2><p>Выбранные артикулы сохраняются локально в вашем браузере. Для этих функций не нужны имя, телефон или регистрация. Удалить выбор можно кнопками в каталоге и сравнении либо очисткой данных сайта в настройках браузера.</p></section><section><h2>Ссылки на подборки</h2><p>При использовании «Скопировать ссылку» артикулы включаются в адрес страницы. Для расчёта в ссылке также сохраняются площадь и запас. Подборка станет доступна тому, кому вы отправите эту ссылку.</p></section><section><h2>Внешние сервисы</h2><p>Сайт загружает цены из публичной таблицы Google, шрифты и материалы производителя. При открытии сторонних сервисов и документов действуют их собственные условия обработки данных.</p></section><section><h2>Контакт по вопросам сайта</h2><p>ООО «Флорсток», УНП 192608003. Телефон: <a href="tel:+375296713971">+375 29 671-39-71</a>.</p></section></div></section>'
    write_page(page,'Конфиденциальность','Как работают сохранение выбора и ссылки на подборки.',body,'privacy')
    page='installers.html'
    write_page(page,'Подготовка к работе с мастером','Что обсудить до начала укладки, чтобы покрытие служило долго.', '<section class="ev-section"><div class="ev-wrap ev-prose"><section><h2>Передайте инструкцию и план помещения</h2><p>До согласования работ обсудите состояние и влажность основания, подложку, направление раскладки, переходы между комнатами, зазоры и встроенную мебель. Попросите включить подготовку основания и расходные материалы в расчёт работ.</p><div class="ev-actions">'+link('Этапы укладки','installation.html',page,'ev-button ev-button--primary')+link('Документы для мастера','downloads.html',page,'ev-button')+'</div></section><section><h2>После монтажа</h2><p>Осмотрите результат вместе с мастером и сохраните документы о покупке, этикетку с упаковки, результаты измерений основания и акт работ.</p></section></div></section>','installers')
    page='sitemap.html'
    nav=[('Главная','index.html'),('Каталог','catalog-ru/'),('Как выбрать','choose.html'),('О продукте','about.html'),('Интерьеры','projects.html'),('Калькулятор','calculator.html'),('Сравнение','compare.html'),('Избранное','favorites.html'),('Укладка','installation.html'),('Уход','care.html'),('Гарантия','warranty.html'),('Вопросы и ответы','faq.html'),('Документы','downloads.html'),('Где купить','where-to-buy.html'),('Контакты','contacts.html')]
    body='<section class="ev-section"><div class="ev-wrap"><div class="ev-link-grid">'+''.join(link('<h2>'+t+'</h2><span aria-hidden="true">↗</span>',u,page,'ev-link-card') for t,u in nav)+'</div><h2>Все декоры</h2><div class="ev-link-grid">'+''.join(link(p['sku']+' · '+e(p['name']),p['canonicalPath'],page,'ev-text-link') for p in PRODUCTS)+'</div></div></section>'
    write_page(page,'Все страницы','Разделы сайта и все декоры EVERSENSE.',body,'sitemap')

def redirect(page, target):
    url=href(target,page)
    (ROOT/page).write_text('<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>EVERSENSE — каталог</title><link rel="canonical" href="https://eversense.by/'+target.lstrip('/')+'"><meta http-equiv="refresh" content="0;url='+e(url)+'"></head><body><p>'+link('Перейти к декору или коллекции EVERSENSE',target,page)+'</p><script>location.replace('+json.dumps(url)+'+location.search+location.hash)</script></body></html>\n')

def aliases():
    redirect('catalog.html','catalog-ru/')
    for old,c in [('nature-aesthetic.html','nature'),('quiet-luxury.html','luxury'),('new-minimalism.html','minimal')]:
        redirect(old,COLLECTION_PATHS[c])
    for p in PRODUCTS:
        redirect('products/'+p['sku']+'.html',p['canonicalPath'])

if __name__ == '__main__':
    catalogs();guides();tools_pages();other_pages();aliases()
    print('Built 4 catalogs, 7 guides, 3 buyer tools, 5 support pages and 34 legacy redirects.')
