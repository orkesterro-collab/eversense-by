"""Add the production feature to the two Russian homepages, idempotently."""
from pathlib import Path
import re


def make_home_production(source):
    if 'id="rec1002600136"' not in source:
        return source
    match = re.search(r'''(?:src|href)=["']((?:\.\./)*assets/)''', source)
    if not match:
        raise ValueError('Cannot resolve homepage asset prefix')
    prefix = match[1][:-len('assets/')]
    block = f'''<!-- ev-production-feature:start -->
<section id="ev-production-feature" aria-labelledby="ev-production-heading">
  <div class="ev-production-feature-inner">
    <div class="ev-production-feature-copy">
      <p class="ev-production-feature-kicker">EVERSENSE JOURNAL · ПРОИЗВОДСТВО</p>
      <h2 id="ev-production-heading">Европейские корни.<br>Производство в Гагарине.</h2>
      <p class="ev-production-feature-lead">За фактурой дерева — опыт международной группы EGGER. От семейного предприятия в австрийском Тироле до завода, где производят EVERSENSE.</p>
      <ul><li>Известный изготовитель</li><li>Испытания по методикам EN</li><li>Документы для покупателя</li></ul>
      <a class="ev-production-feature-button" href="{prefix}production.html">Как создаётся доверие к полу <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M5 19 19 5M5 5h14v14"/></svg></a>
    </div>
    <figure><a href="{prefix}production.html" aria-label="Читать статью о производстве EVERSENSE"><img src="{prefix}assets/production/gagarin-aerial.webp" width="2000" height="1543" loading="lazy" decoding="async" alt="Панорама завода EGGER в Гагарине"></a><figcaption>Гагарин, Смоленская область · Фото: EGGER</figcaption></figure>
  </div>
</section>
<!-- ev-production-feature:end -->'''
    source = re.sub(r'<!-- ev-production-feature:start -->.*?<!-- ev-production-feature:end -->\s*', '', source, flags=re.S)
    anchor = '<div id="rec1002600136"'
    source = source.replace(anchor, block + '\n' + anchor, 1)
    if 'id="ev-home-production-css"' not in source:
        source = source.replace('</head>', f'<link id="ev-home-production-css" rel="stylesheet" href="{prefix}assets/home-production.css?v=20261116"></head>', 1)
    return source


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    for relative in ('index.html', 'ru/index.html'):
        path = root / relative
        path.write_text(make_home_production(path.read_text(encoding='utf-8')), encoding='utf-8')
        print('Updated', relative)
