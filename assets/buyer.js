/* EVERSENSE buyer tools. Product facts are generated from the official catalog. */
(function(){
  'use strict';
  if(window.__eversenseBuyerStarted) return;
  var source=document.currentScript;
  var base=new URL('../',source.src);
  var products=(window.EversenseCatalogData||[]).slice().sort(function(a,b){return ['nature','luxury','minimal'].indexOf(a.collectionID)-['nature','luxury','minimal'].indexOf(b.collectionID)||Number(a.sku.slice(2))-Number(b.sku.slice(2));});
  var core=window.EversenseBuyerCore;
  if(!core||!products.length)return;
  window.__eversenseBuyerStarted=true;
  var route=function(path){return new URL(path.replace(/^\//,''),base).href;};
  var bySku=new Map(products.map(function(p){return [p.sku,p];}));
  var esc=function(value){return String(value==null?'':value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});};
  var number=function(n,max){return n.toLocaleString('ru-RU',{maximumFractionDigits:max==null?2:max});};
  var money=function(n){return n.toLocaleString('ru-RU',{minimumFractionDigits:2,maximumFractionDigits:2});};
  var fullName=function(p){return p.name||[p.family,p.shade].filter(Boolean).join(' ');};
  var params=new URLSearchParams(location.search);
  // Explicit fallback state stays authoritative even if a tiny probe or a
  // later single-key write succeeds: another selection may still be unsaved.
  var storageAvailable=!params.has('ev-favorites');
  // Readable storage may still reject writes (quota/private mode). Detect that
  // before restoring URL fallback state on the next page.
  try{var probe='eversense.storage-probe.v1',prior=localStorage.getItem(probe);localStorage.setItem(probe,'1');if(prior===null)localStorage.removeItem(probe);else localStorage.setItem(probe,prior);}catch(e){storageAvailable=false;}
  function read(key,limit){var raw;try{raw=localStorage.getItem(key)||'[]';}catch(e){storageAvailable=false;return [];}try{return core.cleanItems(JSON.parse(raw),products,limit);}catch(e){return [];}}
  var favorites=read('eversense.favorites.v1',30);
  if(!storageAvailable&&params.has('ev-favorites'))favorites=core.cleanItems(params.get('ev-favorites'),products,30);
  var imported=params.has('items')?core.cleanItems(params.get('items'),products,30):null;
  var pageName=document.body.dataset.buyerPage||'';
  function persist(key,value){try{localStorage.setItem(key,JSON.stringify(value));}catch(e){storageAvailable=false;}}
  function announce(text){
    var box=document.getElementById('ev-buyer-status');
    if(!box){box=document.createElement('div');box.id='ev-buyer-status';box.className='ev-live-status';box.setAttribute('role','status');box.setAttribute('aria-live','polite');document.body.appendChild(box);}
    box.textContent=text;box.hidden=false;
    clearTimeout(announce.timer);announce.timer=setTimeout(function(){box.hidden=true;},5000);
  }
  function activePrice(sku){var p=window.EversensePrices&&window.EversensePrices.get(sku);return p?(p.sale||p.normal):null;}
  function priceHtml(sku){
    var p=window.EversensePrices&&window.EversensePrices.get(sku);
    if(!p)return '<span class="ev-price-pending">Цена уточняется</span>';
    var current=money(p.sale||p.normal)+' BYN/м²';
    var previous=p.sale?'<del>'+money(p.normal)+'</del> ':'';
    var until=p.sale&&p.until?'<small>Акция до '+esc(p.until.split('-').reverse().join('.'))+'</small>':'';
    if(pageName==='catalog'||pageName==='favorites'){
      var priceClass=p.sale?'ev-price-sale':'ev-price-normal';
      return '<strong class="'+priceClass+'">'+current+'</strong>'+previous+until;
    }
    return previous+'<strong>'+current+'</strong>'+until;
  }
  function buttons(p,allowCalculate){return '<div class="ev-card-actions"><button class="ev-button" type="button" data-ev-favorite="'+p.sku+'" aria-pressed="false">В избранное</button>'+(allowCalculate?'<a class="ev-button" href="'+route('calculator.html')+'?sku='+encodeURIComponent(p.sku)+'">Рассчитать</a>':'')+'</div>';}
  /* EV_RESPONSIVE_START */
  var responsiveImages={"/assets/original-tilda/01a5c5f16366-EL2190___ver1_top-mi.webp":1680,"/assets/original-tilda/07d87b8312a9-__-min.webp":1680,"/assets/original-tilda/0c228f6e6d3a-_-1-min.webp":1680,"/assets/original-tilda/0e171125bb3c-_-1-min.webp":1680,"/assets/original-tilda/15f2b2143e0f-_-3-min.webp":1680,"/assets/original-tilda/188a91ad894e-_-1-min.webp":1680,"/assets/original-tilda/221462659c8d-EL1047____ver1_top-m.webp":1680,"/assets/original-tilda/2627c6aebc9e-_-1-min.webp":1680,"/assets/original-tilda/276c5c954956-_-1-min.webp":1680,"/assets/original-tilda/2958945c9e13-EL1050___-_ver1_top-.webp":1680,"/assets/original-tilda/2aaaa4339bae-EL1038____ver1_top-m.webp":1680,"/assets/original-tilda/30ad52e3d4e3-EL1039____ver1_top-m.webp":1680,"/assets/original-tilda/313d56a1a5fa-_--min.webp":1680,"/assets/original-tilda/39eccaaf7460-EL2150____ver1_top-m.webp":1680,"/assets/original-tilda/5752cbf8286d-EL1048____ver1_top-m.webp":1680,"/assets/original-tilda/59c866ccd6f5-EL2170____ver1_top-m.webp":1680,"/assets/original-tilda/59ca17cfb340-_-min.webp":1680,"/assets/original-tilda/5b45d88e0333-EL1041_____ver1_top-.webp":1680,"/assets/original-tilda/62ed51dbc0df-_-1-min.webp":1680,"/assets/original-tilda/68926a6287cd-_EL750_-2-min.webp":1680,"/assets/original-tilda/69a2bd1029cc-EL2151_____ver1_top-.webp":1680,"/assets/original-tilda/6b5ec6aa3c3a-EL1002___ver1_top-mi.webp":1680,"/assets/original-tilda/6c4cb656294c-EL1036____ver1_top-m.webp":1680,"/assets/original-tilda/6eef62f94cd4-EL1053____ver1_top-m.webp":1680,"/assets/original-tilda/71790aee3dc2-EL1044____ver1_top-m.webp":1680,"/assets/original-tilda/71bae444c7a8-__-min.webp":1680,"/assets/original-tilda/824da7b32934-__-1-min.webp":1680,"/assets/original-tilda/8528d0440ac0-EL1000___ver1_top-mi.webp":1680,"/assets/original-tilda/8613c6c7dc0f-_-min.webp":1680,"/assets/original-tilda/86a2371a094d-EL2152____ver1_top-m.webp":1680,"/assets/original-tilda/8ce9a355c101-EL1046_____ver1_top-.webp":1680,"/assets/original-tilda/8f2f91961524-EL1049____ver1_top-m.webp":1680,"/assets/original-tilda/9172533304ae-_-1-min.webp":1680,"/assets/original-tilda/935e11546197-_-min.webp":1680,"/assets/original-tilda/9b60d4d34a96-_-min.webp":1680,"/assets/original-tilda/9db832bb8968-EL1040____ver1_top-m.webp":1680,"/assets/original-tilda/a3061e70133a-EL1045____ver1_top-m.webp":1680,"/assets/original-tilda/a4e61edb12c0-A2190_Bedroom04_fron.webp":1680,"/assets/original-tilda/a6152eb83895-EL2171____ver1_top-m.webp":1680,"/assets/original-tilda/a6908199fe1b-EL1054____ver1_top-m.webp":1680,"/assets/original-tilda/ad0c6e75f260-_-min.webp":1680,"/assets/original-tilda/b07fb52f913a-_-min.webp":1680,"/assets/original-tilda/b43c3df596a6-EL1037_____ver1_top-.webp":1680,"/assets/original-tilda/b572561dead9-__-min.webp":1680,"/assets/original-tilda/bba0287e4a5a-_-1-min.webp":1680,"/assets/original-tilda/be59eb1ec84c-_-1-min.webp":1680,"/assets/original-tilda/bfd854ede1c4-_-1-min.webp":1680,"/assets/original-tilda/c2de9d8b2136-EL1043____ver1_top-m.webp":1680,"/assets/original-tilda/caf9f0ec9c58-EL1049_R1049_Kitchen.webp":1680,"/assets/original-tilda/ce635ae9f66a-EL153___ver1_top-min.webp":1680,"/assets/original-tilda/cf62865e7dbb-_-1-min.webp":1680,"/assets/original-tilda/cf8d4a4bf1a2-El1052____ver1_top-m.webp":1680,"/assets/original-tilda/d00a2b3e4818-_-min.webp":1680,"/assets/original-tilda/d055377b4d0a-__-1-min.webp":1680,"/assets/original-tilda/e35797186861-__-1-min.webp":1680,"/assets/original-tilda/ed642c78d089-EL2153____ver1_top-m.webp":1680,"/assets/original-tilda/f30cf85356ba-__-1-min.webp":1680,"/assets/original-tilda/f41c2d5d4ba1-EL1051_____ver1_top-.webp":1680,"/assets/original-tilda/f9cbba8d1844-__EL750_-_ver1__top-.webp":1680,"/assets/original-tilda/ff23b8576315-EL2173____ver1_top-m.webp":1680};
  /* EV_RESPONSIVE_END */
  function imageAttrs(path,sizes){
    var width=responsiveImages[path];
    if(!width)return ' decoding="async"';
    var variant=path.replace('/original-tilda/','/responsive/').replace(/\.webp$/,'');
    var set=[route(variant+'-480.webp')+' 480w',route(variant+'-960.webp')+' 960w',route(path)+' '+width+'w'];
    return ' decoding="async" srcset="'+esc(set.join(', '))+'" sizes="'+esc(sizes)+'"';
  }
  function card(p,allowCalculate){return '<article class="ev-card" data-product="'+p.sku+'"><a class="ev-card-image" href="'+route(p.canonicalPath)+'"><img src="'+route(p.productImage)+'"'+imageAttrs(p.productImage,'(max-width: 640px) calc(100vw - 40px), (max-width: 1050px) calc((100vw - 64px) / 2), 400px')+' alt="'+esc(fullName(p))+'" loading="lazy" width="640" height="500">'+(p.interiorImage?'<img class="ev-card-interior" src="'+route(p.interiorImage)+'"'+imageAttrs(p.interiorImage,'(max-width: 640px) calc(100vw - 40px), (max-width: 1050px) calc((100vw - 64px) / 2), 400px')+' alt="" loading="lazy" width="640" height="500">':'')+'</a><div class="ev-card-body"><span class="ev-sku">'+p.sku+'</span><h2 class="ev-card-title"><a href="'+route(p.canonicalPath)+'">'+esc(fullName(p))+'</a></h2><p class="ev-card-meta">'+esc(p.collectionName)+' · '+p.lengthMM+' × '+p.widthMM+' мм</p><div class="ev-price-box" data-buyer-price="'+p.sku+'">'+priceHtml(p.sku)+'</div>'+buttons(p,allowCalculate)+'</div></article>';}
  function syncButtons(){
    document.querySelectorAll('[data-ev-favorite]').forEach(function(button){
      var on=favorites.includes(button.dataset.evFavorite);
      button.setAttribute('aria-pressed',String(on));
      if(!button.classList.contains('ev-card-favorite'))button.textContent=on?'В избранном':'В избранное';
    });
    var favoriteSummary='Избранное - '+(favorites.length?favorites.length+' шт.':'пока пусто');
    document.querySelectorAll('[data-favorites-summary]').forEach(function(n){n.textContent=favoriteSummary;});
    document.querySelectorAll('[data-favorites-count]').forEach(function(n){n.textContent=String(favorites.length);});
    document.querySelectorAll('[data-favorites-link]').forEach(function(a){a.classList.toggle('has-favorites',favorites.length>0);a.setAttribute('aria-label',favoriteSummary);});
    if(!storageAvailable)document.querySelectorAll('a[href]').forEach(function(a){var u;try{u=new URL(a.href);}catch(e){return;}if(u.origin!==base.origin||!u.pathname.startsWith(base.pathname)||a.getAttribute('href').startsWith('#'))return;u.searchParams.set('ev-favorites',favorites.join(','));a.href=u.href;});
    if(!storageAvailable){var current=new URL(location.href);current.searchParams.set('ev-favorites',favorites.join(','));history.replaceState(null,'',current);}
  }
  function updatePrices(){
    document.querySelectorAll('[data-buyer-price]').forEach(function(n){n.innerHTML=priceHtml(n.dataset.buyerPrice);});
    var calc=document.getElementById('ev-calc-form');if(calc&&calc.dataset.calculated==='true')renderCalculation(false);
  }
  function toggleFavorite(sku){
    if(!bySku.has(sku))return;
    var root=document.getElementById('ev-favorites'),selector='[data-ev-favorite]';
    var index=root?Array.from(root.querySelectorAll(selector)).indexOf(document.activeElement):-1;
    var existing=favorites.indexOf(sku);
    if(existing>=0)favorites.splice(existing,1);else favorites.push(sku);
    persist('eversense.favorites.v1',favorites);
    if(pageName==='favorites'&&imported===null)renderFavorites();
    syncButtons();
    if(index>=0&&!document.activeElement.closest(selector)){
      var remaining=root.querySelectorAll(selector),next=remaining[Math.min(index,remaining.length-1)]||root.querySelector('a');
      if(next)next.focus({preventScroll:true});
    }
    announce(existing>=0?'Декор убран из избранного.':'Декор добавлен в избранное.');
    if(!storageAvailable)announce('Выбор сохранён на этой странице. Чтобы не потерять его, скопируйте ссылку на подборку.');
  }
  function selectedList(){return imported!==null?imported:favorites;}
  function renderFavorites(){
    var root=document.getElementById('ev-favorites');if(!root)return;
    var list=selectedList();
    if(list.length){
      var templates=document.getElementById('ev-favorite-cards').content;
      var grid=document.createElement('div');
      grid.className='ev-grid';
      list.forEach(function(sku){
        var source=templates.querySelector('[data-product="'+sku+'"]');
        var savedCard=document.importNode(source,true);
        savedCard.querySelector('[data-buyer-price]').innerHTML=priceHtml(sku);
        grid.appendChild(savedCard);
      });
      root.replaceChildren(grid);
    }else{
      root.innerHTML='<div class="ev-empty"><h2>Здесь будут ваши декоры</h2><p>Отметьте понравившиеся варианты в каталоге, чтобы вернуться к ним и показать продавцу.</p><a class="ev-button ev-button--primary" href="'+route('catalog-ru/')+'">Выбрать декор</a></div>';
    }
    var shared=document.getElementById('ev-shared-note');if(shared)shared.hidden=imported===null;
    document.querySelectorAll('[data-share-selection]').forEach(function(b){b.disabled=!list.length;});
    var count=document.getElementById('ev-favorite-total');if(count)count.textContent=number(list.length);
    syncButtons();
  }
  function renderCalculation(focus){
    var form=document.getElementById('ev-calc-form');if(!form)return;
    var sku=form.elements.sku.value,p=bySku.get(sku),root=document.getElementById('ev-calc-result');
    if(!p){root.innerHTML='<p>Выберите декор для расчёта.</p>';return;}
    var result=core.calculate(form.elements.area.value,form.elements.reserve.value,p.packArea,activePrice(sku));
    if(result.error){root.innerHTML='<p class="ev-error" role="alert">'+esc(result.error)+'</p>';form.dataset.calculated='false';return;}
    form.dataset.calculated='true';
    root.innerHTML='<span class="ev-eyebrow">'+esc(fullName(p))+' · '+p.sku+'</span><h2>'+result.packs+' <small>уп.</small></h2><dl class="ev-calc-values"><div><dt>С выбранным запасом</dt><dd>'+number(result.neededArea,4)+' м²</dd></div><div><dt>В целых упаковках</dt><dd>'+number(result.purchasedArea,4)+' м²</dd></div><div><dt>В одной упаковке</dt><dd>'+number(p.packArea,4)+' м² / '+p.packCount+' шт.</dd></div><div><dt>Стоимость материала</dt><dd>'+(result.totalCents===null?'Уточнить цену':money(result.totalCents/100)+' BYN')+'</dd></div></dl><p class="ev-note">Расчёт включает только покрытие. Подложка, плинтусы, доставка и монтаж рассчитываются отдельно. Количество уточните по плану помещения и выбранной раскладке.</p><div class="ev-actions"><a class="ev-button ev-button--primary" href="'+route('contacts.html')+'?sku='+sku+'&packs='+result.packs+'">Уточнить наличие</a><button class="ev-text-link" type="button" data-share-calculation>Скопировать расчёт</button></div>';
    var url=new URL(location.href);url.searchParams.set('sku',sku);url.searchParams.set('area',form.elements.area.value);url.searchParams.set('reserve',form.elements.reserve.value);history.replaceState(null,'',url);
    syncButtons();
    if(focus){root.focus({preventScroll:true});if(window.innerWidth<750)root.scrollIntoView({behavior:'smooth',block:'start'});}
  }
  function mountCalculator(){
    var form=document.getElementById('ev-calc-form');if(!form)return;
    var s=params.get('sku');if(bySku.has(s))form.elements.sku.value=s;
    if(params.has('area')&&core.parseDecimal(params.get('area'))!==null)form.elements.area.value=params.get('area');
    if(params.has('reserve')&&core.parseDecimal(params.get('reserve'))!==null)form.elements.reserve.value=params.get('reserve');
    function preview(){var p=bySku.get(form.elements.sku.value),el=document.getElementById('ev-calc-product');if(p&&el)el.innerHTML='<img src="'+route(p.productImage)+'"'+imageAttrs(p.productImage,'(max-width: 640px) calc(100vw - 40px), 360px')+' alt="'+esc(fullName(p))+'" width="360" height="240"><p>'+p.sku+' · '+p.lengthMM+' × '+p.widthMM+' × '+p.thicknessMM+' мм<br>'+number(p.packArea,4)+' м² в упаковке</p>';}
    form.addEventListener('submit',function(e){e.preventDefault();renderCalculation(true);});
    form.addEventListener('input',function(){if(form.dataset.calculated==='true'){form.dataset.calculated='false';document.getElementById('ev-calc-result').innerHTML='<p>Данные изменились. Нажмите «Рассчитать», чтобы обновить результат.</p>';}});
    form.elements.sku.addEventListener('change',preview);preview();
    if(params.has('area'))renderCalculation(false);
  }
  function matchesTone(p,tone){if(!tone)return true;if(tone==='light')return p.tags.tone==='light';var patterns={natural:/натуральн/i,gray:/сер/i,brown:/коричнев/i,beige:/беж/i};return !!(patterns[tone]&&patterns[tone].test(p.shade||''));}
  function mountCatalog(){
    var form=document.getElementById('ev-catalog-filters'),root=document.getElementById('ev-catalog-results');if(!form||!root)return;
    // Keep links saved from the former collection dropdown working through the collection pages.
    var legacyCollection=params.get('collection');
    if(legacyCollection&&!document.body.dataset.collection){
      var collectionProduct=products.find(function(product){return product.collectionID===legacyCollection;});
      if(collectionProduct){
        var collectionUrl=new URL(location.href);
        collectionUrl.pathname=new URL('../',route(collectionProduct.canonicalPath)).pathname;
        collectionUrl.searchParams.delete('collection');
        location.replace(collectionUrl.href);
        return;
      }
    }

    var keys=['q','tone','design'];
    var cards=Array.from(root.querySelectorAll('[data-product]'));
    var empty=document.getElementById('ev-catalog-empty');
    var status=document.getElementById('ev-catalog-status');
    var reset=form.querySelector('[data-reset-filters]');
    if(!empty||!status||!reset)return;

    keys.forEach(function(key){
      var field=form.elements.namedItem(key);
      if(!field||!params.has(key))return;
      field.value=params.get(key);
      if(field.selectedIndex===-1)field.selectedIndex=0;
    });

    function draw(){
      var filters=new FormData(form);
      var search=filters.get('q').trim().toLocaleLowerCase('ru');
      var tone=filters.get('tone'),design=filters.get('design');
      var count=0;
      cards.forEach(function(card){
        var product=bySku.get(card.dataset.product);
        var searchable=(product.sku+' '+fullName(product)+' '+product.collectionName).toLocaleLowerCase('ru');
        var matches=matchesTone(product,tone)&&(!design||product.tags.design===design)&&
          searchable.includes(search);
        card.hidden=!matches;
        if(matches)count++;
      });
      empty.hidden=count>0;
      reset.hidden=!(search||tone||design);
      var message=reset.hidden?'':count?'Декоров в выдаче: '+count:'Таких декоров не найдено';
      if(status.textContent!==message)status.textContent=message;

      var url=new URL(location.href);
      keys.forEach(function(key){
        var value=(filters.get(key)||'').trim();
        if(value)url.searchParams.set(key,value);else url.searchParams.delete(key);
      });
      url.searchParams.delete('collection');
      url.searchParams.delete('sort');
      if(url.href!==location.href)history.replaceState(history.state,'',url);
    }

    form.addEventListener('submit',function(e){e.preventDefault();draw();});
    form.addEventListener('input',draw);form.addEventListener('change',draw);
    reset.addEventListener('click',function(){
      form.reset();
      form.elements.q.focus({preventScroll:true});
      draw();
    });
    draw();
  }
  function mountFinder(){
    var form=document.getElementById('ev-finder');if(!form)return;
    form.addEventListener('submit',function(e){e.preventDefault();
      var data=new FormData(form),tone=data.get('tone'),design=data.get('design'),room=data.get('room');
      var matches=products.filter(function(p){return matchesTone(p,tone)&&(!design||p.tags.design===design);});
      var root=document.getElementById('ev-finder-results');
      var roomAdvice={kitchen:'Для кухни особенно важны правильная укладка и быстрое удаление пролитой жидкости.',hall:'В прихожей предусмотрите грязезащитный коврик: песок и мелкие камни могут повреждать поверхность.',bedroom:'Оцените оттенок при вечернем освещении и проверьте совместимость покрытия с подложкой.',living:'Сравните несколько планок рядом с мебелью: отдельный образец не показывает весь рисунок пола.'};
      root.innerHTML='<h2>Декоры по вашим предпочтениям</h2><p>'+esc(roomAdvice[room]||'Оцените выбранные декоры на физическом образце.')+' Подбор учитывает дизайн и оттенок; требования к монтажу и эксплуатации остаются общими для продукта.</p>'+(matches.length?'<div class="ev-grid">'+matches.slice(0,6).map(card).join('')+'</div><a class="ev-button" href="'+route('catalog-ru/')+'?tone='+encodeURIComponent(tone||'')+'&design='+encodeURIComponent(design||'')+'">Все подходящие декоры ('+matches.length+')</a>':'<p>Точного сочетания сейчас нет. Попробуйте изменить один из параметров.</p>');
      root.hidden=false;syncButtons();root.focus({preventScroll:true});root.scrollIntoView({behavior:'smooth',block:'start'});
    });
  }
  function mountProduct(){
    var path=location.pathname.replace(/\/index\.html$/,'/');
    var p=products.find(function(product){return new URL(route(product.canonicalPath)).pathname===path;});
    if(!p)return;
    function insert(){
      if(document.getElementById('ev-product-tools'))return true;
      var price=document.getElementById('ev-product-price');if(!price)return false;
      var section=document.createElement('section');section.id='ev-product-tools';section.className='ev-tools-panel ev-buyer';
      section.innerHTML='<div class="ev-wrap"><div class="ev-actions"><a class="ev-button ev-button--primary" href="'+route('calculator.html')+'?sku='+p.sku+'">Рассчитать упаковки</a>'+buttons(p)+'</div><div class="ev-swatch-row"><a href="'+route('favorites.html')+'"><span data-favorites-summary>Избранное - пока пусто</span></a><a href="'+route('choose.html')+'#sample">Как проверить образец</a></div></div>';
      var gallery=price.previousElementSibling;
      // Accept both current and cached versions of the price loader.
      if(!gallery||!gallery.matches('.t-rec')||!gallery.querySelector('[role="img"]'))gallery=price.nextElementSibling;
      if(gallery&&gallery.matches('.t-rec')&&gallery.querySelector('[role="img"]'))gallery.insertAdjacentElement('afterend',section);
      else price.insertAdjacentElement('afterend',section);
      section.querySelector('.ev-wrap').prepend(price);
      var support=document.createElement('section');support.id='ev-product-support';support.className='ev-tools-panel ev-buyer';support.innerHTML='<div class="ev-wrap"><span class="ev-eyebrow">Перед покупкой</span><h2>Всё важное об этом покрытии</h2><div class="ev-link-grid">'+[['Конструкция и свойства','about.html','Из чего состоит EVERSENSE и что важно в эксплуатации.'],['Укладка и тёплый пол','installation.html','Основание, подложка и подготовка к монтажу.'],['Уход и гарантия','care.html','Ежедневный уход и обращение при повреждении.']].map(function(a){return '<a class="ev-link-card" href="'+route(a[1])+'"><h3>'+a[0]+'</h3><p>'+a[2]+'</p><span aria-hidden="true">↗</span></a>';}).join('')+'</div><div class="ev-actions"><a class="ev-text-link" href="'+route('downloads.html')+'">Документы EVERSENSE</a><a class="ev-text-link" href="'+route('warranty.html')+'">Условия гарантии</a><a class="ev-text-link" href="'+route('faq.html')+'">Ответы на вопросы</a></div></div>';
      var footer=document.querySelector('#t-footer,.t-footer');if(footer)footer.before(support);else document.body.appendChild(support);
      syncButtons();return true;
    }
    if(!insert()){var observer=new MutationObserver(function(){if(insert())observer.disconnect();});observer.observe(document.body,{childList:true,subtree:true});setTimeout(function(){observer.disconnect();},15000);}
  }
  function mountContact(){
    var el=document.getElementById('ev-contact-selection'),p=bySku.get(params.get('sku'));if(!el||!p)return;
    var count=Number(params.get('packs'));
    el.hidden=false;el.innerHTML='<span class="ev-eyebrow">Выбранный декор</span><h2>'+esc(fullName(p))+'</h2><p><b>'+p.sku+'</b>'+(Number.isSafeInteger(count)&&count>0&&count<100000?' · '+count+' уп.':'')+'</p><p>Назовите артикул при обращении: так проще проверить цену, наличие и возможность посмотреть образец.</p>';
  }
  function copy(text){
    if(navigator.clipboard&&window.isSecureContext)navigator.clipboard.writeText(text).then(function(){announce('Ссылка скопирована.');},function(){manualCopy(text);});
    else manualCopy(text);
  }
  function manualCopy(text){var el=document.getElementById('ev-copy-fallback');if(!el){el=document.createElement('div');el.id='ev-copy-fallback';el.className='ev-copy-box ev-buyer';el.innerHTML='<label>Скопируйте ссылку<input readonly aria-label="Ссылка на подборку"></label><button type="button" class="ev-button" data-close-copy>Закрыть</button>';document.body.appendChild(el);}el.hidden=false;var input=el.querySelector('input');input.value=text;input.focus();input.select();announce('Ссылка готова: выделите и скопируйте её.');}
  document.addEventListener('click',function(e){
    var favorite=e.target.closest('[data-ev-favorite]');
    if(favorite){e.preventDefault();toggleFavorite(favorite.dataset.evFavorite);}
    if(e.target.closest('[data-share-selection]'))copy(route('favorites.html')+'?items='+selectedList().join(','));
    if(e.target.closest('[data-share-calculation]'))copy(location.href);
    if(e.target.closest('[data-print]'))window.print();
    if(e.target.closest('[data-close-copy]'))document.getElementById('ev-copy-fallback').hidden=true;
    if(e.target.closest('[data-save-shared]')){favorites=core.cleanItems(favorites.concat(imported||[]),products,30);persist('eversense.favorites.v1',favorites);syncButtons();announce('Декоры добавлены в ваше избранное.');}
  });
  document.addEventListener('eversense:prices',updatePrices);
  document.addEventListener('eversense:header-ready',syncButtons);
  window.addEventListener('pageshow',function(){if(storageAvailable)favorites=read('eversense.favorites.v1',30);if(pageName==='favorites'&&imported===null)renderFavorites();syncButtons();});
  window.addEventListener('storage',function(e){if(!storageAvailable)return;if(e.key===null||e.key==='eversense.favorites.v1'){favorites=read('eversense.favorites.v1',30);if(pageName==='favorites'&&imported===null)renderFavorites();}syncButtons();});
  function boot(){mountCatalog();mountCalculator();mountFinder();mountProduct();mountContact();renderFavorites();syncButtons();updatePrices();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
