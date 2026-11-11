"""Small editorial entry points; all routes and product imagery stay catalog-backed."""
from html import escape


def render_designs(page, products, href):
    by_sku = {p['sku']: p for p in products}
    designs = [
        ('wood', 'EL2151', 'Древесный рисунок', 'Рассмотрите волокна и переходы оттенков. Насколько заметным должен быть рисунок в вашей комнате?'),
        ('stone', 'EL1000', 'Рисунок мрамора', 'Посмотрите на прожилки и масштаб рисунка. У этих декоров более широкая панель.'),
        ('plain', 'EL153', 'Сдержанная палитра', 'Бежевый песок и Ярко-серый. Рассмотрите оттенок и древесный рисунок рядом с отделкой.'),
    ]
    cards = ''
    for design, sku, title, text in designs:
        p = by_sku[sku]
        cards += f'''<a class="ev-design-card" data-design-route="{design}" href="{escape(href('catalog-ru/',page))}?design={design}">
          <img src="{escape(href(p['productImage'],page))}" alt="{escape(p['name'])} — {sku}" width="640" height="480" loading="lazy">
          <span class="ev-sku">{sku} · {escape(p['name'])}</span><h3>{title}</h3><p>{text}</p><span class="ev-text-link">Смотреть декоры <span aria-hidden="true">↗</span></span></a>'''
    return f'''<section class="ev-section ev-design-entry" id="designs"><div class="ev-wrap"><span class="ev-eyebrow">01 · Какой рисунок вам ближе?</span><h2>Сначала — впечатление</h2><div class="ev-design-grid">{cards}</div><a class="ev-text-link" href="{escape(href('projects.html',page))}">Посмотреть, как разные декоры меняют один интерьер <span aria-hidden="true">↗</span></a></div></section>'''


def render_sample():
    steps = [
        ('У окна', 'Положите образец горизонтально. Нравится ли оттенок при дневном свете?'),
        ('В глубине комнаты', 'Перенесите образец подальше от окна. Не становится ли пол слишком тёмным для вас?'),
        ('Вечером', 'Включите свои светильники. Устраивает ли цвет при обычном вечернем освещении?'),
        ('Рядом с отделкой', 'Сравните со стеной, дверью и мебелью. Затем рассмотрите несколько панелей вместе: нравится ли общий рисунок?'),
    ]
    return '<div class="ev-sample-check" role="group" aria-label="Проверка образца"><p class="ev-eyebrow">Четыре наблюдения перед покупкой</p><p>Если можете взять образец домой, пройдите этот короткий маршрут. Отметки — для вашего удобства при просмотре страницы.</p>'+''.join(f'<label class="ev-sample-step"><input type="checkbox" name="sample-check" value="{i}"><span><strong>{title}</strong><span>{text}</span></span></label>' for i,(title,text) in enumerate(steps,1))+'</div>'


def render_situations(key, page, href):
    if key == 'care':
        title = 'Что произошло с полом?'
        lead = 'Начните со своей ситуации — подробные правила ниже.'
        items = [
            ('01', 'Пролили воду', 'Соберите жидкость сразу, затем вытрите поверхность насухо.', 'water-and-spills', 'Подробнее о жидкости и пятнах'),
            ('02', 'Принесли песок', 'Сначала уберите сухие частицы. Затем переходите к влажной уборке.', 'daily-cleaning', 'Как правильно убирать'),
            ('03', 'Двигаете мебель', 'Приподнимайте тяжёлые предметы и проверьте защитные накладки на ножках.', 'furniture', 'Как защитить поверхность'),
        ]
    elif key == 'installation':
        title = 'Три разговора с мастером'
        lead = 'На каждом этапе есть вопросы, которые лучше решить заранее.'
        items = [
            ('До заказа', 'Что покупаем вместе с полом?', 'Согласуйте раскладку, количество, подложку и переходы между комнатами.', 'before-installation', 'Подготовить заказ'),
            ('До монтажа', 'Готово ли основание?', 'Проверьте влажность, ровность и условия работы тёплого пола.', 'subfloor', 'Проверить подготовку'),
            ('При приёмке', 'Что осмотреть и сохранить?', 'Проверьте стыки и примыкания. Сохраните документы и оставшиеся панели.', 'handover', 'Принять работу'),
        ]
    else:
        return ''
    return f'<section class="ev-section ev-situations"><div class="ev-wrap"><h2>{title}</h2><p class="ev-lead">{lead}</p><div class="ev-link-grid">'+''.join(f'<a class="ev-link-card" href="#{anchor}"><span>{number}</span><h3>{heading}</h3><p>{text}</p><span class="ev-text-link">{action} <span aria-hidden="true">↓</span></span></a>' for number,heading,text,anchor,action in items)+'</div></div></section>'


def render_next(key, page, href):
    choices = {
        'product': [('Рассмотреть в интерьере', 'projects.html', 'Один интерьер, два декора: заметные различия на настоящих изображениях каталога.'), ('Проверить свой образец', 'choose.html#sample', 'Четыре наблюдения, которые помогут принять окончательное решение.')],
        'choose': [('Собрать короткий список', 'catalog-ru/', 'Добавьте два-три декора в сравнение и проверьте их на образцах.'), ('Рассчитать покупку', 'calculator.html', 'Узнайте число целых упаковок и стоимость выбранного покрытия.')],
        'installation': [('Обсудить работу с мастером', 'installers.html', 'Что включить в смету и проверить при приёмке.'), ('Ухаживать за новым полом', 'care.html', 'Уборка, защита мебели и действия при пролитой жидкости.')],
        'care': [('Если осталось повреждение', 'warranty.html#claim', 'Какие фотографии и документы подготовить для обращения.'), ('Проверить рекомендации', 'downloads.html', 'Официальные материалы по укладке и уходу.')],
        'warranty': [('Подготовить обращение', 'contacts.html', 'Сообщите артикул, дату покупки и опишите ситуацию.'), ('Открыть документы', 'downloads.html', 'Инструкция, каталог и материалы для конкретной покупки.')],
        'downloads': [('Подготовиться к укладке', 'installation.html', 'Основание, подложка, подогрев и соединение панелей.'), ('Согласовать работу', 'installers.html', 'Короткий список вопросов для разговора с мастером.')],
        'faq': [('Посмотреть конструкцию', 'about.html#layers', 'Разберите панель по слоям и узнайте, за что отвечает каждый.'), ('Задать свой вопрос', 'contacts.html', 'Обсудите с представителем конкретный декор и ваше помещение.')],
    }
    return '<section class="ev-section ev-next-reading"><div class="ev-wrap"><span class="ev-eyebrow">Продолжить знакомство</span><div class="ev-next-grid">'+''.join(f'<a class="ev-link-card" href="{escape(href(url,page))}"><h2>{title}</h2><p>{text}</p><span class="ev-text-link">Перейти <span aria-hidden="true">↗</span></span></a>' for title,url,text in choices[key])+'</div></div></section>'
