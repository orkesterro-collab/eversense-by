#!/usr/bin/env python3
"""Keep the three mirrored home pages static while retaining hover controls."""
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
from home_senses import make_home_senses

HOME_PATHS = ('index.html', 'ru/index.html', 'en/index.html')
LAYER_RECORDS = ('1002600136', '1040271736')
COLLECTION_RECORDS = ('1002600161', '1002600166', '1040271761', '1040271766')
COLLECTION_CONTENT = ('1742824688189', '1742824742704', '1742824688198',
                      '1742824688204', '1742824688207')


def make_static_home(source):
    offsets = []
    position = 0
    for line in source.splitlines(keepends=True):
        offsets.append(position)
        position += len(line)
    edits = []

    class HomeParser(HTMLParser):
        record = None

        def handle_starttag(self, tag, attrs):
            original_attrs = list(attrs)
            values = dict(attrs)
            if values.get('id', '').startswith('rec'):
                self.record = values['id'][3:]
            animated = (values.get('data-animate-sbs-event') in ('scroll', 'intoview')
                        or 'data-animate-style' in values)
            if animated:
                attrs = [(key, value) for key, value in attrs
                         if not key.startswith('data-animate-')]
                classes = values.get('class', '').split()
                classes = [name for name in classes if name not in
                           ('t396__elem--anim-hidden', 't-animate', 't-animate_started')]
                attrs = [(key, ' '.join(classes) if key == 'class' else value)
                         for key, value in attrs]
            if tag == 'html' and 'ev-home-static' not in values.get('class', '').split():
                attrs = [(key, value) for key, value in attrs if key != 'class']
                attrs.append(('class', (values.get('class', '') + ' ev-home-static').strip()))
            # The summary used to replace the layer descriptions during scrolling.
            # Keep both visible, placing the summary below them on wide screens.
            if values.get('data-artboard-recid') in LAYER_RECORDS:
                attrs = [(key, '690' if key == 'data-artboard-height' else value)
                         for key, value in attrs]
            tops = {'1744017596970': '490', '1742894294656': '610'}
            if values.get('data-elem-id') in tops:
                attrs = [(key, tops[values['data-elem-id']] if key == 'data-field-top-value' else value)
                         for key, value in attrs]
            # These two collection panels started 600 px above their artboards;
            # the removed scroll animation used to bring them into view.
            if (self.record in COLLECTION_RECORDS
                    and values.get('data-elem-id') in COLLECTION_CONTENT):
                attrs = [(key, str(int(value) + 600)
                          if key == 'data-field-top-value' and int(value) < 0 else value)
                         for key, value in attrs]
            if attrs != original_attrs:
                raw = self.get_starttag_text()
                replacement = '<' + tag + ''.join(' ' + key if value is None else
                    ' ' + key + '="' + escape(value, quote=True) + '"' for key, value in attrs) + '>'
                line, column = self.getpos()
                start = offsets[line - 1] + column
                edits.append((start, start + len(raw), replacement))

    # Preserve every untouched tag, script and stylesheet byte for byte.
    parser = HomeParser(convert_charrefs=False)
    parser.feed(source)
    for start, end, replacement in reversed(edits):
        source = source[:start] + replacement + source[end:]
    source = re.sub(r'<script\b[^>]*\bsrc=["\'][^"\']*SmoothScroll[^"\']*["\'][^>]*>\s*</script>',
                    '', source, flags=re.I)
    source = re.sub(r'<script\b[^>]*>\s*SmoothScroll\(\{.*?\}\)\s*;?\s*</script>',
                    '', source, flags=re.S)
    source = re.sub(r'background-attachment\s*:\s*fixed', 'background-attachment:scroll', source)
    # Keep the pre-initialization CSS in sync with Tilda's layout attributes.
    collection_top = (r'(#rec(?:' + '|'.join(COLLECTION_RECORDS) +
                      r')\s+\.tn-elem\[data-elem-id="(?:' + '|'.join(COLLECTION_CONTENT) +
                      r')"\]\{[^{}]*?\btop:calc\(50vh - 275px \+ )(-\d+)(px\);)')
    source = re.sub(collection_top,
                    lambda match: match[1] + str(int(match[2]) + 600) + match[3], source)
    if 'id="ev-home-static-style"' not in source:
        rules = ['html.ev-home-static{scroll-behavior:auto!important;scroll-snap-type:none!important}',
                 'html.ev-home-static #ev-global-header{transition:none}']
        for record in LAYER_RECORDS:
            root = '#rec' + record
            rules.append('@media(min-width:1200px){' + root + ' .t396__artboard,' + root +
                         ' .t396__filter,' + root + ' .t396__carrier{height:690px}' + root +
                         ' .tn-elem[data-elem-id="1744017596970"]{top:490px}' + root +
                         ' .tn-elem[data-elem-id="1742894294656"]{top:610px}}')
        source = source.replace('</head>', '<style id="ev-home-static-style">' +
                                ''.join(rules) + '</style></head>', 1)
    carrier_rule = 'html.ev-home-static .t396__carrier{position:absolute!important}'
    if carrier_rule not in source:
        source = source.replace('<style id="ev-home-static-style">',
                                '<style id="ev-home-static-style">' + carrier_rule, 1)
    return make_home_senses(source)


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    for relative in HOME_PATHS:
        path = root / relative
        original = path.read_text(encoding='utf-8')
        updated = make_static_home(original)
        path.write_text(updated, encoding='utf-8')
        print(relative, 'updated' if updated != original else 'already static')
