"""Link the five original homepage photographs to their buyer guides."""
import posixpath
import re


RU_RECORDS = ('1028577696', '1028577701', '1028577706', '1028577716', '1028577721')
EN_RECORDS = ('1040271696', '1040271701', '1040271706', '1040271711', '1040271716')
BENEFITS = (
    ('intro', '102a0149d479-_1-min.webp', 'about.html#surface',
     'Как оценить фактуру и цвет пола', 'How to judge the texture and colour of flooring'),
    ('warranty', '9319855e8cff-_2-min.webp', 'warranty.html',
     'Условия гарантии EVERSENSE', 'EVERSENSE warranty terms'),
    ('water', '8bdd7b9eaba5-_3-min.webp', 'water-resistance.html',
     'Влагостойкость EVERSENSE и 72 часа контакта с водой', 'Water resistance and the 72-hour claim'),
    ('wear', 'ea69fbde8dca-_4-min.webp', 'laminate-classes.html#abrasion',
     'Как проверяют стойкость пола к истиранию', 'How flooring is tested for wear'),
    ('impact', 'e52e5803e60a-_5-min.webp', 'laminate-classes.html#impact-resistance',
     'Как проверяют ударопрочность пола', 'How flooring is tested for impact resistance'),
)
PHONE_COPY = {
    'intro': ('Все ощущения от деревянного пола —', 'без эксплуатационных минусов'),
    'warranty': ('Расчетливая гарантия', 'Ваши внуки вырастут прежде, чем закончится гарантия на пол. Гарантия — 30 лет безупречной работы.'),
    'water': ('Практичная водонепроницаемость', 'Не стоит переживать, если вы опрокинете на пол вазу с цветами. EVERSENSE выдерживает 72 часа в контакте с водой.'),
    'wear': ('Стойкость к износу', 'Если вы любите танго, смело танцуйте на EVERSENSE. Покрытие соответствует 34 классу использования. Стойкость к истиранию — не менее 8 500 оборотов.'),
    'impact': ('Способность держать удар', 'У EVERSENSE высокая ударная прочность поверхности — в соответствии с нормами EN 13329 / EN 15468.'),
}
PHONE_CAPTION = re.compile(r'<!-- ev-benefit-phone -->.*?<!-- /ev-benefit-phone -->', re.S)
COPY = {'1746691102171': 'heading', '1746691102174': 'subheading',
        '1744019111686': 'brand', '1742902620650': 'heading',
        '1742902620663': 'body', '1742902620666': 'body',
        '1746691721257': 'body', '1746692581724': 'body', '1744025494094': 'icon'}
ELEMENT = re.compile(r"""<div\b(?=[^>]*\bdata-elem-id=['"](?P<id>\d+)['"])[^>]+>\s*"""
                     r"""<(?P<atom>div|a|h[1-6])\b[^>]*\bclass=['"]tn-atom['"][^>]*>.*?</(?P=atom)>\s*</div>""", re.S)
END_BOARD = re.compile(r"""\s*</div>\s*</div>\s*<script>t_onFuncLoad\('t396_initialScale'""")
UNLINKED_TITLE = re.compile(r"""(<h2\b[^>]*\bfield=['"]tn_text_(?:1746691102171|1742902620650)['"][^>]*>)"""
                            r"""(?!\s*<a\b)(.*?)(</h2>)""", re.S)
# Match the original photo atom, including the alternate mobile picture in
# the compact export. Preserve the outer Tilda element and its desktop geometry.
PHOTO_CONTENT = re.compile(
    r"""(<div\b[^>]*\bdata-elem-id=['"]1742902666215['"][^>]*>)\s*"""
    r"""<(div|a)\b[^>]*>.*?</\2>\s*(?:<picture\b[^>]*>.*?</picture>\s*)?(?=</div>)""", re.S)


def with_role(node, role):
    return re.sub(r"""(\bclass=['"])""", r'\g<1>ev-benefit-' + role + ' ', node, count=1)


def group_original_elements(body, english):
    """The original English export has the same fields as the grouped RU slides."""
    copy, controls, photos = [], [], []
    if ELEMENT.sub('', body).strip():
        raise ValueError('Unrecognized content in benefits artboard')
    for element in ELEMENT.finditer(body):
        node, field = element[0], element['id']
        if field in COPY:
            copy.append(with_role(node, COPY[field]))
        elif field == '1742902666215':
            photos.append(with_role(node, 'photo'))
        else:
            if 'prevButton ' in node:
                role = 'prev'
            elif 'nextButton ' in node:
                role = 'next'
            elif 'ar_left.svg' in node:
                role = 'prev-icon'
            elif 'ar_right.svg' in node:
                role = 'next-icon'
            elif 'href="#bullet' in node:
                role = 'dot'
            else:
                raise ValueError('Unknown benefit control ' + field)
            controls.append(with_role(node, role))
    label = 'Choose a slide' if english else 'Переключение слайдов'
    return ('<div class="ev-benefit-copy">' + ''.join(copy) + '</div>' +
            f'<div class="ev-benefit-controls" role="group" aria-label="{label}">' +
            ''.join(controls) + '</div>' + ''.join(photos))


def make_home_benefits(source, page):
    english = page == 'en/index.html'
    directory = posixpath.dirname(page) or '.'
    assets = posixpath.relpath('assets', directory)
    for record, (kind, filename, article, ru_label, en_label) in zip(EN_RECORDS if english else RU_RECORDS, BENEFITS):
        record_start = source.index(f'<div id="rec{record}"')
        tag_end = source.index('>', record_start) + 1
        tag = source[record_start:tag_end]
        marker = f'<div class="t396__filter" data-artboard-recid="{record}"></div>'
        start = source.index(marker, tag_end) + len(marker)
        end = END_BOARD.search(source, start).start()
        body = source[start:end]
        if 'class="ev-benefit-copy"' not in body:
            body = group_original_elements(body, english)
            tag = tag.replace('class="r t-rec', 'class="r t-rec ev-benefit-slide ev-benefit-original-size', 1)

        if 'data-ev-benefit=' not in tag:
            tag = tag[:-1] + f' data-ev-benefit="{kind}">'
        label = en_label + ' (in Russian)' if english else ru_label
        target = posixpath.relpath(article, directory)
        title_link = f'<a class="ev-home-article-link" href="{target}" hreflang="ru" aria-label="{label}">'
        body = UNLINKED_TITLE.sub(lambda m: m[1] + title_link + m[2] + '</a>' + m[3], body)
        if not english:
            title, description = PHONE_COPY[kind]
            brand = '<p class="ev-m-brand">EVERSENSE.</p>' if kind != 'intro' else ''
            caption = (f'<!-- ev-benefit-phone --><div class="ev-m-caption">{brand}<h2>{title}</h2>'
                       f'<p>{description}</p><a class="ev-m-read" href="{target}" '
                       f'aria-label="Узнать больше — {title}">Узнать больше <span aria-hidden="true">→</span></a>'
                       '</div><!-- /ev-benefit-phone -->')
            start_copy = '<div class="ev-benefit-copy">'
            body = PHONE_CAPTION.sub('', body).replace(start_copy, start_copy + caption, 1)
        photo = (f'<a class="tn-atom ev-benefit-article" href="{target}" hreflang="ru">'
                 f'<img src="{assets}/original-tilda/{filename}" alt="{label}" '
                 f'width="1680" height="1820" loading="lazy" decoding="async" draggable="false"></a>')
        body, count = PHOTO_CONTENT.subn(lambda match: match[1] + photo, body)
        if count != 1:
            raise ValueError(f'Expected one photograph in benefit {record}, found {count}')
        source = source[:record_start] + tag + source[tag_end:start] + body + source[end:]

    if 'home-benefits-carousel.css' not in source:
        # Tilda sets the desktop scale on direct children. The original EN
        # elements keep that same scale after they are grouped for mobile.
        styles = ('<style>@media (min-width: 960px){.ev-benefit-original-size .t396__artboard_scale '
                  ':is(.ev-benefit-copy,.ev-benefit-controls) > .t396__elem{zoom:var(--zoom,1)}}</style>'
                  f'<link rel="stylesheet" media="(max-width: 959px)" '
                  f'href="{assets}/home-benefits-carousel.css?v=20261119mobile">')
        source = source.replace('</head>', styles + '</head>', 1)
    if 'id="ev-home-article-links-css"' not in source:
        source = source.replace('</head>', f'<link id="ev-home-article-links-css" rel="stylesheet" '
                                f'href="{assets}/home-article-links.css?v=20261119photos"></head>', 1)
    source = re.sub(r'(home-(?:benefits-carousel|article-links)\.css\?v=)[\w-]+', r'\g<1>20261119photos', source)
    return source
