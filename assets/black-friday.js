/* EVERSENSE / Black Friday 2026: retail-only landing page. Prices come
   from the public sheet "price". No private credentials or hidden discounts. */
(function(){
"use strict";
const SHEET_ID="1zzypRi-wST20xu0rns-uSnGk7NmikkW2kw44jvsDgBY";
const START="2026-11-04", END="2026-11-29";
const cards=[...document.querySelectorAll("[data-promo-sku]")];
function minskDate(){
 const o={};new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/Minsk",day:"2-digit",month:"2-digit",year:"numeric"}).formatToParts(new Date()).forEach(p=>{o[p.type]=p.value});
 return o.year+"-"+o.month+"-"+o.day;
}
function money(n){return Number(n).toLocaleString("ru-RU",{minimumFractionDigits:2,maximumFractionDigits:2})+" BYN/м²";}
function value(c,i){return c&&c[i]&&c[i].v;}
function fmt(c,i){return c&&c[i]&&c[i].f;}
function positive(raw){let n=Number(String(raw??"").replace(/[\s\u00a0\u202f]/g,"").replace(",","."));return Number.isFinite(n)&&n>0?n:null;}
function date(raw,formatted){
 const s=String(raw??"");let m=s.match(/^Date\((\d{4}),(\d{1,2}),(\d{1,2})/);
 if(m)return m[1]+"-"+String(Number(m[2])+1).padStart(2,"0")+"-"+m[3].padStart(2,"0");
 m=s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
 if(m)return m[1]+"-"+m[2].padStart(2,"0")+"-"+m[3].padStart(2,"0");
 if(formatted&&formatted!==s)return date(formatted);
 return null;
}
function render(prices){
 const now=minskDate(),expired=now>END;
 cards.forEach(card=>{
   const id=card.dataset.promoSku,p=prices[id],box=card.querySelector(".bf-card__prices");
   if(!box)return;
   if(!p){if(expired)box.innerHTML='<strong>Цена уточняется</strong>';return;}
   const until=p.until||END,start=p.start||START;
   const special=!!(p.sale&&p.sale<p.price&&now<=until);
   box.classList.toggle("is-expired",!special);
   box.replaceChildren();
   if(special){
     const old=document.createElement("del");old.textContent=money(p.price);box.append(old);
     const newPrice=document.createElement("strong");newPrice.textContent=money(p.sale);box.append(newPrice);
     const label=document.createElement("span");label.textContent="до "+Number(until.slice(8,10))+"."+until.slice(5,7);box.append(label);
   }else{
     const normal=document.createElement("strong");normal.textContent=money(p.price);box.append(normal);
   }
 });
 if(expired){
   document.querySelectorAll(".bf-hero__end").forEach(x=>x.textContent="АКЦИЯ ЗАВЕРШЕНА 29 НОЯБРЯ 2026 ГОДА");
   document.querySelectorAll(".bf-hero__offer").forEach(x=>{x.style.display="none"});
   const h=document.querySelector(".bf-hero__lead");if(h)h.textContent="Ноябрьская акция завершена. Выберите понравившийся декор и уточните актуальную цену в каталоге.";
 }
}
window.EversensePromoFeed=function(payload){
 if(payload?.status!=="ok"||!Array.isArray(payload.table?.rows))return;
 const prices=Object.create(null);
 for(const row of payload.table.rows){
   const c=row.c||[],sku=String(value(c,0)||"").trim().toUpperCase();
   if(!/^EL\d{3,4}$/.test(sku))continue;
   const price=positive(value(c,1)),sale=positive(value(c,2));
   if(price)prices[sku]={price,sale,until:date(value(c,3),fmt(c,3)),start:date(value(c,4),fmt(c,4))};
 }
 render(prices);
};
const script=document.createElement("script");
script.src="https://docs.google.com/spreadsheets/d/"+SHEET_ID+"/gviz/tq?"+new URLSearchParams({tqx:"out:json;responseHandler:EversensePromoFeed",sheet:"price",headers:"1",tq:"select A,C,D,E,F",v:String(Date.now())}).toString();
document.head.append(script);
// On a network failure, never keep expired static promotional prices visible.
if(minskDate()>END)render(Object.create(null));
})();