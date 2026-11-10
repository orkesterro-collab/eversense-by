/* Shared header loader for every mirrored page. */
(function(){
  if (window.__evHeaderLoaderQueued) return;
  window.__evHeaderLoaderQueued = true;
  var current = document.currentScript;
  if (!current || !current.src) return;
  var script = document.createElement("script");
  script.src = new URL("unified-header.js?v=20261110b",current.src).href;
  script.async = true;
  document.head.appendChild(script);
})();
/* EVERSENSE Беларусь: публичный прайс Google Sheets. Не хранит ключей/паролей.
   Схема листа price: sku | name | price | sale_price | sale_until | sale_from */
(function () {
  "use strict";
  if(window.EversensePrices)return;
  var SHEET_ID = "1zzypRi-wST20xu0rns-uSnGk7NmikkW2kw44jvsDgBY";
  var table = Object.create(null), loaded = false, timer = null;

  function number(v) {
    if (v === null || v === undefined || v === "") return null;
    var t = String(v).replace(/[\s\u00a0\u202f]|BYN|Br|руб\.?/gi, "").replace(",", ".").trim();
    var n = Number(t);
    return Number.isFinite(n) && n > 0 ? n : null;
  }
  function date(v, formatted) {
    if (v === null || v === undefined || v === "") return null;
    var str = String(v);
    var m = /^Date\((\d{4}),(\d{1,2}),(\d{1,2})\)/.exec(str);
    if (m) return [m[1], String(Number(m[2])+1).padStart(2,"0"),m[3].padStart(2,"0")].join("-");
    m = /^(\d{4})-(\d{1,2})-(\d{1,2})/.exec(str);
    if (m) return [m[1],m[2].padStart(2,"0"),m[3].padStart(2,"0")].join("-");
    m = /^(\d{1,2})\.(\d{1,2})\.(\d{4})$/.exec(str);
    if (m) return [m[3],m[2].padStart(2,"0"),m[1].padStart(2,"0")].join("-");
    if (formatted && formatted !== str) return date(formatted);
    return null;
  }
  function todayMinsk() {
    var parts = new Intl.DateTimeFormat("en-GB",{
      timeZone:"Europe/Minsk",year:"numeric",month:"2-digit",day:"2-digit"
    }).formatToParts(new Date()), data={};
    parts.forEach(function (p) { data[p.type]=p.value; });
    return data.year+"-"+data.month+"-"+data.day;
  }
  function activePrice(sku) {
    var d=table[String(sku||"").toUpperCase()];
    if (!d || !d.price) return null;
    var today=todayMinsk();
    var saleActive=!!(d.sale && d.sale<d.price && d.until && d.until>=today && (!d.from || d.from<=today));
    return {normal:d.price, sale:saleActive?d.sale:null,until:d.until,from:d.from};
  }
  function money(n) {
    return n.toLocaleString("ru-RU",{minimumFractionDigits:2,maximumFractionDigits:2})+" BYN/м²";
  }
  function el(tag,className,value) {
    var n=document.createElement(tag);n.className=className;
    if(value!==undefined)n.textContent=value;
    return n;
  }
  function block(sku,kind) {
    var p=activePrice(sku);
    var box=el("div","ev-price-box ev-price-box--"+kind);
    box.dataset.evSku=sku;
    if (!p) {
      if(kind==="product"||kind==="alternate")box.append(el("span","ev-price-pending","Цена уточняется"));
      return box;
    }
    if (p.sale) {
      box.append(el("del","ev-price-before",money(p.normal)));
      box.append(el("strong","ev-price-sale",money(p.sale)));
      var until=p.until.split("-");
      box.append(el("span","ev-price-until","до "+Number(until[2])+"."+until[1]));
    } else {
      box.append(el("strong","ev-price-normal",money(p.normal)));
    }
    return box;
  }
  function tildaSkuNodes() {
    return document.querySelectorAll(".t396__elem[data-elem-type='text'] > .tn-atom, .t396__elem[data-elem-type='text'] > h2.tn-atom");
  }
  function renderTilda() {
    var nodes=tildaSkuNodes(), isProduct=/\/catalog-(ru|en)\/[^/]+\/[^/]+\/?(?:index\.html)?$/.test(location.pathname);
    if (isProduct) {
      // Once the price panel exists, keep it synchronized even if Tilda changes SKU nodes.
      var existingPanel=document.getElementById("ev-product-price");
      if (existingPanel && existingPanel.dataset.evSku) {
        var existingBox=existingPanel.querySelector(".ev-price-box");
        if (existingBox) existingBox.remove();
        existingPanel.append(block(existingPanel.dataset.evSku,"product"));
        return;
      }
      var match=null, sku=null;
      for (var i=0;i<nodes.length;i++){
        var t=nodes[i].textContent.trim().toUpperCase();
        if(/^EL\d{3,4}$/.test(t)){sku=t;match=nodes[i];break;}
      }
      if(match && sku){
        var record=match.closest(".t-rec");
        if(record){
          var panel=document.getElementById("ev-product-price");
          if (!panel) {
            panel=el("section","ev-product-price-strip");panel.id="ev-product-price";
            panel.append(el("span","ev-price-caption","Цена за 1 м²"));
            record.insertAdjacentElement("afterend",panel);
          }
          panel.dataset.evSku=sku;
          var old=panel.querySelector(".ev-price-box");
          if(old) old.remove();
          panel.append(block(sku,"product"));
        }
      }
      return;
    }
    // Zero Block cards may have separate desktop/mobile copies of each SKU.
    for(var j=0;j<nodes.length;j++){
      var node=nodes[j], raw=node.textContent.trim().toUpperCase();
      var exact=/^EL\d{3,4}$/.exec(raw);
      if(!exact)continue;
      var parent=node.closest(".t396__elem");
      if(!parent)continue;
      var prev=parent.querySelector(":scope > .ev-price-box");
      if(prev)prev.remove();
      var badge=block(exact[0],"tile");
      if(badge.childNodes.length)parent.append(badge);
    }
  }
  function renderAlternative() {
    // Existing fallback HTML cards and individual HTML product pages.
    document.querySelectorAll(".catalog-product").forEach(function(card){
      var link=card.getAttribute("href")||"",match=link.match(/(EL\d{3,4})\.html/i);
      if(!match)return;
      var old=card.querySelector(".ev-price-box");if(old)old.remove();
      var badge=block(match[1],"tile");
      if(badge.childNodes.length)card.append(badge);
    });
    var match=location.pathname.match(/\/products\/(EL\d{3,4})\.html$/i);
    if(match) {
      var summary=document.querySelector(".product-summary");
      if(summary){
        var old=summary.querySelector(".ev-price-box");if(old)old.remove();
        var badge=block(match[1].toUpperCase(),"alternate");
        var spot=summary.querySelector(".sku")||summary.querySelector("h1");
        if(spot)spot.insertAdjacentElement("afterend",badge);
        else summary.prepend(badge);
      }
    }
  }
  function render() {
    if (!document.body)return;
    if(document.querySelector(".t-records")||document.querySelector(".t396__elem"))renderTilda();
    else renderAlternative();
  }
  window.EversensePriceFeed=function(payload){
    if(!payload||payload.status!=="ok"||!payload.table||!Array.isArray(payload.table.rows)) {
      console.warn("EVERSENSE: цены Google Sheets временно недоступны",payload&&payload.errors);
      return;
    }
    var newTable=Object.create(null);
    payload.table.rows.forEach(function(row){
      var c=row.c||[],v=function(i){return c[i]&&c[i].v;},f=function(i){return c[i]&&c[i].f;};
      var sku=String(v(0)||"").trim().toUpperCase();
      if(!/^EL\d{3,4}$/.test(sku))return;
      newTable[sku]={price:number(v(1)),sale:number(v(2)),until:date(v(3),f(3)),from:date(v(4),f(4))};
    });
    table=newTable;loaded=true;render();
    document.dispatchEvent(new CustomEvent('eversense:prices'));
    setTimeout(render,1000);
    setTimeout(render,3500);
  };
  function requestFeed() {
    var previous=document.getElementById("ev-google-price-feed");
    if(previous)previous.remove();
    var s=document.createElement("script");
    s.id="ev-google-price-feed";
    s.src="https://docs.google.com/spreadsheets/d/"+SHEET_ID+
      "/gviz/tq?"+new URLSearchParams({
        tqx:"out:json;responseHandler:EversensePriceFeed",
        sheet:"price",headers:"1",tq:"select A,C,D,E,F",
        nonce:String(Date.now())
      }).toString();
    s.onerror=function(){console.warn("EVERSENSE: нет доступа к опубликованной таблице price");};
    document.head.appendChild(s);
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",render,{once:true});
  else render();
  requestFeed();
  // Re-read without reloading the page; Google may cache its response for a few minutes.
  timer=setInterval(requestFeed,15*60*1000);
  window.EversensePrices={get:activePrice,render:render,refresh:requestFeed,isLoaded:function(){return loaded;}};
})();
