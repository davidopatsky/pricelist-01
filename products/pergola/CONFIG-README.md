# config.json – konfigurační data pergol

Soubor `products/pergola/<sku>/config.json` (ALUX a Strada). Slouží jako konfigurační data bokem od cen – cenové matice a aplikace ho nepoužívají.

| Pole | Význam |
|---|---|
| `frame_color` | `standard` = standardní barva rámu (cs / en), `other_colors: "surcharge"` = ostatní barvy za příplatek |
| `roof_type` | typ střechy (cs / en) |
| `roof_color` | `options` = nabízené barvy střechy, `note` = poznámka (např. „ostatní barvy v ceně“). Prázdné `options` = barva není v datech určena |
| `louvre_color` | **jen ALUX Bioclimatic** (místo `roof_color`): `standard` = standardní barvy lamel (RAL 9006, RAL 7016), `other_colors: "surcharge"` = ostatní za příplatek |
| `motor_type` | **jen ALUX Bioclimatic**: `options` = Somfy IO, Somfy WT; `standard` = motor v ceně (Somfy IO) |
| `led_rafters` | LED lamely / krokve: `true` = ano, `false` = ne, `null` = zatím nevyplněno |
| `led_perimeter` | LED obvod: `true` / `false` / `null` |

Barvy a typ střechy jsou převzaté z popisů v ceníku. **LED zatím nikde v datech u ALUX ani Strady není, proto je `null`** – doplnit podle skutečnosti. MAXI a Simple config zatím nemají.

**ALUX Thermo:** `roof_color.options` mají `bottom` (spodní strana panelu) a `top` (horní); `custom_allowed: true` = atypické barvy lze zadat ručně.
