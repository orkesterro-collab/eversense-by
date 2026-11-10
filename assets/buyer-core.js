/* Shared, side-effect-free selection and quantity rules. */
(function(root,factory){
  var api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  else root.EversenseBuyerCore=api;
})(typeof window==='undefined'?globalThis:window,function(){
  'use strict';
  function cleanItems(value,products,limit){
    var known=new Set(products.map(function(p){return p.sku;}));
    if(typeof value==='string') value=value.split(',');
    if(!Array.isArray(value)) return [];
    var out=[];
    value.forEach(function(raw){
      if(typeof raw!=='string') return;
      var sku=raw.trim().toUpperCase();
      if(known.has(sku)&&out.indexOf(sku)<0&&out.length<limit) out.push(sku);
    });
    return out;
  }
  function parseDecimal(value){
    if(typeof value!=='string'&&typeof value!=='number') return null;
    var text=String(value==null?'':value).trim().replace(',','.');
    if(!/^\d+(?:\.\d{1,4})?$/.test(text)) return null;
    var n=Number(text);
    return Number.isFinite(n)?n:null;
  }
  function moneyCents(purchasedUnits,unitPrice){
    if(!Number.isFinite(unitPrice)||unitPrice<=0) return null;
    // Preserve the decimal price from the feed until the final total is rounded.
    // A premature kopek conversion changes e.g. 2 m² × 1.005 BYN from 2.01 to 2.00.
    var parts=String(unitPrice).match(/^(\d+)(?:\.(\d+))?(?:e([+-]?\d+))?$/i);
    if(!parts)return null;
    var fraction=parts[2]||'',scale=fraction.length-Number(parts[3]||0);
    var numerator=BigInt(parts[1]+fraction),denominator=10000n;
    if(scale>=0)denominator*=10n**BigInt(scale);
    else numerator*=10n**BigInt(-scale);
    numerator*=BigInt(purchasedUnits)*100n;
    var total=(numerator*2n+denominator)/(denominator*2n);
    return total<=BigInt(Number.MAX_SAFE_INTEGER)?Number(total):null;
  }
  function calculate(area,reserve,packArea,unitPrice){
    area=parseDecimal(area);reserve=parseDecimal(reserve);packArea=parseDecimal(packArea);
    if(area===null||area<=0||area>100000) return {error:'Укажите площадь больше 0 и не больше 100 000 м².'};
    if(reserve===null||reserve<0||reserve>20) return {error:'Укажите запас от 0 до 20%.'};
    if(packArea===null||packArea<=0) return {error:'Площадь упаковки этого декора нужно уточнить у продавца.'};
    // Integer units avoid an extra package at exact decimal boundaries.
    var areaUnits=Math.round(area*10000),reserveUnits=Math.round(reserve*10000),packUnits=Math.round(packArea*10000);
    if(!Number.isSafeInteger(packUnits)||packUnits<=0) return {error:'Площадь упаковки этого декора нужно уточнить у продавца.'};
    var numerator=BigInt(areaUnits)*BigInt(1000000+reserveUnits),denominator=BigInt(packUnits)*1000000n;
    var packs=Number((numerator+denominator-1n)/denominator);
    var purchasedUnits=packs*packUnits;
    // Round the final material total once, half up, to BYN kopeks.
    var totalCents=moneyCents(purchasedUnits,unitPrice);
    return {packs:packs,neededArea:Number(numerator)/10000000000,purchasedArea:purchasedUnits/10000,extraArea:(purchasedUnits-areaUnits)/10000,totalCents:totalCents};
  }
  return {cleanItems:cleanItems,parseDecimal:parseDecimal,calculate:calculate};
});
