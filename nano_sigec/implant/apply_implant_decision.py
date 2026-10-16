#!/usr/bin/env python3
"""Apply the registered decision rules of implant_design.json (ledger 151) to
implant_results.json. Run once, after analyze_implant.py. Payload keys are text only."""
import hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger  # noqa: E402
D = json.load(open(os.path.join(HERE, "implant_design.json")))
R = json.load(open(os.path.join(HERE, "implant_results.json")))
sha = hashlib.sha256(open(os.path.join(HERE, "implant_results.json"), "rb").read()).hexdigest()
led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
if any(e["payload"].get("op_id") == "analysis-" + D["campaign"] for e in led.entries):
    sys.exit("already applied")
P, Dec = R["pred"], R["decision"]
assert Dec["gates_pass"]
a = led.append("analysis", {
    "op_id": "analysis-" + D["campaign"], "campaign": D["campaign"], "prereg_seq": 151, "raw_seq": 152,
    "results_file": "nano_sigec/implant/implant_results.json", "results_sha256": sha,
    "gates": {k: bool(v["pass"]) for k, v in R["gates"].items()},
    "predictions": {k: bool(v["pass"]) for k, v in P.items()},
    "statement": "registered analysis run once on the committed SRIM and RustBCA outputs and almaBTE host modes"})
k = R["A_kappa_1vol_x0.2"]
s1 = led.append("shard_operation", {
    "op_id": "decision-cavity-" + D["campaign"], "campaign": D["campaign"], "op": "scope_limit",
    "target": "cavity claim (ledger 76): 1 vol% of 5 nm cavities saves about 40% Ge at x = 0.2",
    "cause": ("registered rule: at the post-anneal radius R = 20 nm (anchor: 40 keV, 5e16 He cm-2, 900 C) the Ge "
              f"saving at 300 K is {Dec['cavity_worst_saving_R20_300K']:.1f}%, inside the 10-25% band; the cavities "
              f"still lower kappa_L by {P['PI3']['min_reduction_pct_R20']:.1f}-{P['PI3']['max_reduction_pct_R20']:.1f}%"),
    "effect": {"claim_now": ("cavities save about 40% Ge only if they stay at R <= 10 nm, i.e. anneal and service "
                             "below the void-coarsening range; after a >= 700 C anneal (R 5-20 nm) the saving is "
                             "about 18% and the cavities remain a lever (>= 5%)"),
               "implant_recipe": "He 40 keV, about 5e16 cm-2 into Si0.8Ge0.2 gives a cavity layer at about 220-410 nm",
               "scope_note": "implanted layers are 0.1-1 um deep: a surface layer or film, not a sintered leg"},
    "evidence": {"analysis_seq": str(a["seq"]), "results_sha256": sha},
    "decision": D["decision_rule"]["cavity_claim"]})
b = R["B_c_box"]["recipes"]["1at%"]
s2 = led.append("claim", {
    "op_id": "claim-sic-route-" + D["campaign"], "campaign": D["campaign"], "claim": "C_impl_route",
    "statement": ("five C implants (10-160 keV, total about 2.6e16 cm-2) give 1 at% C over 30-300 nm of Si0.8Ge0.2 "
                  f"within {b['rms_dev_pct']:.1f}% rms; peak damage {b['peak_dpa_KP']:.1f} displacements per atom, so "
                  "the layer amorphises and regrows by solid-phase epitaxy; 1 at% exceeds the 2-4e20 cm-3 "
                  "substitutional cap, so the excess carbon is expected to leave the lattice as SiC on anneal, the "
                  "form the campaign recommends; particle size after anneal is not computed"),
    "evidence": {"analysis_seq": str(a["seq"])}})
C = R["C_chain"]
s3 = led.append("claim", {
    "op_id": "decision-chain-" + D["campaign"], "campaign": D["campaign"], "claim": "C_impl_chain",
    "target": "damage-to-kappa chain (SRIM vacancies plus point-defect scattering) for as-implanted layers",
    "cause": (f"registered rule: f_req = {C['f_req_for_10WmK']:.3f} <= 0.06, so the chain is usable with the retained "
              "fraction as the named weak input; prediction PI7 (f_req > 0.06) is refuted. The anchor is an upper "
              "bound (<= 10 W/mK), so it fixes f >= 0.05 for point defects alone and cannot separate point defects "
              "from the amorphous pockets the authors favour"),
    "effect": {"usable_for": "as-implanted kappa estimates quoted with f in [0.05, 0.1] and the anchor stated",
               "not_usable_for": "any claim that point defects, not amorphous pockets, set the measured value",
               "weak_input": "retained vacancy fraction f"},
    "evidence": {"analysis_seq": str(a["seq"])},
    "decision": D["decision_rule"]["chain"]})
assert led.verify_chain()
print("seq", a["seq"], s1["seq"], s2["seq"], s3["seq"])
