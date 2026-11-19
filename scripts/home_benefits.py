"""Prepare the mobile artwork and captions of the five homepage benefits."""
import posixpath
import re


RU_RECORDS = ('1028577696', '1028577701', '1028577706', '1028577716', '1028577721')
EN_RECORDS = ('1040271696', '1040271701', '1040271706', '1040271711', '1040271716')
# All photographs come from the site's existing EVERSENSE imagery.
MOBILE_PHOTOS = (
    ('intro', '793f54aaa5b5-textures_2000_1.webp'),
    ('warranty', '9319855e8cff-_2-min.webp'),
    ('water', '6e9fe83a853f-__-min.webp'),
    ('wear', 'c7ca08eeb95d-_1_2-min.webp'),
    ('impact', 'e52e5803e60a-_5-min.webp'),
)
COPY = {'1746691102171': 'heading', '1746691102174': 'subheading',
        '1744019111686': 'brand', '1742902620650': 'heading',
        '1742902620663': 'body', '1742902620666': 'body',
        '1746691721257': 'body', '1746692581724': 'body', '1744025494094': 'icon'}
ELEMENT = re.compile(r"""<div\b(?=[^>]*\bdata-elem-id=['"](?P<id>\d+)['"])[^>]+>\s*"""
                     r"""<(?P<atom>div|a|h[1-6])\b[^>]*\bclass=['"]tn-atom['"][^>]*>.*?</(?P=atom)>\s*</div>""", re.S)
END_BOARD = re.compile(r"""\s*</div>\s*</div>\s*<script>t_onFuncLoad\('t396_initialScale'""")
TRANSPARENT = 'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs='


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
    assets = posixpath.relpath('assets', posixpath.dirname(page) or '.')
    for record, (kind, filename) in zip(EN_RECORDS if english else RU_RECORDS, MOBILE_PHOTOS):
        record_start = source.index(f'<div id="rec{record}"')
        tag_end = source.index('>', record_start) + 1
        tag = source[record_start:tag_end]
        if 'data-ev-benefit=' in tag:
            continue
        marker = f'<div class="t396__filter" data-artboard-recid="{record}"></div>'
        start = source.index(marker, tag_end) + len(marker)
        end = END_BOARD.search(source, start).start()
        body = source[start:end]
        if 'class="ev-benefit-copy"' not in body:
            body = group_original_elements(body, english)
            tag = tag.replace('class="r t-rec', 'class="r t-rec ev-benefit-slide ev-benefit-original-size', 1)

        # Keep the desktop background. A hidden, lazy native picture also selects
        # the right mobile source in the carousel's cloned slides and on rotation.
        picture = (f'<picture class="ev-benefit-mobile-image" hidden aria-hidden="true">'
                   f'<source media="(max-width: 959px)" srcset="{assets}/original-tilda/{filename}">'
                   f'<img src="{TRANSPARENT}" alt="" loading="lazy" decoding="async"></picture>')
        photo = next(element for element in ELEMENT.finditer(body) if element['id'] == '1742902666215')
        insert = body.rindex('</div>', photo.start(), photo.end())
        body = body[:insert] + picture + body[insert:]
        source = (source[:record_start] + tag[:-1] + f' data-ev-benefit="{kind}">' +
                  source[tag_end:start] + body + source[end:])

    if 'home-benefits-carousel.css' not in source:
        # Tilda sets the desktop scale on direct children. The original EN
        # elements keep that same scale after they are grouped for mobile.
        styles = ('<style>@media (min-width: 960px){.ev-benefit-original-size .t396__artboard_scale '
                  ':is(.ev-benefit-copy,.ev-benefit-controls) > .t396__elem{zoom:var(--zoom,1)}}</style>'
                  f'<link rel="stylesheet" media="(max-width: 959px)" '
                  f'href="{assets}/home-benefits-carousel.css?v=20261119mobile">')
        source = source.replace('</head>', styles + '</head>', 1)
    source = re.sub(r'(home-benefits-carousel\.css\?v=)[\w-]+', r'\g<1>20261119mobile', source)
    return source
