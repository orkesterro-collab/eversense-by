#!/usr/bin/env python3
"""Build small, readable buyer pages around the existing EVERSENSE catalog.

Run from any directory. Product facts come from extract_products.py, editorial
content from content/buyer-guides.json. No third-party build dependencies.
"""
from pathlib import Path
from html import escape
import json
import posixpath
from explore_product import render_layers
from explore_interiors import render_interiors
from explore_guides import render_designs, render_sample, render_situations, render_next

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'assets/products-data.json').read_text())
PRODUCTS = DATA if isinstance(DATA, list) else DATA['products']
PRODUCTS.sort(key=lambda p: (['nature','luxury','minimal'].index(p['collectionID']), int(p['sku'][2:])))
GUIDES = json.loads((ROOT / 'content/buyer-guides.json').read_text())
VERSION = '20261112favoriteportrait'
COLLECTIONS = [
    ('nature', 'Природная эстетика', 'Спокойные древесные оттенки и выразительные рисунки дуба.'),
    ('luxury', 'Тихая роскошь', 'Натуральные и глубокие тона для интерьера с характером.'),
    ('minimal', 'Новый минимализм', 'Светлое дерево, бежевые и серые тона, рисунок мрамора.'),
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
    return '<div class="ev-actions">' + link('<svg class="ev-heart-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M20.8 4.6c-2.1-2.1-5.5-2.1-7.6 0L12 5.8l-1.2-1.2c-2.1-2.1-5.5-2.1-7.6 0s-2.1 5.5 0 7.6L12 21l8.8-8.8c2.1-2.1 2.1-5.5 0-7.6Z"/></svg>Избранное (<span data-favorites-count>0</span>)', 'favorites.html', page, 'ev-favorites-link', 'data-favorites-link') + '</div>'

def footer(page):
    groups = [
        ('Выбрать и купить', [('Все декоры', 'catalog-ru/'), ('Помощь с выбором', 'choose.html'), ('Интерьеры', 'projects.html'), ('Где купить', 'where-to-buy.html'), ('Контакты', 'contacts.html')]),
        ('Полезно знать', [('О продукте', 'about.html'), ('Укладка и тёплый пол', 'installation.html'), ('Уход', 'care.html'), ('Гарантия', 'warranty.html'), ('Ответы на вопросы', 'faq.html'), ('Документы', 'downloads.html')]),
    ]
    return '<footer class="ev-footer"><div class="ev-wrap"><div>' + link('<img class="ev-footer-logo" src="'+e(href('assets/original-tilda/44ef8387add2-Frame_784.svg',page))+'" alt="EVERSENSE" width="220" height="80">', 'index.html', page, 'ev-footer-brand') + '<p>Напольные покрытия на древесной основе.</p><p>Представитель в Беларуси — ООО «Флорсток».<br>УНП 192608003<br>220062, г. Минск, пр. Победителей, д. 129, пом. 358</p><p><a href="tel:+375296713971">+375 29 671-39-71</a></p></div>' + ''.join('<div><h2>'+title+'</h2><nav aria-label="'+title+'">'+''.join(link(label, url, page) for label, url in items)+'</nav></div>' for title, items in groups) + '<div class="ev-footer-bottom"><span>© EVERSENSE · Беларусь</span>'+link('Все страницы', 'sitemap.html', page)+link('Конфиденциальность', 'privacy.html', page)+'</div></div></footer>'

def write_page(page, title, lead, body, page_type='', collection='', hero_actions='', structured=None):
    canonical = 'https://eversense.by/' + (page[:-10] if page.endswith('index.html') else page)
    schema = structured or {'@context':'https://schema.org','@type':'WebPage','name':title,'description':lead,'url':canonical,'inLanguage':'ru'}
    extras = []
    if page_type in ('product', 'choose', 'faq', 'installation', 'care', 'warranty', 'downloads'):
        extras.append('explore-guides.css')
    if page_type == 'product':
        extras.extend(['explore-product.css', 'explore-product.js'])
    if page_type == 'projects':
        extras.extend(['explore-interiors.css', 'explore-interiors.js'])
    extra_assets = '\n'.join(f'<link rel="stylesheet" href="{href("assets/"+file,page)}?v={VERSION}">' if file.endswith('.css') else f'<script src="{href("assets/"+file,page)}?v={VERSION}" defer></script>' for file in extras)
    html = f'''<!doctype html>
<html lang="ru" data-buyer-static="true"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#343333"><meta name="robots" content="noindex,nofollow">
<title>{e(title)} — EVERSENSE Беларусь</title><meta name="description" content="{e(lead)}">
<link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:locale" content="ru_RU"><meta property="og:title" content="{e(title)} — EVERSENSE"><meta property="og:description" content="{e(lead)}"><meta property="og:url" content="{canonical}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="{href('assets/buyer.css',page)}?v={VERSION}" data-ev-buyer-css>
{extra_assets}
<script type="application/ld+json">{json.dumps(schema,ensure_ascii=False).replace('<',chr(92)+'u003c')}</script>
<script src="{href('assets/products-data.js',page)}?v={VERSION}" defer></script>
<script src="{href('assets/buyer-core.js',page)}?v={VERSION}" defer></script>
<script src="{href('assets/prices.js',page)}?v={VERSION}" defer></script>
<script src="{href('assets/buyer.js',page)}?v={VERSION}" defer></script>
</head><body class="ev-buyer" data-buyer-page="{e(page_type)}" data-collection="{e(collection)}">
<a href="#main" class="ev-skip-link">Перейти к содержанию</a>
<main id="main"><section class="ev-hero"><div class="ev-wrap"><nav class="ev-breadcrumb" aria-label="Хлебные крошки">{link('Главная','index.html',page)}<span aria-hidden="true">/</span><span>{e(title)}</span></nav><h1>{e(title)}</h1><p class="ev-lead">{e(lead)}</p>{hero_actions}</div></section>
{body}</main>{footer(page)}
<noscript><div class="ev-wrap ev-note">Для расчёта, фильтров, избранного включите JavaScript. Страницы декоров и полезные материалы доступны по обычным ссылкам.</div></noscript>
</body></html>'''
    path = ROOT / page
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html + '\n')

def card(p, page):
    return f'''<article class="ev-card" data-product="{p['sku']}"><a class="ev-card-image" href="{e(href(p['canonicalPath'],page))}"><img src="{e(href(p['productImage'],page))}" alt="{e(p['name'])}" width="640" height="500" loading="lazy"><img class="ev-card-interior" src="{e(href(p['interiorImage'],page))}" alt="" width="640" height="500" loading="lazy"></a><div class="ev-card-body"><span class="ev-sku">{p['sku']}</span><h2 class="ev-card-title">{link(e(p['name']),p['canonicalPath'],page)}</h2><p class="ev-card-meta">{e(p['collectionName'])} · {p['lengthMM']} × {p['widthMM']} мм</p><div class="ev-price-box" data-buyer-price="{p['sku']}"><span class="ev-price-pending">Цена уточняется</span></div><div class="ev-card-actions"><button type="button" class="ev-button" data-ev-favorite="{p['sku']}" aria-pressed="false">В избранное</button></div></div></article>'''

def field(label, name, options, value=''):
    return '<div class="ev-field"><label for="ev-'+name+'">'+label+'</label><select id="ev-'+name+'" name="'+name+'">'+''.join('<option value="'+e(v)+'"'+(' selected' if v==value else '')+'>'+e(t)+'</option>' for v,t in options)+'</select></div>'

TONE = [('', 'Все оттенки'), ('light', 'Светлые'), ('natural', 'Натуральные'), ('gray', 'Серые'), ('brown', 'Коричневые'), ('beige', 'Бежевые')]
DESIGN = [('', 'Все группы'), ('wood', 'Дубовые декоры'), ('stone', 'Мрамор'), ('plain', 'Песок и серый')]

def catalogs():
    for collection, title, lead, page in [('', 'Каталог декоров', '30 декоров. Найдите свой оттенок и сохраните понравившиеся варианты.', 'catalog-ru/index.html')] + [(c,t,d,COLLECTION_PATHS[c].lstrip('/')+'index.html') for c,t,d in COLLECTIONS]:
        items = [p for p in PRODUCTS if not collection or p['collectionID']==collection]
        nav = '<nav class="ev-inline-nav" aria-label="Коллекции">'+link('Все декоры', 'catalog-ru/', page, extra='aria-current="page"' if not collection else '')+''.join(link(t, COLLECTION_PATHS[c], page, extra='aria-current="page"' if c==collection else '') for c,t,_ in COLLECTIONS)+'</nav>'
        filters = '<form id="ev-catalog-filters" class="ev-toolbar" role="search"><div class="ev-field"><label for="ev-q">Поиск по названию или артикулу</label><input id="ev-q" name="q" type="search" placeholder="Например, EL1052 или дуб" autocomplete="off"></div><details class="ev-filter-details" open><summary>Фильтры и сортировка</summary><div class="ev-filter-row">'
        if not collection:
            filters += field('Коллекция','collection',[('','Все коллекции')]+[(c,t) for c,t,_ in COLLECTIONS])
        design_options = [(v,t) for v,t in DESIGN if not v or any(p['tags']['design']==v for p in items)]
        filters += field('Оттенок','tone',TONE)+field('Группа декоров','design',design_options)+field('Порядок','sort',[('','По коллекциям'),('name','По названию'),('price-up','Сначала дешевле'),('price-down','Сначала дороже')])+'</div></details><div class="ev-actions"><p id="ev-result-count" class="ev-count" role="status">Найдено декоров: '+str(len(items))+'</p><button type="button" class="ev-text-link" data-reset-filters>Сбросить фильтры</button></div></form>'
        body = '<section class="ev-section"><div class="ev-wrap">'+nav+filters+'<div class="ev-grid" id="ev-catalog-results">'+''.join(card(p,page) for p in items)+'</div></div></section><section class="ev-section"><div class="ev-wrap"><p class="ev-note">Оттенок на экране зависит от освещения и настроек устройства. Перед покупкой посмотрите реальный образец. Наличие нужного количества уточняйте у продавца.</p>'+link('Помочь с выбором', 'choose.html', page,'ev-button')+'</div></section>'
        write_page(page,title,lead,body,'catalog',collection,actions(page))

def finder(page):
    return '<section class="ev-section" id="finder"><div class="ev-wrap"><span class="ev-eyebrow">02 · От впечатления к вариантам</span><h2>Сузим круг выбора</h2><p class="ev-lead">Оттенок и рисунок определят подборку. Комната подскажет, на что обратить внимание в эксплуатации.</p><form id="ev-finder"><div class="ev-filter-row">'+field('Комната','room',[('living','Гостиная'),('bedroom','Спальня'),('kitchen','Кухня'),('hall','Прихожая')])+field('Оттенок','tone',TONE)+field('Группа декоров','design',DESIGN)+'</div><button class="ev-button ev-button--primary" type="submit">Показать декоры</button></form><div id="ev-finder-results" class="ev-section" tabindex="-1" hidden></div></div></section>'

def guides():
    for key, page in [('product','about.html'),('choose','choose.html'),('faq','faq.html'),('installation','installation.html'),('care','care.html'),('warranty','warranty.html'),('downloads','downloads.html')]:
        g = GUIDES[key]
        sections = [s for s in g['sections'] if key != 'choose' or s['id'] not in COLLECTION_PATHS]
        toc = '<aside class="ev-toc"><strong>На этой странице</strong><ul>'+''.join('<li>'+link(e(s['title']),'#'+s['id'],page)+'</li>' for s in sections)+'</ul></aside>'
        prose = ''
        for s in sections:
            prose += '<section id="'+s['id']+'"><h2>'+e(s['title'])+'</h2>'
            if key == 'product' and s['id'] == 'layers':
                prose += render_layers(page, href)
            else:
                prose += ''.join('<p>'+e(t)+'</p>' for t in s.get('body',[]))
            if key == 'choose' and s['id'] == 'collections':
                for collection, title, description in COLLECTIONS:
                    prose += '<div class="ev-collection-glance" id="'+collection+'"><h3>'+e(title)+'</h3><p>'+e(description)+'</p>'+link('Рассмотреть коллекцию',COLLECTION_PATHS[collection],page,'ev-text-link')+'</div>'
            if key == 'choose' and s['id'] == 'sample':
                prose += render_sample()
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
        extra = render_designs(page, PRODUCTS, href) + finder(page) if key=='choose' else ''
        if key=='product':
            p = next(p for p in PRODUCTS if p['sku']=='EL2151')
            extra = '<section class="ev-section"><div class="ev-wrap ev-article-visual"><img src="'+e(href(p['interiorImage'],page))+'" alt="'+e(p['name'])+' в интерьере" width="900" height="650"><div><span class="ev-eyebrow">Дуб · Мрамор · Бежевые и серые тона</span><h2>Три коллекции.<br>Ваш характер дома.</h2><p class="ev-lead">Выберите настроение, затем оцените материал вживую. Разница видна в рисунке, оттенке и формате.</p>'+link('Посмотреть все декоры','catalog-ru/',page,'ev-button')+'</div></div></section>'
        body = (extra if key=='choose' else render_situations(key,page,href))+'<section class="ev-section"><div class="ev-wrap ev-article-layout">'+toc+'<div class="ev-prose">'+prose+'</div></div></section>'+ (extra if key=='product' else '') + render_next(key,page,href)
        primary = {
            'product': ('Посмотреть конструкцию', '#layers'),
            'choose': ('Посмотреть рисунки', '#designs'),
            'installation': ('Открыть инструкцию PDF', 'https://drive.google.com/file/d/1dImDaWKPtefl-TOjxHiSL3zauqBfHdJH/view'),
            'care': ('Правила ежедневной уборки', '#daily-cleaning'),
            'warranty': ('Запросить условия гарантии', 'contacts.html'),
            'downloads': ('Инструкция по укладке PDF', 'https://drive.google.com/file/d/1dImDaWKPtefl-TOjxHiSL3zauqBfHdJH/view'),
        }.get(key, ('Каталог декоров', 'catalog-ru/'))
        secondary = ('Каталог декоров', 'catalog-ru/') if key in ('installation','care','warranty','downloads') else ('Где посмотреть образец','where-to-buy.html')
        write_page(page,g['title'],g['lead'],body,key,hero_actions='' if key=='choose' else '<div class="ev-actions">'+link(primary[0],primary[1],page,'ev-button ev-button--primary', 'target="_blank" rel="noopener noreferrer"' if primary[1].startswith('https://') else '')+link(secondary[0],secondary[1],page,'ev-button')+'</div>')

def tools_pages():
    page = 'calculator.html'
    opts = [(p['sku'],p['sku']+' · '+p['name']) for p in PRODUCTS]
    body = '<section class="ev-section"><div class="ev-wrap ev-calculator"><form id="ev-calc-form" novalidate>'+field('Декор','sku',opts)+'<div id="ev-calc-product"></div><div class="ev-filter-row"><div class="ev-field"><label for="ev-area">Площадь помещения, м²</label><input type="text" inputmode="decimal" id="ev-area" name="area" placeholder="Например, 20,5" required autocomplete="off"><small>Укажите площадь вместе с нишами и проходами.</small></div><div class="ev-field"><label for="ev-reserve">Запас на подрезку, %</label><input type="text" inputmode="decimal" id="ev-reserve" name="reserve" value="10" required><small>От 0 до 20%. Значение 10% — пример; нужный запас зависит от плана и раскладки.</small></div></div><button type="submit" class="ev-button ev-button--primary">Рассчитать</button><p class="ev-note">Расчёт округляет количество вверх до целых упаковок. Используется площадь упаковки выбранного артикула: 1,99 или 2,54 м².</p></form><section id="ev-calc-result" class="ev-result" aria-live="polite" tabindex="-1"><span class="ev-eyebrow">Ваш расчёт</span><h2>Сколько упаковок нужно?</h2><p>Выберите декор и введите площадь. Здесь появятся количество, площадь покупки и стоимость покрытия по текущей цене.</p></section></div></section>'
    write_page(page,'Рассчитать покупку','Площадь комнаты → запас → целые упаковки. Получите расчёт покрытия и сохраните ссылку для продавца.',body,'calculator')
    page='favorites.html'
    body='<section class="ev-section"><div class="ev-wrap"><div class="ev-favorites-bar"><p>В подборке: <b id="ev-favorite-total">0</b></p><div class="ev-actions"><button type="button" class="ev-button" data-share-selection disabled>Скопировать ссылку</button><button type="button" class="ev-text-link" data-print>Распечатать</button></div></div><div id="ev-shared-note" class="ev-note" hidden><p>Вы открыли подборку по ссылке. Её можно сохранить в своём избранном.</p><button type="button" class="ev-button" data-save-shared>Добавить в моё избранное</button></div><div id="ev-favorites"><p>Отметьте понравившиеся декоры в каталоге.</p>'+link('Открыть каталог','catalog-ru/',page,'ev-button')+'</div><p class="ev-note">Избранное хранится в этом браузере. Чтобы открыть подборку на другом устройстве или показать продавцу, скопируйте ссылку.</p></div></section>'
    write_page(page,'Ваши избранные декоры','Сохраните понравившиеся декоры и покажите подборку в магазине.',body,'favorites',hero_actions='')

def other_pages():
    page='contacts.html'
    body='<section class="ev-section"><div class="ev-wrap"><section id="ev-contact-selection" class="ev-note" hidden></section><div class="ev-article-layout"><div><span class="ev-eyebrow">Республика Беларусь</span><h2>ООО «Флорсток»</h2><p>Представитель торговой марки EVERSENSE в Беларуси.</p></div><div class="ev-prose"><section><h2>Обсудим вашу покупку</h2><p>Уточните наличие нужного декора, количество упаковок и возможность посмотреть образец. Если уже выбрали варианты, назовите артикулы или сохраните ссылку на подборку.</p><div class="ev-actions"><a class="ev-button ev-button--primary" href="tel:+375296713971">+375 29 671-39-71</a>'+link('Найти магазин','where-to-buy.html',page,'ev-button')+'</div></section><section><h2>Что подготовить к разговору</h2><ul><li>Артикул или два-три понравившихся декора.</li><li>Площадь помещения и ориентировочное время покупки.</li><li>Тип помещения, наличие подогрева и особенности основания.</li><li>Город, в котором удобно получить покупку или посмотреть образец.</li></ul></section><section><h2>Реквизиты</h2><p>ООО «Флорсток»<br>УНП 192608003<br>220062, Республика Беларусь, г. Минск,<br>пр. Победителей, д. 129, пом. 358</p><p>Перед визитом уточните адрес торговой точки и наличие экспозиции: адрес компании может отличаться от адреса магазина.</p></section></div></div></div></section>'
    write_page(page,'Контакты в Беларуси','Проверить наличие, найти образец и получить ответы по выбранному покрытию.',body,'contacts')
    page='projects.html'
    body=render_interiors(page, PRODUCTS, href)
    write_page(page,'Одна комната — разный характер','Три комнаты. Шесть декоров. Посмотрите, как пол меняет интерьер.',body,'projects')
    page='privacy.html'
    body='<section class="ev-section"><div class="ev-wrap ev-prose"><section><h2>Избранное</h2><p>Выбранные артикулы сохраняются локально в вашем браузере. Для избранного не нужны имя, телефон или регистрация. Удалить выбор можно кнопками в каталоге или очисткой данных сайта в настройках браузера.</p></section><section><h2>Ссылки на подборки</h2><p>При использовании «Скопировать ссылку» артикулы включаются в адрес страницы. Для расчёта в ссылке также сохраняются площадь и запас. Подборка станет доступна тому, кому вы отправите эту ссылку.</p></section><section><h2>Внешние сервисы</h2><p>Сайт загружает цены из публичной таблицы Google, шрифты и материалы производителя. При открытии сторонних сервисов и документов действуют их собственные условия обработки данных.</p></section><section><h2>Контакт по вопросам сайта</h2><p>ООО «Флорсток», УНП 192608003. Телефон: <a href="tel:+375296713971">+375 29 671-39-71</a>.</p></section></div></section>'
    write_page(page,'Конфиденциальность','Как работают сохранение выбора и ссылки на подборки.',body,'privacy')
    page='installers.html'
    body = '<section class="ev-section"><div class="ev-wrap ev-prose"><section><h2>До согласования стоимости</h2><p>Покажите мастеру план помещения, выбранный артикул и инструкцию EVERSENSE. Обсудите направление рядов, переходы между комнатами, трубы, дверные проёмы и встроенную мебель. Договоритесь, кто заказывает покрытие и расходные материалы.</p><ul><li>Какие измерения основания нужны: ровность, влажность и готовность подогрева.</li><li>Нужно ли снимать старое покрытие и выравнивать основание.</li><li>Какая подложка и пароизоляция предусмотрены для вашей конструкции.</li><li>Какие работы, профили, плинтусы и вывоз мусора включены в смету.</li></ul></section><section><h2>Перед началом укладки</h2><p>Сверьте количество упаковок с раскладкой и согласованным запасом. Вместе проверьте маркировку и состояние панелей. Попросите зафиксировать результаты измерений основания и уточните, где будут компенсационные зазоры и переходные профили.</p><div class="ev-actions">'+link('Этапы укладки','installation.html',page,'ev-button ev-button--primary')+link('Документы для мастера','downloads.html',page,'ev-button')+'</div></section><section><h2>При приёмке работы</h2><p>Осмотрите поверхность, соединения панелей, примыкания и дверные проёмы при хорошем освещении. Проверьте открывание дверей. Обсудите уход и защиту под мебелью, сохраните оставшиеся целые панели.</p><p>Попросите передать акт работ, сведения о подложке и результаты проверки основания. Этикетки упаковок и документы о покупке храните вместе: они помогут при последующем обращении по покрытию.</p>'+link('Как ухаживать за готовым полом','care.html',page,'ev-text-link')+'</section></div></section>'
    write_page(page,'Подготовка к работе с мастером','Короткий список для обсуждения сметы, подготовки основания и приёмки готового пола.',body,'installers')
    page='sitemap.html'
    nav=[('Главная','index.html'),('Каталог','catalog-ru/'),('Как выбрать','choose.html'),('О продукте','about.html'),('Интерьеры','projects.html'),('Избранное','favorites.html'),('Укладка','installation.html'),('Уход','care.html'),('Гарантия','warranty.html'),('Вопросы и ответы','faq.html'),('Документы','downloads.html'),('Где купить','where-to-buy.html'),('Контакты','contacts.html'),('Подготовка к работе с мастером','installers.html'),('Конфиденциальность','privacy.html')]
    body='<section class="ev-section"><div class="ev-wrap"><div class="ev-link-grid">'+''.join(link('<h2>'+t+'</h2><span aria-hidden="true">↗</span>',u,page,'ev-link-card') for t,u in nav)+'</div><h2>Все декоры</h2><div class="ev-link-grid">'+''.join(link(p['sku']+' · '+e(p['name']),p['canonicalPath'],page,'ev-text-link') for p in PRODUCTS)+'</div></div></section>'
    write_page(page,'Все страницы','Разделы сайта и все декоры EVERSENSE.',body,'sitemap')

def redirect(page, target):
    url=href(target,page)
    (ROOT/page).write_text('<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>EVERSENSE — каталог</title><link rel="canonical" href="https://eversense.by/'+target.lstrip('/')+'"><meta http-equiv="refresh" content="0;url='+e(url)+'"></head><body><p>'+link('Перейти к декору или коллекции EVERSENSE',target,page)+'</p><script>location.replace('+json.dumps(url)+'+location.search+location.hash)</script></body></html>\n')

def aliases():
    redirect('compare.html','favorites.html')
    redirect('catalog.html','catalog-ru/')
    for old,c in [('nature-aesthetic.html','nature'),('quiet-luxury.html','luxury'),('new-minimalism.html','minimal')]:
        redirect(old,COLLECTION_PATHS[c])
    for p in PRODUCTS:
        redirect('products/'+p['sku']+'.html',p['canonicalPath'])

if __name__ == '__main__':
    catalogs();guides();tools_pages();other_pages();aliases()
    print('Built 4 catalogs, 7 guides, 2 buyer tools, 5 support pages and 34 legacy redirects.')
