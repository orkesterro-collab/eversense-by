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
    return (p.sale?'<del>'+money(p.normal)+'</del> ':'')+'<strong>'+money(p.sale||p.normal)+' BYN/м²</strong>'+(p.sale&&p.until?'<small>Акция до '+esc(p.until.split('-').reverse().join('.'))+'</small>':'');
  }
  function buttons(p,allowCalculate){return '<div class="ev-card-actions"><button class="ev-button" type="button" data-ev-favorite="'+p.sku+'" aria-pressed="false">В избранное</button>'+(allowCalculate?'<a class="ev-button" href="'+route('calculator.html')+'?sku='+encodeURIComponent(p.sku)+'">Рассчитать</a>':'')+'</div>';}
  function card(p,allowCalculate){return '<article class="ev-card" data-product="'+p.sku+'"><a class="ev-card-image" href="'+route(p.canonicalPath)+'"><img src="'+route(p.productImage)+'" alt="'+esc(fullName(p))+'" loading="lazy" width="640" height="500">'+(p.interiorImage?'<img class="ev-card-interior" src="'+route(p.interiorImage)+'" alt="" loading="lazy" width="640" height="500">':'')+'</a><div class="ev-card-body"><span class="ev-sku">'+p.sku+'</span><h2 class="ev-card-title"><a href="'+route(p.canonicalPath)+'">'+esc(fullName(p))+'</a></h2><p class="ev-card-meta">'+esc(p.collectionName)+' · '+p.lengthMM+' × '+p.widthMM+' мм</p><div class="ev-price-box" data-buyer-price="'+p.sku+'">'+priceHtml(p.sku)+'</div>'+buttons(p,allowCalculate)+'</div></article>';}
  function syncButtons(){
    document.querySelectorAll('[data-ev-favorite]').forEach(function(b){var on=favorites.includes(b.dataset.evFavorite);b.setAttribute('aria-pressed',String(on));b.textContent=on?'В избранном':'В избранное';});
    document.querySelectorAll('[data-favorites-count]').forEach(function(n){n.textContent=String(favorites.length);});
    document.querySelectorAll('[data-favorites-link]').forEach(function(a){a.classList.toggle('has-favorites',favorites.length>0);});
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
    root.innerHTML=list.length?'<div class="ev-grid">'+list.map(function(s){return card(bySku.get(s),true);}).join('')+'</div>':'<div class="ev-empty"><h2>Здесь будут ваши декоры</h2><p>Отметьте понравившиеся варианты в каталоге, чтобы вернуться к ним и показать продавцу.</p><a class="ev-button ev-button--primary" href="'+route('catalog-ru/')+'">Выбрать декор</a></div>';
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
    function preview(){var p=bySku.get(form.elements.sku.value),el=document.getElementById('ev-calc-product');if(p&&el)el.innerHTML='<img src="'+route(p.productImage)+'" alt="'+esc(fullName(p))+'" width="360" height="240"><p>'+p.sku+' · '+p.lengthMM+' × '+p.widthMM+' × '+p.thicknessMM+' мм<br>'+number(p.packArea,4)+' м² в упаковке</p>';}
    form.addEventListener('submit',function(e){e.preventDefault();renderCalculation(true);});
    form.addEventListener('input',function(){if(form.dataset.calculated==='true'){form.dataset.calculated='false';document.getElementById('ev-calc-result').innerHTML='<p>Данные изменились. Нажмите «Рассчитать», чтобы обновить результат.</p>';}});
    form.elements.sku.addEventListener('change',preview);preview();
    if(params.has('area'))renderCalculation(false);
  }
  function matchesTone(p,tone){if(!tone)return true;if(tone==='light')return p.tags.tone==='light';var patterns={natural:/натуральн/i,gray:/сер/i,brown:/коричнев/i,beige:/беж/i};return !!(patterns[tone]&&patterns[tone].test(p.shade||''));}
  function mountCatalog(){
    var form=document.getElementById('ev-catalog-filters'),root=document.getElementById('ev-catalog-results');if(!form||!root)return;
    var collection=document.body.dataset.collection||'';
    var filterDetails=form.querySelector('.ev-filter-details');
    var compact=window.matchMedia('(max-width:760px)');
    function fitFilters(){if(filterDetails)filterDetails.open=!compact.matches;}fitFilters();
    if(compact.addEventListener)compact.addEventListener('change',fitFilters);
    ['q','tone','design','sort'].forEach(function(key){if(form.elements[key]&&params.has(key))form.elements[key].value=params.get(key);});
    if(form.elements.collection&&params.has('collection'))form.elements.collection.value=params.get('collection');
    function draw(){
      var search=form.elements.q.value.toLocaleLowerCase('ru').trim();
      var f=function(k){return form.elements[k]?form.elements[k].value:'';};
      var items=products.filter(function(p){return (!collection||p.collectionID===collection)&&(!f('collection')||p.collectionID===f('collection'))&&matchesTone(p,f('tone'))&&(!f('design')||p.tags.design===f('design'))&&(!search||(p.sku+' '+fullName(p)+' '+p.collectionName).toLocaleLowerCase('ru').includes(search));});
      var sort=f('sort');if(sort==='name')items.sort(function(a,b){return fullName(a).localeCompare(fullName(b),'ru');});
      if(sort==='price-up'||sort==='price-down')items.sort(function(a,b){var x=activePrice(a.sku),y=activePrice(b.sku);if(x===null)return y===null?0:1;if(y===null)return -1;return sort==='price-up'?x-y:y-x;});
      root.innerHTML=items.length?items.map(card).join(''):'<div class="ev-empty"><h2>Таких декоров не найдено</h2><p>Попробуйте другой оттенок или уберите часть фильтров.</p><button type="button" class="ev-button" data-reset-filters>Сбросить фильтры</button></div>';
      document.getElementById('ev-result-count').textContent='Найдено декоров: '+items.length;
      var u=new URL(location.href);['q','collection','tone','design','sort'].forEach(function(k){var v=f(k);if(v)u.searchParams.set(k,v);else u.searchParams.delete(k);});history.replaceState(null,'',u);
      syncButtons();
    }
    form.addEventListener('submit',function(e){e.preventDefault();draw();});
    form.addEventListener('input',draw);form.addEventListener('change',draw);
    document.addEventListener('click',function(e){if(e.target.closest('[data-reset-filters]')){form.reset();draw();}});
    document.addEventListener('eversense:prices',function(){if(/^price/.test(form.elements.sort.value))draw();});
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
      section.innerHTML='<div class="ev-wrap"><div class="ev-actions"><a class="ev-button ev-button--primary" href="'+route('contacts.html')+'?sku='+p.sku+'">Уточнить наличие</a><a class="ev-button" href="'+route('calculator.html')+'?sku='+p.sku+'">Рассчитать упаковки</a>'+buttons(p)+'</div><div class="ev-swatch-row"><a href="'+route('favorites.html')+'">Избранное (<span data-favorites-count>0</span>)</a><a href="'+route('choose.html')+'#sample">Как проверить образец</a></div></div>';
      var gallery=price.nextElementSibling;
      if(gallery&&gallery.matches('.t-rec')&&gallery.querySelector('[role="img"]'))gallery.insertAdjacentElement('afterend',section);
      else price.insertAdjacentElement('afterend',section);
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
  window.addEventListener('storage',function(e){if(!storageAvailable)return;if(e.key===null||e.key==='eversense.favorites.v1'){favorites=read('eversense.favorites.v1',30);if(pageName==='favorites'&&imported===null)renderFavorites();}syncButtons();});
  function boot(){mountCatalog();mountCalculator();mountFinder();mountProduct();mountContact();renderFavorites();syncButtons();updatePrices();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();
