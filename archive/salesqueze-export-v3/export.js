#!/usr/bin/env node
// One-shot SalesQueeze export.
//
// Reads the flat pricelist from two levels above this script:
//   <category>/<sku>/item.json        — flat item info
//   <category>/<sku>/prices.json      — price matrix (products only)
//
// Writes a single products.json next to this file with every item.
// Matrix products include their full matrix; accessories/extras include
// their flat price/cost/formula.
//
// Run:  node export.js     (no arguments, no dependencies)

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const OUT_FILE = path.join(__dirname, 'products.json');

const PRODUCTS_ROOT = 'products';
const PRODUCT_CATS = ['pergola', 'screen', 'glazing', 'awning'];
const ACCESSORY_CATS = ['accessories', 'extras'];

const readJson = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const listSkus = relDir => {
  const full = path.join(ROOT, PRODUCTS_ROOT, relDir);
  if (!fs.existsSync(full)) return [];
  return fs.readdirSync(full)
    .filter(n => fs.statSync(path.join(full, n)).isDirectory())
    .sort();
};

function summarize(matrix) {
  let min = Infinity, max = -Infinity, count = 0;
  for (const row of matrix) for (const v of row) {
    if (v == null || v === 0) continue;
    if (v < min) min = v;
    if (v > max) max = v;
    count++;
  }
  return {
    price_min: min === Infinity ? null : min,
    price_max: max === -Infinity ? null : max,
    price_count: count,
  };
}

const meta = readJson(path.join(ROOT, 'meta.json'));

// ---- Products ----
const products = [];
for (const cat of PRODUCT_CATS) {
  for (const sku of listSkus(cat)) {
    const item = readJson(path.join(ROOT, PRODUCTS_ROOT, cat, sku, 'item.json'));
    const pricesPath = path.join(ROOT, PRODUCTS_ROOT, cat, sku, 'prices.json');
    const pr = fs.existsSync(pricesPath) ? readJson(pricesPath) : null;

    const entry = {
      order: item.order,
      sku: item.sku,
      category: item.category,
      name_cs: item.name_cs,
      name_en: item.name_en,
      currency: item.currency,
      unit: item.unit,
      price: item.price,
      cost_percent: item.cost_percent,
      discount: item.discount,
      delivery_weeks: item.delivery_weeks,
      description_cs: item.description_cs,
      description_en: item.description_en,
      description_de: item.description_de,
      color_options: item.color_options,
    };

    if (pr && pr.type === 'matrix') {
      Object.assign(entry, summarize(pr.prices));
      entry.matrix = {
        horizontal_values: pr.horizontal_values,
        vertical_values: pr.vertical_values,
        prices: pr.prices,
      };
    } else if (pr && pr.type === 'multi-matrix') {
      let allMin = Infinity, allMax = -Infinity, allCount = 0;
      const variants = pr.variants.map(v => {
        const s = summarize(v.prices);
        if (s.price_min != null && s.price_min < allMin) allMin = s.price_min;
        if (s.price_max != null && s.price_max > allMax) allMax = s.price_max;
        allCount += s.price_count;
        return {
          label: v.label,
          horizontal_values: v.horizontal_values,
          vertical_values: v.vertical_values,
          prices: v.prices,
          ...s,
        };
      });
      entry.price_min = allMin === Infinity ? null : allMin;
      entry.price_max = allMax === -Infinity ? null : allMax;
      entry.price_count = allCount;
      entry.matrix = { variants };
    } else {
      entry.price_min = null;
      entry.price_max = null;
      entry.price_count = 0;
    }

    products.push(entry);
  }
}
products.sort((a, b) => {
  if (a.order != null && b.order != null) return a.order - b.order;
  if (a.order != null) return -1;
  if (b.order != null) return 1;
  return a.sku.localeCompare(b.sku);
});

// ---- Accessories + extras ----
const accessories = [];
for (const cat of ACCESSORY_CATS) {
  for (const sku of listSkus(cat)) {
    const item = readJson(path.join(ROOT, PRODUCTS_ROOT, cat, sku, 'item.json'));
    accessories.push({
      sku: item.sku,
      category: item.category,
      name_cs: item.name_cs,
      name_en: item.name_en,
      currency: item.currency,
      unit: item.unit,
      price: item.price,
      cost: item.cost,
      description_cs: item.description_cs,
      description_en: item.description_en,
      description_de: item.description_de,
    });
  }
}
accessories.sort((a, b) => a.sku.localeCompare(b.sku));

// ---- Write ----
const out = {
  exported_at: new Date().toISOString().slice(0, 10),
  source: 'pricelist-alux',
  currency: meta.currency,
  vat_included: meta.vat_included,
  product_count: products.length,
  accessory_count: accessories.filter(a => a.category === 'accessory').length,
  extra_count: accessories.filter(a => a.category === 'extra').length,
  products,
  accessories,
};

fs.writeFileSync(OUT_FILE, JSON.stringify(out, null, 2) + '\n');
console.log(`Wrote ${products.length} products + ${accessories.length} accessories/extras`);
console.log(`File: ${OUT_FILE}`);
