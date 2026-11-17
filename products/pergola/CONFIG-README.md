# config.json – konfigurační data pergol

Soubor `products/pergola/<sku>/config.json` (ALUX a Strada). Slouží jako konfigurační data bokem od cen – cenové matice a aplikace ho nepoužívají.

| Pole | Význam |
|---|---|
| `frame_color` | barva rámu (cs / en) |
| `roof_type` | typ střechy (cs / en) |
| `roof_color` | `options` = nabízené barvy střechy, `note` = poznámka (např. „ostatní barvy v ceně“). Prázdné `options` = barva není v datech určena |
| `led_rafters` | LED lamely / krokve: `true` = ano, `false` = ne, `null` = zatím nevyplněno |
| `led_perimeter` | LED obvod: `true` / `false` / `null` |

Barvy a typ střechy jsou převzaté z popisů v ceníku. **LED zatím nikde v datech u ALUX ani Strady není, proto je `null`** – doplnit podle skutečnosti. MAXI a Simple config zatím nemají.
