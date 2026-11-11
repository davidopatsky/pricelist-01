# Strada – historie cen a cenová logika

Ceny v Kč bez DPH, rozměr = šířka × hloubka. Zálohy matic jsou v `products/pergola/<sku>/history/`.

## Platná logika (od 10. 11. 2026)

### Strada Carbo 16 mm (`strada-carbo-dutinkovy`)

```
obchodní náklad (nákup) = výrobní náklad × 1,20 × 1,15  (+ výztuha 3 500 Kč v zónách s "pricky": true)
prodejní cena            = obchodní náklad / 0,58
(× 1,20 = výrobní náklad +20 % od 11. 11. 2026)
```

- Výrobní náklad = buňka **S22** v kalkulaci `strada-carbo-dutinkovy/history/naklady-kalkulace-vse-2026-11-10.xlsx`, list **Strada Carbo** (mění se jen B2 šířka a D2 hloubka).
- Počet krokví B11 = **(šířka − 240) / 600** (v listu Strada Carbo je B11 zapsané jako pevné číslo 6,2667 – pro přepočet vždy použít vzorec).
- Stojny mají v kalkulaci cenu 0 Kč (záměr). Na hranicích zón (šířka 5 100, hloubka 4 100) proto cena klesá – zóna „2 stojny + výztuha“ přechází na „3 stojny“ bez výztuhy.
- `cost_percent` v pricelistu = 58 % (= obchodní nákup).
- Proti 9. 11. 2026 (vč. +20 %): +26 až +57 %, medián +41 %.

| Rozměr | Výrobní náklad (kalkulace) | Cena 10. 11. | Cena od 11. 11. (výrobní +20 %) |
|---|---:|---:|---:|
| 2 × 2 m | 17 259 | 34 221 | 41 066 |
| 3 × 3 m | 23 917 | 47 421 | 56 905 |
| 5 × 4 m | 38 595 | 82 558 | 97 863 |
| 6 × 4 m | 44 334 | 87 903 | 105 484 |
| 7 × 4 m | 50 073 | 105 318 | 125 174 |
| 8 × 3 m | 46 910 | 99 046 | 117 649 |
| 8 × 4 m | 55 813 | 116 697 | 138 830 |

### Strada Carbo 6 mm (`strada-carbo-plny`) a Strada Glass (`strada-glass`)

- Ceny ponechány ve stavu z aktualizace Q3 (12. 8. 2026) + oprav plochých úseků (2. 11. 2026). Glass max. hloubka 4 000 mm.
- Kalkulace (listy **Strada Plexi** a **Strada Glass**) dává oběma stejný výrobní náklad – krytina počítaná jako VSG 4.4.2 za 800 Kč/m² (záměr).
- Podle kalkulace by s pravidlem „× 1,15 / 0,58“ vyšly o 8–40 % levněji (medián −15 až −18 %) → **rozhodnuto nechat původní ceny**. Obchodní nákup je u nich typicky ~48 % ceny (38–53 %).

## Historie

| Datum | Změna |
|---|---|
| 12. 4. 2026 | Nové matice ze CSV od uživatele, interpolace na krok 100 mm. |
| 12. 8. 2026 | **Q3:** cena = výrobní náklad × 1,775 (1,25 × 1,42); kde byla stará cena vyšší, u Carbo 16 + polovina rozdílu, u Glass jiná pravidla prémie. Carbo 6 mm = kopie Glass. Náklady ze screenshotů: `history/naklady-screenshoty-2026-08-12/`, `history/naklady-2026-08-12-Q3.json`. |
| 12. 8. 2026 | ⚠️ Screenshoty Carbo 16 mm měly prázdný počet krokví (krokve, přítlačky, těsnění = 0 Kč) a krytinu VSG se zápornou plochou → náklady Carbo 16 podhodnocené, ceník příliš levný. Zjištěno 10. 11. 2026. |
| 7. 10. 2026 | Zóny stojen + výztuha: náklad výztuhy +3 500 Kč v zónách s `pricky`. |
| 2. 11. 2026 | Carbo 6 mm a Glass: ploché úseky (stejná cena u více rozměrů) dorovnány. |
| 4. 11. 2026 | Glass: max. hloubka 4 000 mm. |
| 10. 11. 2026 | Dočasně všechny Strady plošně +30 % a +10 % (× 1,43) – nahrazeno. |
| 10. 11. 2026 | **Carbo 16 mm z opravené kalkulace** (× 1,15 / 0,58). Carbo 6 mm a Glass vráceny na stav z 9. 11. 2026. |
| 11. 11. 2026 | **Carbo 16 mm: výrobní náklad z kalkulace +20 %**, z toho obchodní náklad (× 1,15) a cena (58 %). |

## Zálohy

- `history/prices-2026-08-12-pre-Q3-update.json` – před Q3
- `history/prices-2026-11-10-pre-30pct.json` – stav 9. 11. 2026 (před dnešními změnami)
- `strada-carbo-dutinkovy/history/prices-2026-11-10-pre-kalkulace.json` – Carbo 16 × 1,43 (nepoužito)
- `strada-carbo-dutinkovy/history/prices-2026-11-11-pre-20pct.json` – Carbo 16 z kalkulace před +20 %
