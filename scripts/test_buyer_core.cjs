/* Run: node scripts/test_buyer_core.cjs. No network or production data writes. */
'use strict';
const assert = require('node:assert/strict');
const core = require('../assets/buyer-core.js');
const products = require('../assets/products-data.json');

let checks = 0;
function test(name, fn) {
  fn();
  checks += 1;
  process.stdout.write(`ok ${checks} - ${name}\n`);
}
function hasError(...args) {
  assert.equal(typeof core.calculate(...args).error, 'string');
}

test('catalog has 30 unique canonical SKU records', () => {
  assert.equal(products.length, 30);
  assert.equal(new Set(products.map(p => p.sku)).size, 30);
  for (const product of products) {
    assert.match(product.sku, /^EL\d{3,4}$/);
    assert.ok(product.packArea > 0 && Number.isFinite(product.packArea));
  }
});

const sku = products.slice(0, 4).map(p => p.sku);
test('shared selection normalizes case and whitespace and removes duplicates', () => {
  assert.deepEqual(core.cleanItems(` ${sku[0].toLowerCase()},${sku[1]},${sku[0]}, `, products, 30), sku.slice(0, 2));
});
test('unknown, HTML and URL-looking SKU are never admitted', () => {
  const value = ['EL999999', '<script>alert(1)</script>', 'javascript:alert(1)', 'https://example.com', '%', null, 42, {}, sku[2]];
  assert.deepEqual(core.cleanItems(value, products, 30), [sku[2]]);
});
test('comparison limit is three while favorites can retain four or all thirty', () => {
  assert.deepEqual(core.cleanItems(sku, products, 3), sku.slice(0, 3));
  assert.deepEqual(core.cleanItems(sku, products, 30), sku);
  assert.equal(core.cleanItems(products.map(p => p.sku), products, 30).length, 30);
});
test('cleaning damaged storage values is safe and does not mutate the input', () => {
  for (const value of [null, undefined, 42, {}, true]) assert.deepEqual(core.cleanItems(value, products, 3), []);
  const input = [sku[0], sku[0], sku[1]];
  const before = input.slice();
  core.cleanItems(input, products, 3);
  assert.deepEqual(input, before);
});
test('query decoding delegates only verified values to the whitelist', () => {
  const query = new URLSearchParams(`items=${sku[0]}%2C%20${sku[1]}%2C%3Cscript%3E%2C%25E0%25A4%25A`);
  assert.deepEqual(core.cleanItems(query.get('items'), products, 30), sku.slice(0, 2));
});
test('decimal input accepts Russian comma and four fractional places', () => {
  assert.equal(core.parseDecimal(' 20,5 '), 20.5);
  assert.equal(core.parseDecimal('1.2345'), 1.2345);
  assert.equal(core.parseDecimal(0), 0);
});
test('decimal input rejects ambiguous, nonnumeric and coercible structured values', () => {
  for (const value of ['', ' ', null, undefined, '-1', '1e3', 'Infinity', Infinity, NaN, '1.2.3', '1,2,3', '1.23456', [1], {}, true]) {
    assert.equal(core.parseDecimal(value), null, String(value));
  }
});

const goldens = [
  {name: 'A: normal purchase', input: ['20', '10', 1.99, 45.90], expected: {packs: 12, neededArea: 22, purchasedArea: 23.88, totalCents: 109609}},
  {name: 'B: exact pack boundary', input: ['18', '0', 3.00, 52.35], expected: {packs: 6, neededArea: 18, purchasedArea: 18, totalCents: 94230}},
  {name: 'C: reserve must not round down before counting packs', input: ['1.81', '10', 1.99, 17.95], expected: {packs: 2, neededArea: 1.991, purchasedArea: 3.98, totalCents: 7144}},
  {name: 'D: exact half kopek rounds up', input: ['1.5', '0', 1.99, 25.50], expected: {packs: 1, neededArea: 1.5, purchasedArea: 1.99, totalCents: 5075}}
];
for (const fixture of goldens) test(fixture.name, () => {
  const actual = core.calculate(...fixture.input);
  assert.ok(!actual.error);
  for (const [key, expected] of Object.entries(fixture.expected)) assert.equal(actual[key], expected, key);
});
test('full input price precision is preserved until the final material total', () => {
  assert.equal(core.calculate(2, 0, 1, 1.005).totalCents, 201);
  assert.equal(core.calculate(1, 0, 1, 1.005).totalCents, 101);
  assert.equal(core.calculate(10, 0, 1, 0.001).totalCents, 1);
});
test('no price yields quantity but never an invented zero total', () => {
  for (const value of [null, undefined, 0, -1, NaN, Infinity, '45.90', {}]) {
    const result = core.calculate(20, 10, 1.99, value);
    assert.equal(result.packs, 12);
    assert.equal(result.totalCents, null);
  }
});
test('unrepresentable monetary totals degrade to price unavailable', () => {
  const result = core.calculate(100000, 20, 1.99, 1e308);
  assert.ok(Number.isSafeInteger(result.packs) && result.packs > 0);
  assert.equal(result.totalCents, null);
});
test('invalid areas and reserve percentages produce explicit validation errors', () => {
  for (const area of ['', 0, -1, 100000.0001, Infinity, '1e3']) hasError(area, 10, 1.99, 10);
  for (const reserve of ['', -1, 20.0001, 21, Infinity]) hasError(20, reserve, 1.99, 10);
  assert.ok(!core.calculate(0.0001, 0, 1.99, 10).error);
  assert.ok(!core.calculate(100000, 20, 1.99, 10).error);
});
test('missing, nonpositive and unsafe pack quantities cannot create NaN or zero packs', () => {
  for (const packArea of [null, undefined, '', 0, -1, 'broken', Infinity, '1' + '0'.repeat(308)]) {
    hasError(20, 10, packArea, 10);
  }
});
test('every actual pack size keeps exact boundaries and rounds one tick above them up', () => {
  for (const area of new Set(products.map(p => p.packArea))) {
    const packUnits = Math.round(area * 10000);
    for (const packs of [1, 2, 3, 7, 19, 100]) {
      const exact = ((packUnits * packs) / 10000).toFixed(4);
      const below = ((packUnits * packs - 1) / 10000).toFixed(4);
      const above = ((packUnits * packs + 1) / 10000).toFixed(4);
      assert.equal(core.calculate(exact, 0, area, null).packs, packs, `${area}: exact ${exact}`);
      assert.equal(core.calculate(below, 0, area, null).packs, packs, `${area}: below ${below}`);
      assert.equal(core.calculate(above, 0, area, null).packs, packs + 1, `${area}: above ${above}`);
    }
  }
});
test('20 percent reserve at an exact boundary does not add a spurious pack', () => {
  const result = core.calculate('4.975', '20', '1.99', 25.50);
  assert.equal(result.neededArea, 5.97);
  assert.equal(result.packs, 3);
  assert.equal(result.purchasedArea, 5.97);
  assert.equal(result.totalCents, 15224);
});

process.stdout.write(`\n${checks} test groups passed.\n`);
