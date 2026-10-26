# Pricelist consumers (briefing pro Claude Code)

> Krátký integration guide pro Claude Code instance v **jiných projektech** (web configurator, quoting tool, Raynet sync, …) které potřebují číst tento pricelist.

## Co tu je

Centrální ALUX pricelist. Single source of truth: 27 položek (pergoly, výplně, příslušenství, služby).

Repo: **`davidopatsky/pricelist-01`** (GitHub, **private** — fetch vyžaduje token).

## 1. Hlavní database

```
https://raw.githubusercontent.com/davidopatsky/pricelist-01/main/pricelist.json
```

JSON array, každý objekt má N polí (aktuálně 16, může přibývat — apps by měly číst po klíčích, ne po indexech):

```json
{
  "sku": "alux-bioclimatic",
  "category": "pergola",
  "name": "ALUX Bioclimatic",
  "name_en": "ALUX Bioclimatic",
  "description": "Bioklimatická pergola...",
  "standard_price": 1,
  "price_formula": "matrix",
  "currency": "CZK",
  "unit": "ks",
  "cost": 1,
  "cost_percent": 58,
  "discount": "0-22%",
  "delivery_weeks": "7-8",
  "color_summary": "RAL 7016 + RAL 9006",
  "raynet_description": "<p>HTML pro Raynet...</p>",
  "raynet_cost": null
}
```

`name_en` je volitelné — pokud je `null`, fallback na `name`.

`category` je jeden z: `pergola` / `maxi` / `vypln` / `prislusenstvi` / `elektro` / `priplatky` / `profily` / `sluzba`. SKU je join key.

## 2. ⚠️ Pricing convention — POVINNÉ ČÍST

**`standard_price = 1` je magic placeholder, NE reálná cena 1 CZK.**

Skutečná cena vychází z **kombinace** `standard_price` + `price_formula`:

| `standard_price` | `price_formula` | význam | co s tím |
|---|---|---|---|
| číslo (≠ 1) | `null` | **fixní cena** | použij `standard_price` přímo |
| `1` | `"matrix"` | **maticová cena** | fetchni `prices.json` produktu a vyhledej podle dimenzí |
| `1` | `"<text>"` | **formula** | aplikuj vzorec (např. `"4% from price"`) |
| `1` | `null` | **placeholder (TBD)** | cena ještě není známá → zobraz "na vyžádání" |
| `null` | `null` | **bez ceny** | nemá smysl prodávat samostatně |

Když uvidíš `standard_price === 1`, **nikdy** to nezobrazuj jako "1 CZK". Vždy se podívej na `price_formula`.

## 3. Per-product files (jen pro maticové / prose-rich produkty)

Každý SKU má složku `products/<category>/<sku>/`:

```
https://raw.githubusercontent.com/davidopatsky/pricelist-01/main/products/<category>/<sku>/prices.json
https://raw.githubusercontent.com/davidopatsky/pricelist-01/main/products/<category>/<sku>/metadata.json
https://raw.githubusercontent.com/davidopatsky/pricelist-01/main/products/<category>/<sku>/knowledge.md
```

### `prices.json` (jen pro produkty s `price_formula === "matrix"`)

**Single matrix:**
```json
{
  "type": "matrix",
  "horizontal_values": [2390, 2590, ...],   // šířky v mm
  "vertical_values":   [2000, 2100, ...],   // hloubky v mm
  "prices": [
    [81928, 84692, ...],
    ...
  ]
}
```

`prices[verticalIndex][horizontalIndex]` = cena v **CZK bez DPH**. `null` nebo `0` = "není dostupné v této dimenzi".

**Multi-matrix** (zasklení s 2D/3D/4D variantami):
```json
{
  "type": "multi-matrix",
  "variants": [
    { "label": "2D", "horizontal_values": [...], "vertical_values": [...], "prices": [...] },
    ...
  ]
}
```

### `metadata.json` (volitelné, jen pro produkty se strukturovanými daty)

Obsahuje `axes`, `horizontal_footer` (např. počet lamel), `display_name_cs`, `accessories_compatible`, u pergol `support_zones` a `standard_colors`, u markýz s dvojitým provedením `double_unit`. Neexistuje pro jednoduché položky (např. `montaz`, `stojna-*`).

**`support_zones`** (pergoly) — zóny stojen pro zvýraznění v matici. Pole pravidel, vyhodnocují se **shora dolů, platí první, které sedí**. Když nesedí žádné → 2 stojny (bez zvýraznění).

| Klíč | Typ | Význam |
|---|---|---|
| `stojny` | číslo, povinné | počet stojen (2, 3 nebo 4; u pergol 2 jen spolu s `pricky`, u `maxi` i samotné) |
| `pricky` | bool, nepovinné (výchozí `false`) | + výztuha |
| `strecha` | `"uno"` / `"duo"`, nepovinné (jen kategorie `maxi`) | UNO = střecha bez středového nosníku (krokve rovnoběžně s hloubkou, spád dopředu); DUO = se středovým nosníkem (sedlový spád do boků, krokve rovnoběžně se šířkou) |
| `sirka_od` / `sirka_do` | mm, včetně, nepovinné | šířka = vodorovná osa matice |
| `hloubka_od` / `hloubka_do` | mm, včetně, nepovinné | hloubka = svislá osa matice |
| `popisek` | text, nepovinné | vlastní text do legendy; jinak se složí sám, např. „3× stojna + výztuha“ |

Chybějící mez = bez omezení.

```json
"support_zones": [
  { "stojny": 3, "pricky": true, "hloubka_od": 4500 },
  { "stojny": 3, "sirka_od": 5100 }
]
```

U Strad je cena příček (výztuhy) v zónách s `"pricky": true` už započtena v cenách matice — nepřičítat znovu.

**ALUX MAXI (`category: "maxi"`)** — zóny pokrývají **celou** matici a jsou zapsané horními mezemi (`sirka_do`, `hloubka_do`) od nejmenší: platí první, do které rozměr spadá, poslední zóna = max. rozměr. Každá zóna má `strecha` (UNO / DUO) a `popisek`; v legendě zobrazit i zónu se 2 stojnami (liší se UNO / DUO).

```json
"support_zones": [
  { "stojny": 2, "strecha": "uno", "sirka_do": 7500, "hloubka_do": 5000, "popisek": "UNO - 2 stojny" },
  { "stojny": 2, "strecha": "duo", "sirka_do": 7500, "hloubka_do": 6000, "popisek": "DUO - 2 stojny" },
  { "stojny": 3, "strecha": "duo", "sirka_do": 8000, "hloubka_do": 6000, "popisek": "DUO - 3 stojny" }
]
```

MAXI Carbo je `multi-matrix` se 2 variantami (dutinkový / plný polykarbonát), zóny platí pro obě. MAXI Fusion je `multi-matrix` se 4 variantami (BIO / Glass, BIO / Carbo, Thermo / Glass, Thermo / Carbo) a ceny má zatím `null` (ještě nejsou stanoveny) — matice slouží jen k rozměrům a zónám.

**`standard_colors`** (pergoly) — **jediný zdroj** standardního (bezpříplatkového) provedení barev, česky i anglicky. Pole dílů; každý díl má seznam variant.

```json
"standard_colors": [
  { "part": "frame", "label": "Rám", "label_en": "Frame",
    "options": [ { "cs": "RAL 7016 Axalta jemná struktura", "en": "RAL 7016 Axalta structure" } ] },
  { "part": "louvres", "label": "Lamely", "label_en": "Louvres",
    "options": [ { "cs": "RAL 9006 Axalta struktura", "en": "RAL 9006 Axalta structure" }, { "cs": "RAL 7016", "en": "RAL 7016" } ] }
]
```

- `part` = strojový klíč dílu (`frame`, `louvres`, `panel`), `label` / `label_en` = text do ceníku.
- `options` = standardní varianty (kterákoli z nich je bez příplatku); `cs` / `en` = text varianty.
- volitelně `note` / `note_en` = doplněk k dílu (např. Thermo panel: „ostatní konzultovat individuálně“).
- Zobrazení např. „Rám: RAL 7016 · Lamely: RAL 9006 Axalta struktura / RAL 7016“.
- `color_summary` v `pricelist.json` je jen volný text (barvy výplní, příplatky…) — standardní barvy brát odtud.

**`double_unit`** (markýzy, nyní Portofino ZIP) — od které šířky je markýza dvojitá (dvě markýzy vedle sebe). Slouží ke zvýraznění řádků v matici a k zobrazení počtu úchytů.

```json
"double_unit": {
  "label": "Dvojitá markýza",
  "axis": "vertical",
  "from": 700,
  "unit": "cm",
  "description": "Dvě markýzy vedle sebe na dvojitém držáku na krokvi. V ceně 2 kazety, 2 motory, 4 vodící lišty.",
  "mounting_points": { "label": "počet držáků (pod střechu) / patek (nad střechu)",
                        "single": [4, 6, 6, 6, 8, 8, 8, 8], "double": [8, 12, 12, 12, 16, 16, 16, 16] }
}
```

- `axis` = osa matice, na které je šířka (u markýz `"vertical"` — svislá osa). Hodnota na té ose `>= from` (včetně) = dvojitá markýza; řádky zvýraznit a v legendě použít `label`.
- `mounting_points.single` / `.double` jsou paralelní s druhou osou (u markýz `horizontal_values` = výsuv): pod matici vypsat řádek „počet držáků“ — pro jednoduchou a dvojitou zvlášť.
- Ceny dvojité markýzy (i dvojnásobný příplatek za RAL) jsou už v matici / `options` — nic nepřepočítávat.

### `knowledge.md` (vždy)

Markdown s frontmatterem `sku:` a sekcemi `## Popis`, `## Specifikace`, případně `### Description (EN)`. Použij na detail page nebo info modal.

## 4. Authentication

Repo je private. Tvoje fetch musí mít hlavičku:

```
Authorization: Bearer <github_pat>
```

Token vygeneruj na github.com/settings/tokens (scope: `repo`). V Node:

```js
const headers = { 'Authorization': `Bearer ${process.env.GITHUB_TOKEN}` };
const items = await fetch(URL, { headers }).then(r => r.json());
```

## 5. Příklad — kompletní lookup

```js
const BASE = 'https://raw.githubusercontent.com/davidopatsky/pricelist-01/main';
const headers = { 'Authorization': `Bearer ${process.env.GITHUB_TOKEN}` };

const items = await fetch(`${BASE}/pricelist.json`, { headers }).then(r => r.json());

async function priceFor(sku, width_mm, depth_mm) {
  const item = items.find(i => i.sku === sku);
  if (!item) return null;

  // 1. Fixní cena
  if (item.standard_price !== 1 && item.price_formula == null) {
    return item.standard_price;
  }
  // 2. Matice
  if (item.price_formula === 'matrix') {
    const m = await fetch(
      `${BASE}/products/${item.category}/${item.sku}/prices.json`,
      { headers }
    ).then(r => r.json());
    const wIdx = m.horizontal_values.indexOf(width_mm);
    const dIdx = m.vertical_values.indexOf(depth_mm);
    if (wIdx < 0 || dIdx < 0) return null;
    return m.prices[dIdx][wIdx] || null;  // null = N/A in this dimension
  }
  // 3. Formula
  if (item.price_formula) {
    return { formula: item.price_formula };  // app must interpret
  }
  // 4. Placeholder / no price
  return null;
}
```

## 5b. Montáž (B2C výpočet)

`products/sluzba/montaz/prices.json` — sazby montáže pro aplikaci obchodníků (B2C). B2B ceník montáž neuvádí.

- `sections[]` — produkt patří do sekce podle `applies_to_category` nebo `applies_to_skus`.
- `rate_type`: `tiered_by_price` (procento podle hladiny ceny produktu, `tiers[].price_up_to_czk`), `flat_percent` (`percent` z ceny produktu), `flat_fee` (pevná částka `fee_czk`).
- `adjustments[]` (u sekce, volitelné) — příplatek k procentu pro vybrané SKU: `add_percent` se **přičte** k procentu z hladiny. Příklad: ALUX Glass s cenou v hladině 13 % → montáž 13 % + 2 % = 15 % z ceny pergoly.

## 5c. Termín dodání

`delivery_weeks` v `pricelist.json` je **interní termín pro český B2C obchod** (aplikace obchodníků). B2B ceník ho nepřebírá — obecný termín pro partnery je v B2B ceníku/podmínkách vyplněný ručně. Do technických údajů (knowledge.md) se termín nikdy nepíše.

## 6. Záložka „Kusové položky“ (interaktivní ceník)

Samostatná záložka **na konci navigace** se všemi položkami s pevnou cenou za jednotku (stojny, kotvení, elektro, profily, služby, příplatky…).

**Které položky:** z `pricelist.json` všechny, kde `price_formula !== "matrix"` a `standard_price !== 1` (1 = zástupná hodnota, cena se počítá z matice nebo vzorce — např. `montaz`, `extra-ral-ram`).

```js
const kusove = items.filter(i => i.price_formula !== 'matrix' && i.standard_price !== 1);
```

**Sloupce:** SKU (`sku`), Název (`name`), Prodejní cena (`standard_price`), Náklad (`cost`).

Cena je za `unit` (ks, m2, bm, km) — u jednotek jiných než `ks` doporučeno zobrazit jednotku u ceny (např. „30 Kč/km“), jinak je cena zavádějící.

## 7. Caching

GitHub raw URL CDN cache TTL ~5 min. **Necachuj per-request** — fetchni `pricelist.json` jednou při startu, cachuj v paměti, refresh každých pár minut nebo po webhooku.

## 8. Pinning na verzi (volitelné)

Místo `main` můžeš pinnout commit hash:

```
https://raw.githubusercontent.com/davidopatsky/pricelist-01/<commit-sha>/pricelist.json
```

## 9. Když se něco rozbije

- Plný schema spec: `BLUEPRINT.md` v rootu repa
- Workflow + history: `BLUEPRINT.md` → sekce "Projektový kontext"
- Tento soubor (`CONSUMERS.md`) — pravidelně aktualizuju když se schema změní
