# Archive

Tato složka obsahuje **legacy soubory** ze starších iterací pricelistu.
Nic z toho **není používáno** žádným současným skriptem ani aplikací.
Důvod existence: historický kontext + safety net (nic se nesmazalo).

## Co je tady

| soubor | původní umístění | éra | proč legacy |
|---|---|---|---|
| `meta-v2.json` | root: `meta.json` | v2 | obsahuje **staré 6 kategorií** (`pergola/screen/glazing/awning/accessories/extras`) a staré field jména (`commerce.cost_percent`); v6.1 používá 4 kategorie a 15-pole flat schema v `pricelist.json` |
| `pricelist-v3-with-matrices.xlsx` | `export/pricelist.xlsx` | v3 | experimentální xlsx s **celými cenovými maticemi** jako oddělené sheety per produkt; nahrazeno současným `pricelist.xlsx` který má jen 15-pole tabulku |
| `salesqueze-export-v3/` | `export/salesqueze-export/` | v3 | starý Node skript pro SalesQueeze export, **čte neexistující `item.json`** (v3 schema) — neběží; per BLUEPRINT.md "out of scope, postaví se znova od nuly později" |

## Co s tím

- **Necht to být** — jako referenci, jako proof že nic se neztratilo
- **Smazat** — pokud jednou už nikdy nebudeš potřebovat historii, jen `rm -rf archive/`
- **Reprodukovat něco z toho** — viz git history (`git log --all --full-history -- archive/`)

## Aktuální workflow

Žádný skript v `scripts/` se nedotkne ničeho v `archive/`. Pricelist žije v:
- `pricelist.json` (canonical derived DB)
- `pricelist.xlsx` (canonical edit surface, gitignored)
- `products/<category>/<sku>/{knowledge.md, metadata.json, prices.json}`

Detail viz `../BLUEPRINT.md`.
