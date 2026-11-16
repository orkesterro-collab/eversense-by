/* No network or Sheet writes: exercise the shared feed's price/taxonomy boundary. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const warnings=[];
const ctx={window:{},document:{currentScript:null,readyState:'loading',body:null,addEventListener(){},dispatchEvent(){},getElementById(){return null},createElement(){return {}},head:{appendChild(){}}},URLSearchParams,Intl,Date,console:{warn(...args){warnings.push(args);}},CustomEvent:function(){},setInterval(){},setTimeout(){}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(require.resolve('../assets/prices.js'),'utf8'),ctx);
const feed=(c,cols)=>ctx.window.EversensePriceFeed({status:'ok',table:{cols,rows:[{c:c.map(v=>({v}))}]}});
feed(['EL153',65.66,50.96,'2099-11-29','2020-01-01',100,' Светлый; Бежевый, Светлый ','Однотонные']);
assert.equal(ctx.window.EversensePrices.get('EL153').normal,65.66);
assert.equal(ctx.window.EversensePrices.get('EL153').sale,50.96);
assert.equal(JSON.stringify(ctx.window.EversensePrices.getFilters('EL153')),'{"tones":["light","beige"],"design":"plain"}');
feed(['EL153',65.66,null,null,null,100,'Белый, Тёмный','Под камень']);
assert.equal(JSON.stringify(ctx.window.EversensePrices.getFilters('EL153')),'{"tones":["white","dark"],"design":"stone"}');
feed(['EL153',65.66,null,null,null,100]);
assert.equal(ctx.window.EversensePrices.getFilters('EL153').tones,null);
assert.equal(ctx.window.EversensePrices.getFilters('EL153').design,null);
feed(['EL153',65.66,null,null,null,100,'Светлый, неизвестный','invalid']);
assert.equal(JSON.stringify(ctx.window.EversensePrices.getFilters('EL153')),'{"tones":["light"],"design":""}');
assert.equal(warnings.length,2);
assert.equal(ctx.window.EversensePrices.get('EL153').normal,65.66);
for(const empty of [null,'','  ', ' , ; \n ; ']){
  feed(['EL153',65.66,null,null,null,100,empty,'   ']);
  assert.equal(JSON.stringify(ctx.window.EversensePrices.getFilters('EL153')),'{"tones":[],"design":""}');
}
// GViz may omit trailing blank cells, but declared columns make them explicit clears.
feed(['EL153',65.66,null,null,null,100],Array.from({length:8},()=>({})));
assert.equal(JSON.stringify(ctx.window.EversensePrices.getFilters('EL153')),'{"tones":[],"design":""}');
feed(['EL153',65.66,null,null,null,100],Array.from({length:6},()=>({})));
assert.equal(JSON.stringify(ctx.window.EversensePrices.getFilters('EL153')),'{"tones":null,"design":null}');
feed(['EL153',65.66,null,null,null,100,'неизвестный','invalid']);
assert.equal(JSON.stringify(ctx.window.EversensePrices.getFilters('EL153')),'{"tones":[],"design":""}');
ctx.window.EversensePriceFeed({status:'error'});
assert.equal(ctx.window.EversensePrices.get('EL153').normal,65.66);
console.log('Passed: price preservation, multi-tone parsing, live group override, explicit blank/invalid clearing, mixed-token retention, schema-only fallback and failed refresh.');
