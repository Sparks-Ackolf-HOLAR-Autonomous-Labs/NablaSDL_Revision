"""Pilot C: LLM extraction of kappa datapoints from Asta snippets, and a
hypergraph knowledge graph over the evidence.

- Snippets come from Asta semantic-scholar snippet search (asta/q2*.json).
- Extraction runs on the DGX's resident vLLM server (Qwen3.6-35B-A3B,
  localhost:8000) with a strict JSON schema prompt; every datapoint keeps
  provenance (corpusId, title, snippet hash) so it can be shard-operated
  like any other evidence.
- The hypergraph follows 04_experimental_design_v2.md element 3: vertices
  are regimes (x-band, T-band), papers, methods, and system types; each
  extracted datapoint is a hyperedge over {paper, regime, method, system}
  carrying the kappa value. DGX Green-Kubo results join as a second
  evidence party when present.

Run:  python extract_kg.py <kg_dir>
"""

from __future__ import annotations

import glob
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

VLLM = "http://localhost:8000/v1/chat/completions"

PROMPT = """You extract thermal-conductivity datapoints from a physics text
snippet about Si-Ge (silicon-germanium) materials.

Return ONLY a JSON array (possibly empty). One object per numeric thermal
conductivity value stated in the snippet, with fields:
  x_ge: Ge fraction 0-1 (null if not stated; pure Si = 0, pure Ge = 1)
  T_K: temperature in kelvin (use 300 if described as room temperature,
       null if not stated)
  kappa_W_mK: the numeric value in W/(m K)
  system: one of bulk | film | nanowire | nanostructured | amorphous |
          superlattice | other
  method: one of experiment | MD | BTE/DFT | model-fit | unclear
Rules: only values actually present in the text; no unit conversion errors
(mW/m-K is 0.001 W/m-K); coefficients of fit formulas (like A_SiGe) are NOT
datapoints; ranges become two entries (min and max).

Snippet:
"""


def ask_llm(snippet: str) -> list[dict]:
    body = json.dumps({
        "model": "Qwen/Qwen3.6-35B-A3B-FP8",
        "messages": [{"role": "user", "content": PROMPT + snippet}],
        "temperature": 0.0, "max_tokens": 2500,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode()
    req = urllib.request.Request(VLLM, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        content = json.load(r)["choices"][0]["message"]["content"]
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.S)
    m = re.search(r"\[.*\]", content, flags=re.S)
    if not m:
        return []
    try:
        return [d for d in json.loads(m.group(0))
                if isinstance(d, dict) and d.get("kappa_W_mK") is not None]
    except json.JSONDecodeError:
        return []


def regime(x, T):
    xb = "x?" if x is None else f"x{min(int(float(x) * 5), 4)}"
    tb = "T?" if T is None else f"T{min(max(int((float(T) - 300) / 200), 0), 4)}"
    return f"{xb}{tb}"


def main():
    kg_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    if "--reuse" in sys.argv:
        # Rebuild the graph from the committed extraction (frozen literature
        # evidence) instead of re-querying the vLLM; simulation-party points
        # (DGX, CHPC) re-scanned from their result files.
        points = [p for p in
                  json.loads((kg_dir / "extracted_points.json").read_text())
                  if not str(p.get("corpusId", "")).startswith(
                      ("DGX-", "CHPC-", "DB-", "MACE-", "BTE-"))]
        build(kg_dir, points)
        return
    snippets = []
    for f in sorted(glob.glob(str(kg_dir / "asta" / "q2*snippets*.json"))) + \
              sorted(glob.glob(str(kg_dir / "asta" / "q2[12]*.json"))):
        data = json.loads(Path(f).read_text()).get("data", [])
        for d in data:
            s = d.get("snippet", {}).get("text", "")
            p = d.get("paper", {})
            if s and p.get("corpusId"):
                snippets.append({"text": s, "corpusId": p["corpusId"],
                                 "title": p.get("title", ""),
                                 "query_file": Path(f).name})
    # de-dup identical snippets
    seen, uniq = set(), []
    for s in snippets:
        h = hashlib.sha256(s["text"].encode()).hexdigest()[:16]
        if h not in seen:
            seen.add(h)
            s["snippet_hash"] = h
            uniq.append(s)

    points, failures = [], 0
    for s in uniq:
        try:
            for d in ask_llm(s["text"]):
                d.update({k: s[k] for k in
                          ("corpusId", "title", "snippet_hash", "query_file")})
                points.append(d)
        except Exception as e:                       # noqa: BLE001
            failures += 1
            print("LLM extraction failed:", s["snippet_hash"], repr(e)[:100])
    print(f"snippets={len(uniq)} extracted_points={len(points)} "
          f"failures={failures}")
    build(kg_dir, points)


def build(kg_dir: Path, points: list[dict]):
    # DGX kappa points (Muller-Plathe rNEMD) as a second evidence party
    gk_home = Path.home() / "mat_theory_pilot" / "gk"
    for f in glob.glob(str(gk_home / "kappa_*.json")):
        d = json.loads(Path(f).read_text())
        points.append({"x_ge": d["x"], "T_K": d["T"],
                       "kappa_W_mK": d["kappa_W_mK"], "system": "bulk",
                       "method": "MD", "corpusId": "DGX-MD",
                       "title": "This work: DGX Muller-Plathe rNEMD pilot",
                       "snippet_hash": Path(f).stem, "query_file": "local"})

    # CHPC kappa points (Phase B guest-partition campaign) as a third party
    chpc_dir = kg_dir.resolve().parents[1] / "chpc" / "results"
    for f in sorted(glob.glob(str(chpc_dir / "*.json"))):
        d = json.loads(Path(f).read_text())
        points.append({"x_ge": d["x"], "T_K": d["T"],
                       "kappa_W_mK": d["kappa_W_mK"], "system": "bulk",
                       "method": "MD", "corpusId": "CHPC-MD",
                       "title": "This work: CHPC Phase B Muller-Plathe rNEMD",
                       "snippet_hash": Path(f).stem, "query_file": "local"})

    # Phase C production campaign (P1 fault-study substrate, 132 runs) and
    # the Ge-corner shard action (19 runs), both CHPC-MD. Amorphous probes
    # enter as system "amorphous" so they never share a hyperedge with the
    # crystalline alloy (added 2026-09-29: the hypergraph was stale).
    decks = {}
    pts_file = kg_dir.resolve().parents[1] / "phase_c" / "production" / "points_production.txt"
    if pts_file.exists():
        for line in pts_file.read_text().split("\n"):
            if line.strip():
                f_ = line.split()
                decks[f_[0]] = f_[-1]
    for sub, title in (("production", "This work: Phase C production rNEMD (CHPC)"),
                       ("shard_action_corner", "This work: Ge-corner shard action rNEMD (CHPC)")):
        rdir = kg_dir.resolve().parents[1] / "phase_c" / sub / "results"
        for f in sorted(glob.glob(str(rdir / "*.json"))):
            d = json.loads(Path(f).read_text())
            if not isinstance(d, dict) or d.get("kappa_W_mK") is None:
                continue  # skip aggregate files (production_rows.json)
            system = "amorphous" if decks.get(Path(f).stem) == "amorph" else "bulk"
            points.append({"x_ge": d["x"], "T_K": d["T"],
                           "kappa_W_mK": d["kappa_W_mK"], "system": system,
                           "method": "MD", "corpusId": "CHPC-MD",
                           "title": title, "snippet_hash": Path(f).stem,
                           "query_file": "local"})

    # Party 4 (different method family): MACE-MD and BTE-DFT result files,
    # produced by the party4/ campaign scripts, one JSON per kappa point
    # with x, T, kappa_W_mK and a method tag.
    proj = kg_dir.resolve().parents[1]
    for sub, cid, meth, title in (
            ("party4_mace", "MACE-MD", "MD",
             "This work: MACE foundation-potential rNEMD (party 4b)"),
            ("party4_bte", "BTE-DFT", "BTE/DFT",
             "This work: DFT+BTE via almaBTE VCA (party 4a)")):
        for f in sorted(glob.glob(str(proj / sub / "results" / "*.json"))):
            d = json.loads(Path(f).read_text())
            recs = d if isinstance(d, list) else [d]
            for r in recs:
                if r.get("kappa_W_mK") is None:
                    continue
                points.append({"x_ge": r["x"], "T_K": r["T"],
                               "kappa_W_mK": r["kappa_W_mK"],
                               "system": "bulk", "method": meth,
                               "corpusId": cid, "title": title,
                               "snippet_hash":
                                   r.get("tag", Path(f).stem),
                               "query_file": "local"})

    # Party 5 (derived/aggregated databases): ingested by
    # party5_databases/ingest_citrine.py; dedup_suspect rows stay out so
    # aggregated evidence never double-counts the literature party.
    p5 = proj / "party5_databases" / "party5_points.json"
    if p5.exists():
        points.extend(p for p in json.loads(p5.read_text())
                      if not p.get("dedup_suspect"))

    # Party 5b (open experimental databases, 2026-09-29): Starrydata2 slice
    # from party5_databases/open_db/ingest_open_db.py. DB-UCSB rows are all
    # dedup_suspect (numerically identical to Citrine) and stay out; rows
    # failing the BTE-DFT physical-bound screen would stay out too (none do).
    # Each curve's upstream paper becomes its own paper vertex.
    p5b = proj / "party5_databases" / "open_db" / "open_db_points.json"
    if p5b.exists():
        for p in json.loads(p5b.read_text()):
            if p.get("dedup_suspect") or p.get("bound_flag"):
                continue
            up = p.get("upstream", {})
            p["paper_vertex"] = (f"S2:{up['s2_corpusId']}"
                                 if up.get("s2_corpusId")
                                 else f"DOI:{up.get('doi', p['corpusId'])}")
            points.append(p)

    # Hypergraph
    vertices, hyperedges = {}, []
    def vid(kind, name):
        key = f"{kind}:{name}"
        vertices.setdefault(key, {"kind": kind, "name": str(name)})
        return key
    for i, p in enumerate(points):
        members = [
            vid("paper", p.get("paper_vertex", p["corpusId"])),
            vid("regime", regime(p.get("x_ge"), p.get("T_K"))),
            vid("method", p.get("method", "unclear")),
            vid("system", p.get("system", "other")),
        ]
        hyperedges.append({"id": f"e{i}", "members": members,
                           "kappa_W_mK": p["kappa_W_mK"],
                           "x_ge": p.get("x_ge"), "T_K": p.get("T_K"),
                           "provenance": {"corpusId": p["corpusId"],
                                          "snippet": p["snippet_hash"]}})
    kg = {"vertices": vertices, "hyperedges": hyperedges,
          "n_vertices": len(vertices), "n_hyperedges": len(hyperedges)}
    (kg_dir / "kg_hypergraph.json").write_text(json.dumps(kg, indent=2))
    (kg_dir / "extracted_points.json").write_text(json.dumps(points, indent=2))

    # Bipartite expansion kept as the algorithmic representation only
    import networkx as nx
    G = nx.Graph()
    for key, v in vertices.items():
        G.add_node(key, **v)
    for e in hyperedges:
        G.add_node(e["id"], kind="datapoint", kappa=e["kappa_W_mK"])
        for mkey in e["members"]:
            G.add_edge(e["id"], mkey)
    nx.write_graphml(G, kg_dir / "kg_bipartite.graphml")

    # The figure draws true hyperedge regions, not the star expansion
    import render_hypergraph
    render_hypergraph.render(kg_dir)
    print("wrote kg_hypergraph.json / .graphml / .png")


if __name__ == "__main__":
    main()
