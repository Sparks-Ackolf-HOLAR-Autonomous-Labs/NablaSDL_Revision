"""Second-extractor labels for the 67 literature rows of extracted_points.json.

Labels were written by a Claude model reading only the snippet text and paper
title (plus x_ge, T_K, kappa_W_mK to locate each datapoint). The first
extractor's `system` and `method` fields were not read during labeling.
This script only serialises the hand labels, attaches the snippet hash, and
verifies that every evidence quote is a verbatim substring of its snippet.

value_note: verbatim = number appears in the snippet as the reported value;
            derived  = number does not appear but is arithmetic on snippet
                       numbers (e.g. 2.2 - 0.6); absent = not in snippet and not
                       a recoverable derivation.
material:   chemistry of the quoted value per the snippet (the dataset is
            nominally Si1-xGex; non-SiGe chemistries are flagged).
"""
import glob
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MT = HERE.parents[2]
KG = MT / "pilot" / "kg"

N = None
# row: (sample_class, method, confidence, evidence_quote, value_in_snippet,
#       value_note, material, thickness_nm, diameter_nm, grain_size_nm,
#       prep_route, note)
L = {
 0: ("bulk", "model-fit", "medium", "following ref 39, we set in eq 1 κ Si = 148 W/m•K", True, "verbatim", "Si", N, N, N, N, "bulk Si endpoint parameter of a phenomenological kappa(x) fit"),
 1: ("bulk", "model-fit", "medium", "κ Ge = 60 W/m•K, and A SiGe = 2.8 W/m• K", True, "verbatim", "Ge", N, N, N, N, "bulk Ge endpoint parameter of the fit"),
 2: ("bulk", "model-fit", "medium", "For the GeSn case, after fixing κ Sn = 63 W/m•K", True, "verbatim", "Sn", N, N, N, N, "value is for Sn, not a SiGe composition; x_ge=0 is a misattribution"),
 3: ("bulk", "model-fit", "medium", "eq 1 indicates that already at 10% of Sn content, κ GeSn drops at 5 W/m•K", True, "verbatim", "GeSn", N, N, N, N, "GeSn model prediction, not SiGe"),
 4: ("bulk", "BTE/DFT", "medium", "minimum thermal conductivity of Si 1−x Sn x alloys was 3 W m −1 K −1 with x = 0.5", True, "verbatim", "SiSn", N, N, N, N, "SiSn; x=0.5 is Sn fraction, recorded as x_ge"),
 5: ("bulk", "BTE/DFT", "medium", "5.86 W m −1 K −1 for the Ge 1−y Sn y with y = 0.61", True, "verbatim", "GeSn", N, N, N, N, "GeSn; x_ge=0.39 is the Ge fraction of GeSn"),
 6: ("nanowire", "experiment", "high", "Individual P-type SiGe alloy NW was reported with thermal conductivity ∼1.1 W m −1 K −1 and ZT ∼0.18 at 300 K experimentally", True, "verbatim", "SiGe", N, N, N, N, "Ge fraction not stated for this value"),
 7: ("amorphous", "MD", "high", "starting from a reference κ = 2.2 W m −1 K −1 for a-Si", True, "verbatim", "Si", N, N, N, N, "atomistic 4096-atom model with QHGK; labeled MD as empirical-potential atomistic simulation"),
 8: ("amorphous", "MD", "high", "the substitution of 5% Ge results in a 0.6 W m −1 K −1 drop of κ", False, "derived", "SiGe", N, N, N, N, "1.6 = 2.2 - 0.6"),
 9: ("amorphous", "MD", "high", "A further 0.55 W m −1 K −1 reduction of κ is obtained raising the Ge concentration to 15%", False, "derived", "SiGe", N, N, N, N, "1.05 = 2.2 - 0.6 - 0.55"),
 10: ("film", "experiment", "medium", "Thermal conductivity of the unsuspended Ge 1−x Sn x /Ge/Si microwire at 5% Sn content, 20.1 W m −1 K −1", True, "verbatim", "GeSn", N, N, N, "epilayer heterostructure patterned into microwire", "GeSn epilayer microwire; could also be read as wire geometry"),
 11: ("film", "experiment", "medium", "18 W m −1 K −1 obtained experimentally by Spirito et al from Ge 1−x Sn x /Ge/Si heterostructures", True, "verbatim", "GeSn", N, N, N, "epitaxial heterostructure", "GeSn"),
 12: ("film", "experiment", "medium", "9.1 W m −1 K −1 (as can be seen in Figure 4) for the suspended Ge 1−x Sn x /Ge microwire", True, "verbatim", "GeSn", N, N, N, "suspended epilayer microwire", "GeSn"),
 13: ("bulk", "BTE/DFT", "low", "the 9.7 W m −1 K −1 calculated theoretically elsewhere for Ge 0.95 Sn. 0.05", True, "verbatim", "GeSn", N, N, N, N, "theory type not named in this snippet; GeSn, x_ge=0.95 is Ge fraction of GeSn"),
 14: ("bulk", "experiment", "low", "The thermal conductivities of 2 and 1.31 W m −1 K −1 were reported elsewhere for a polycrystalline Ge 0.93 Sn 0.07", True, "verbatim", "GeSn", N, N, N, "polycrystalline", "GeSn polycrystal; grain size not stated"),
 15: ("other", "unclear", "low", "most efficient TE material (Bi 0.7 Sb 0.3 Te)", True, "verbatim", "BiSbTe", N, N, N, N, "not a group-IV material at all"),
 16: ("film", "experiment", "medium", "that are lower than our 2.5 W m −1 K −1 obtained at 9% Sn content", True, "verbatim", "GeSn", N, N, N, "suspended epilayer", "GeSn"),
 17: ("nanostructured", "experiment", "high", "the low lattice thermal conductivity 'кl' was nearly constant for about 1 Wm -1 K -1 for x = 0.02 and x = 0.03", True, "verbatim", "SiGe", N, N, N, N, "x is Ni/B co-dopant level, not Ge fraction; nano-to-micro grain boundaries"),
 18: ("nanostructured", "experiment", "high", "the low lattice thermal conductivity 'кl' was nearly constant for about 1 Wm -1 K -1 for x = 0.02 and x = 0.03", True, "verbatim", "SiGe", N, N, N, N, "x is dopant level, not Ge fraction"),
 19: ("nanostructured", "experiment", "high", "for x = 0.02 and x = 0.04, the estimated 'кl' was increased up to 1.2 Wm -1 K -1 at high temperature", True, "verbatim", "SiGe", N, N, N, N, "x is dopant level, not Ge fraction"),
 20: ("nanostructured", "experiment", "high", "for x = 0.02 and x = 0.04, the estimated 'кl' was increased up to 1.2 Wm -1 K -1 at high temperature", True, "verbatim", "SiGe", N, N, N, N, "x is dopant level, not Ge fraction"),
 21: ("amorphous", "experiment", "high", "experimental thermal conductivity typically ranges from 1 to 6 W/m-K at room temperature", True, "verbatim", "Si", N, N, N, N, "a-Si experimental range endpoint"),
 22: ("amorphous", "experiment", "high", "experimental thermal conductivity typically ranges from 1 to 6 W/m-K at room temperature", True, "verbatim", "Si", N, N, N, N, "a-Si experimental range endpoint"),
 23: ("amorphous", "MD", "high", "Pure amorphous Si and Ge have thermal conductivities of 1.55 ± 0.20 W/m-K and 0.99 ± 0.21 W/m-K", True, "verbatim", "Si", N, N, N, N, "GK MD with SW potential"),
 24: ("amorphous", "MD", "high", "Pure amorphous Si and Ge have thermal conductivities of 1.55 ± 0.20 W/m-K and 0.99 ± 0.21 W/m-K", True, "verbatim", "Ge", N, N, N, N, "a-Ge"),
 25: ("amorphous", "MD", "high", "the minimum thermal conductivity of 0.50 ± 0.17 W/m-K achieved with 55% of Ge content", True, "verbatim", "SiGe", N, N, N, "amorphous heterogeneous nanocomposite (simulated)", "na-SiGe"),
 26: ("bulk", "experiment", "high", "κ ph ⊥ = 36 W m −1 K −1 [13] was used for bulk Si at 900 K", True, "verbatim", "Si", N, N, N, N, None),
 27: ("superlattice", "experiment", "medium", "κ ph ⊥ = 1.9 W m −1 K −1 was used for the Si/Ge-SL [55]", True, "verbatim", "Si/Ge SL", N, N, N, N, "lattice part stated as taken from experiment"),
 28: ("nanostructured", "unclear", "low", "the expected nano-alloy limit of 2.5 W m −1 K −1 [69]", True, "verbatim", "SiGe", N, N, N, N, "a cited limiting value, origin not stated"),
 29: ("film", "experiment", "medium", ".1±2.8 and 18.2±2.6 W m −1 K −1 attributed to the unsuspended micro-fabricated Ge 1−x Sn x /Ge/Si heterostructures microwires", False, "absent", "GeSn", N, N, N, "micro-fabricated epilayer heterostructure", "20.8 not in snippet (snippet has truncated '.1±2.8' and 18.2)"),
 30: ("film", "experiment", "medium", ".1±2.8 and 18.2±2.6 W m −1 K −1 attributed to the unsuspended micro-fabricated Ge 1−x Sn x /Ge/Si heterostructures microwires", False, "absent", "GeSn", N, N, N, "micro-fabricated epilayer heterostructure", "15.6 not in snippet"),
 31: ("film", "experiment", "high", "Values for Ge 1−x Sn x /Ge microwires with 5% and 9% Sn are measured to be 9.07 and 6.9 W m −1 K −1", True, "verbatim", "GeSn", N, N, N, "suspended epilayer microwire", "GeSn"),
 32: ("film", "experiment", "high", "Values for Ge 1−x Sn x /Ge microwires with 5% and 9% Sn are measured to be 9.07 and 6.9 W m −1 K −1", True, "verbatim", "GeSn", N, N, N, "suspended epilayer microwire", "GeSn"),
 33: ("bulk", "unclear", "medium", "Depending on the germanium content in silicon, values ranging from ~20 to ~9 W K −1 m −1 can be achieved", True, "verbatim", "SiGe", N, N, N, N, "upper end of a bulk SiGe alloy range, not pure Si (x_ge=0 misattributed)"),
 34: ("bulk", "unclear", "medium", "an alloy with 20% germanium concentration in silicon (~9 W K −1 m −1 )", True, "verbatim", "SiGe", N, N, N, N, "~9 belongs to 20% Ge, not x_ge=1 (misattributed)"),
 35: ("bulk", "unclear", "medium", "an alloy with 20% germanium concentration in silicon (~9 W K −1 m −1 )", True, "verbatim", "SiGe", N, N, N, N, None),
 36: ("film", "experiment", "high", "nanostructured Si 0.8 Ge 0.2 films grown through Metal Induced Crystallization (MIC) 38 , have been able to achieve thermal conductivity values down to ~1.2", True, "verbatim", "SiGe", N, N, N, "metal-induced crystallization", "nanostructured film; film and nanostructured both defensible"),
 37: ("bulk", "model-fit", "medium", "corresponding to the roomtemperature thermal conductivity values of Si and Ge bulk systems", True, "verbatim", "Si", N, N, N, N, "fixed bulk input to SL model fit"),
 38: ("bulk", "model-fit", "medium", "corresponding to the roomtemperature thermal conductivity values of Si and Ge bulk systems", True, "verbatim", "Ge", N, N, N, N, "fixed bulk input to SL model fit"),
 39: ("bulk", "MD", "high", "the thermal conductivity of Si0.5Ge0.5 in the present work is 1.62 W/(m•K)", True, "verbatim", "SiGe", N, N, N, N, "Green-Kubo MD"),
 40: ("bulk", "MD", "high", "comparable to 1.06 ± 0.16 W/(m•K) using the NEMD method", False, "derived", "SiGe", N, N, N, N, "1.22 = 1.06 + 0.16; the central value 1.06 was not extracted"),
 41: ("bulk", "MD", "high", "comparable to 1.06 ± 0.16 W/(m•K) using the NEMD method", False, "derived", "SiGe", N, N, N, N, "0.9 = 1.06 - 0.16"),
 42: ("bulk", "MD", "high", "we benchmark the thermal conductivity of Si using the same set of simulation parameters and obtain the thermal conductivity of 56.1 W/(m•K)", True, "verbatim", "Si", N, N, N, N, None),
 43: ("bulk", "experiment", "high", "only about half of the experimental value of 125.5 W/(m•K)", True, "verbatim", "Si", N, N, N, N, None),
 44: ("nanostructured", "experiment", "high", "nanostructured SiGe alloy as compared to reference sample. At room temperature 300K thermal conductivity of hotpressed sample is 1.91 W/mK", True, "verbatim", "SiGe", N, N, N, "hot pressing", "n-type, nano-grained porous"),
 45: ("film", "experiment", "medium", "the solid line corresponds to an effective in-plane thermal conductivity of κ eff = 0.05 W/m K", True, "verbatim", "SiGe", N, 25, 150, "laser sintering (mesoporous thin film)", "Raman plus simulation inversion; nanostructured also defensible; diameter is of surviving nanocrystals"),
 46: ("film", "experiment", "medium", "In the present case, this yields κ normalized = 0.1 W/m K", True, "verbatim", "SiGe", N, 25, 150, "laser sintering (mesoporous thin film)", "porosity-normalized value"),
 47: ("film", "experiment", "medium", "we obtain a maximum thermal conductivity of κ max normalized = 0.3 W/m K", True, "verbatim", "SiGe", N, 25, 150, "laser sintering (mesoporous thin film)", "uncertainty upper bound"),
 48: ("nanowire", "experiment", "high", "a value for the thermal conductivity of 1.1 Wm -1 K -1 for tapered NWs with a mean diameter of about 200 nm", True, "verbatim", "SiGe", N, 200, N, N, None),
 49: ("nanowire", "experiment", "high", "Another work showed a thermal conductivity of 1.2 Wm -1 K -1 for a NW with a diameter of 65 nm", True, "verbatim", "SiGe", N, 65, N, N, None),
 50: ("other", "experiment", "high", "the phenomenological thermal conductivities κSi-XII and κSi-III were calculated to be 33.2 and 37.4 W•m −1 •K −1", True, "verbatim", "Si", N, N, N, "dynamic decompression (metastable Si-XII phase)", "metastable Si polymorph, Raman thermometry"),
 51: ("other", "experiment", "high", "the phenomenological thermal conductivities κSi-XII and κSi-III were calculated to be 33.2 and 37.4 W•m −1 •K −1", True, "verbatim", "Si", N, N, N, "dynamic decompression (metastable Si-III phase)", "metastable Si polymorph"),
 52: ("bulk", "experiment", "high", "None of the previous ones gives a reasonable match to the reference experimental value of 51 W/mK", True, "verbatim", "Si", N, N, N, N, "diamond Si at 700 K"),
 53: ("bulk", "MD", "medium", "predict comparable values and overshoot the experimental value by about 80%", False, "derived", "Si", N, N, N, N, "91.8 = 51 x 1.8"),
 54: ("bulk", "MD", "medium", "underestimate the experimental value by a factor of 2 and 5, respectively", False, "derived", "Si", N, N, N, N, "25.5 = 51 / 2"),
 55: ("bulk", "MD", "medium", "underestimate the experimental value by a factor of 2 and 5, respectively", False, "derived", "Si", N, N, N, N, "10.2 = 51 / 5"),
 56: ("bulk", "experiment", "high", "experimental results for natural 56 and highly isotopically enriched 57 Si (k=130-160 W/(m•K) for 300 K)", True, "verbatim", "Si", N, N, N, N, None),
 57: ("bulk", "experiment", "high", "experimental results for natural 56 and highly isotopically enriched 57 Si (k=130-160 W/(m•K) for 300 K)", True, "verbatim", "Si", N, N, N, N, "isotopically enriched end of range"),
 58: ("bulk", "MD", "high", "calculated thermal conductivity of unstrained SW silicon is about 393 W/m•K", True, "verbatim", "Si", N, N, N, N, None),
 59: ("bulk", "MD", "high", "the value of k resulting from the EDIP calculations for unstrained silicon was found to be about 174 W/(m•K)", True, "verbatim", "Si", N, N, N, N, None),
 60: ("bulk", "MD", "high", "the calculated value of k for unstrained silicon with Tersoff III potential is about 229 W/(m•K)", True, "verbatim", "Si", N, N, N, N, None),
 61: ("nanowire", "MD", "high", "a steady decrease of the thermal conductivity down to about 1 W/mK with decreasing wire size from 5 to 1.6 nm at 300 K", True, "verbatim", "Si", N, 1.6, N, N, "Si NW, GK MD with SW"),
 62: ("nanowire", "MD", "high", "reported a thermal conductivity larger than 45 W/mK and the opposite trend for a size reduction from 2 to 1.1 nm", True, "verbatim", "Si", N, 1.1, N, N, "Si NW, GK MD with Tersoff; lower bound"),
 63: ("nanowire", "BTE/DFT", "medium", "a steady decrease of thermal conductivity with decreasing size down to 1 nm and 0.33 W/mK", True, "verbatim", "Si", N, 1, N, N, "computed from phonon dispersions (lattice-dynamics/BTE type)"),
 64: ("bulk", "MD", "high", "the calculated value of k for unstrained silicon with Tersoff III potential is about 229 W/(m•K)", True, "verbatim", "Si", N, N, N, N, None),
 65: ("bulk", "MD", "high", "For a 4% tensile hydrostatic strain, there is a 37% reduction (from 229 W/(m•K) to 144 W/(m•K))", True, "verbatim", "Si", N, N, N, N, "strained Si"),
 66: ("bulk", "MD", "high", "at a 4% compressive hydrostatic strain, the thermal conductivity increases 22% to 280 W/(m•K)", True, "verbatim", "Si", N, N, N, N, "strained Si"),
}


def snippets_by_hash():
    out = {}
    for f in sorted(glob.glob(str(KG / "asta" / "*.json"))):
        for e in json.loads(Path(f).read_text()).get("data", []):
            t = e.get("snippet", {}).get("text", "")
            if t:
                out.setdefault(hashlib.sha256(t.encode()).hexdigest()[:16], t)
    return out


def main():
    pts = json.loads((KG / "extracted_points.json").read_text())
    lit = [i for i, p in enumerate(pts) if str(p.get("corpusId", "")).isdigit()]
    assert sorted(L) == lit, (sorted(L), lit)
    sn = snippets_by_hash()
    rows = []
    for i in lit:
        p = pts[i]
        (sc, meth, conf, quote, vin, vnote, mat, th, dia, gs, prep, note) = L[i]
        text = sn[p["snippet_hash"]]
        assert quote in text, (i, quote)
        assert len(quote.split()) <= 25, (i, len(quote.split()))
        rows.append({
            "row": i, "snippet_hash": p["snippet_hash"],
            "corpusId": p["corpusId"], "title": p["title"],
            "sample_class": sc, "method": meth, "confidence": conf,
            "evidence_quote": quote, "value_in_snippet": vin,
            "value_note": vnote, "material": mat,
            "thickness_nm": th, "diameter_nm": dia, "grain_size_nm": gs,
            "prep_route": prep, "note": note,
        })
    out = {"extractor": "Claude (Anthropic), claude-opus-5-5, blind second pass",
           "date": "2026-09-29", "n_rows": len(rows), "rows": rows}
    (HERE / "labels_second.json").write_text(json.dumps(out, indent=1,
                                                        ensure_ascii=False))
    long_q = [r["row"] for r in rows if len(r["evidence_quote"].split()) > 25]
    print(f"wrote {len(rows)} rows; quotes verified verbatim; "
          f"quotes over 25 words: {long_q}")


if __name__ == "__main__":
    main()
