#!/usr/bin/env python3
"""Kontrola textů pergol: CZ × EN fakta, duplicity, čeština v angličtině.

    python3 scripts/check_texts.py      # exit 1, když něco najde

Kontroluje u každé pergoly (category == "pergola"):
  1. v anglických textech nejsou česká písmena,
  2. česky i anglicky stejná fakta: typ skla (VSG …), RAL kódy, barvy výplně, typ konstrukce,
  3. žádný text ručně na dvou místech (description = knowledge Popis, color_summary = Barvy …).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CZ_CHARS = re.compile(r"[ěščřžýáíéúůťďňĚŠČŘŽÝÁÍÉÚŮŤĎŇ]")
FILL_COLORS = [("čir", "clear"), ("antracit", "anthracite"), ("mléčn", "opal")]
CONSTRUCTION = [("rovný rám", "flat frame"), ("šikm", "sloped")]


def sections(md):
    """knowledge*.md → {nadpis sekce: text}."""
    body = re.sub(r"^---\n.*?\n---\n", "", md, flags=re.S)
    out, cur = {}, None
    for line in body.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            out[cur] = ""
        elif cur and line.strip():
            out[cur] = (out[cur] + " " + line.strip()).strip()
    return out


def walk_en(obj, path=""):
    """Všechny anglické řetězce v metadata.json (klíče *_en, en)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and (k.endswith("_en") or k == "en"):
                yield f"{path}.{k}", v
            else:
                yield from walk_en(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_en(v, f"{path}[{i}]")


def facts(text):
    t = text.lower()
    return {
        "VSG": sorted(set(re.findall(r"vsg\s*(\d+(?:\.\d+)?)", t))),
        "RAL": sorted(set(re.findall(r"\b(\d{4})\b", t)) & {"7016", "9006", "9010", "9016", "8014", "8017"}),
    }


def main():
    items = {i["sku"]: i for i in json.loads((ROOT / "pricelist.json").read_text(encoding="utf-8"))}
    problems = []
    for sku, it in items.items():
        if it["category"] != "pergola":
            continue
        d = ROOT / "products" / "pergola" / sku
        meta = json.loads((d / "metadata.json").read_text(encoding="utf-8"))
        kcs = (d / "knowledge.md").read_text(encoding="utf-8")
        ken_path = d / "knowledge.en.md"
        ken = ken_path.read_text(encoding="utf-8") if ken_path.exists() else ""
        P = lambda msg: problems.append(f"{sku}: {msg}")

        # 1) čeština v angličtině
        if not ken_path.exists():
            P("chybí knowledge.en.md")
        for f in ("name_en", "description_en", "color_summary_en"):
            if not it.get(f):
                P(f"chybí {f}")
        for where, txt in [("knowledge.en.md", ken)] + [(f, it.get(f) or "") for f in ("name_en", "description_en", "color_summary_en")] + list(walk_en(meta)):
            if CZ_CHARS.search(txt):
                P(f"české znaky v angličtině ({where}): {CZ_CHARS.findall(txt)[:5]}")

        # 2) stejná fakta CZ × EN
        cs_all = " ".join(filter(None, [it.get("name"), it.get("description"), it.get("color_summary"),
                                        meta.get("display_name_cs"), kcs]))
        en_all = " ".join(filter(None, [it.get("name_en"), it.get("description_en"), it.get("color_summary_en"),
                                        meta.get("display_name_en"), ken]))
        fc, fe = facts(cs_all), facts(en_all)
        for k in fc:
            if fc[k] != fe[k]:
                P(f"{k} česky {fc[k]} × anglicky {fe[k]}")
        vsg_by_src = {n: facts(s or "")["VSG"] for n, s in (("name", it.get("name")), ("description", it.get("description")),
                       ("color_summary", it.get("color_summary")), ("display_name_cs", meta.get("display_name_cs")),
                       ("knowledge.md", kcs)) if facts(s or "")["VSG"]}
        if len({tuple(v) for v in vsg_by_src.values()}) > 1:
            P(f"rozporné sklo česky: {vsg_by_src}")
        for cz, en in FILL_COLORS + CONSTRUCTION:
            if (cz in cs_all.lower()) != (en in en_all.lower()):
                P(f"„{cz}“ / „{en}“ jen v jednom jazyce (cs={cz in cs_all.lower()}, en={en in en_all.lower()})")

        # 3) duplicity — tentýž text ručně na dvou místech
        scs, sen = sections(kcs), sections(ken)
        dup = [("description", it.get("description"), "knowledge.md Popis", scs.get("Popis")),
               ("color_summary", it.get("color_summary"), "knowledge.md Barvy a povrchy", scs.get("Barvy a povrchy")),
               ("description_en", it.get("description_en"), "knowledge.en.md Description", sen.get("Description")),
               ("color_summary_en", it.get("color_summary_en"), "knowledge.en.md Colors and finishes", sen.get("Colors and finishes"))]
        for a, va, b, vb in dup:
            if va and vb and " ".join(va.split()) == " ".join(vb.split()):
                P(f"duplicita: {a} = {b}")
        for a, va in (("description", it.get("description")), ("description_en", it.get("description_en"))):
            for para in re.split(r"\n\s*\n", va or "")[1:]:
                if para.strip():
                    P(f"{a}: odstavec navíc mimo knowledge („{para.strip()[:50]}…“)")

    for p in problems:
        print(p)
    print(f"\n{len(problems)} problémů" if problems else "✓ bez problémů")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
