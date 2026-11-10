#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
puf_metrics.py  —  [2] PUF analysis metrics (pure computation, no figures)

Metrics
  entropy_axis(key, axis)      Shannon entropy per row/column (normalized by log2(3))  [paper Eq. 1-4]
  entropy_profile(key)         Ex array per row, Ey array per column (for Fig 4g)
  fractional_hd(a, b)          Fractional Hamming Distance (fraction of differing cells)
  inter_hd(keys)               pairwise inter-HD between tags (uniqueness, ideal 0.667)
  intra_hd(raws, ref, R)       simulated re-capture intra-HD (reliability, ideal 0)
  pearson_keys(a, b)           Pearson correlation between keys (ideal 0)
  bit_population(keys)         share of bits 0/1/2 (ideal 33.3%)
  degree_of_freedom(p, sd)     degrees of freedom / data capacity [paper Eq. 5]
  full_report(keys, raws)      all of the above as a dict

CLI:  py puf_metrics.py        # extract → compute all metrics → PUF_최종결과/metrics.json
"""
import os, json, itertools
import numpy as np
import cv2
import puf_extract as E

S = 3                       # ternary
RNG = np.random.default_rng(42)


# ===========================================================================
# Entropy (paper Eq. 1-4)
# ===========================================================================
def _line_entropy(line):
    p = np.array([(line == v).mean() for v in range(S)])
    p = p[p > 0]
    return float(-np.sum(p * np.log2(p)) / np.log2(S))      # normalize by log2(S)


def entropy_profile(key):
    """Returns: (per-row Ex array, per-column Ey array) — paper Fig 4g."""
    ex = np.array([_line_entropy(key[r, :]) for r in range(key.shape[0])])
    ey = np.array([_line_entropy(key[:, c]) for c in range(key.shape[1])])
    return ex, ey


def entropy_axis(key, axis):
    """Returns: (mean, standard deviation). axis=0 → rows (Ex), axis=1 → columns (Ey)."""
    ex, ey = entropy_profile(key)
    arr = ex if axis == 0 else ey
    return float(arr.mean()), float(arr.std())


# ===========================================================================
# Hamming distance / correlation
# ===========================================================================
def fractional_hd(a, b):
    """Fraction of differing cells (0 = identical, 1 = all different). Ideal for ternary = 0.667."""
    return float((a != b).mean())


def pearson_keys(a, b):
    x, y = a.flatten().astype(float), b.flatten().astype(float)
    return 0.0 if x.std() == 0 or y.std() == 0 else float(np.corrcoef(x, y)[0, 1])


def inter_hd(keys):
    """Pairwise inter-HD between tags (uniqueness). keys = {name: key}."""
    names = list(keys)
    return {a + " vs " + b: fractional_hd(keys[a], keys[b])
            for a, b in itertools.combinations(names, 2)}


def perturb(raw, s=1.0):
    """Simulated re-capture perturbation: brightness, noise, focus, rotation, translation."""
    h, w = raw.shape[:2]
    out = raw.astype(np.float32)
    out *= (1.0 + RNG.uniform(-0.03, 0.03) * s)
    out += RNG.normal(0, 4.0 * s, out.shape)
    out = np.clip(out, 0, 255).astype(np.uint8)
    if RNG.random() < 0.5 * s:
        out = cv2.GaussianBlur(out, (3, 3), 0)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), RNG.uniform(-1, 1) * s, 1.0)
    M[0, 2] += RNG.uniform(-2, 2) * s; M[1, 2] += RNG.uniform(-2, 2) * s
    return cv2.warpAffine(out, M, (w, h), borderMode=cv2.BORDER_REPLICATE)


def intra_hd(raws, refs, R=25):
    """Simulated re-capture intra-HD (reliability). Estimated with perturbation since no real re-captured images are available."""
    out = {}
    for name, raw in raws.items():
        out[name] = [fractional_hd(refs[name], E.extract_key(perturb(raw))[0])
                     for _ in range(R)]
    return out


# ===========================================================================
# Bit uniformity / data capacity
# ===========================================================================
def bit_population(keys):
    """Returns: {name: {0:%,1:%,2:%}} — ideal 33.3%."""
    return {n: {v: float((k == v).mean() * 100) for v in range(S)} for n, k in keys.items()}


def degree_of_freedom(p, sd):
    """Paper Eq. 5: DoF = p(1-p)/σ² (number of independent bits). Data capacity = S^DoF."""
    return float(p * (1 - p) / (sd ** 2)) if sd > 0 else float("inf")


# ===========================================================================
# Combined report
# ===========================================================================
def full_report(keys, raws=None, R=25):
    names = list(keys)
    inter = inter_hd(keys)                       # empty dict if there is only one image
    iv = np.array(list(inter.values())) if inter else np.array([np.nan])
    pear = {a + " vs " + b: pearson_keys(keys[a], keys[b])
            for a, b in itertools.combinations(names, 2)}
    ent = {n: dict(Ex=entropy_axis(keys[n], 0), Ey=entropy_axis(keys[n], 1)) for n in names}
    bits = bit_population(keys)

    rep = dict(
        method="Method 4: fixed 20x20 grid + size-based ternary",
        n_tags=len(names),
        entropy={n: dict(Ex_mean=round(ent[n]["Ex"][0], 4), Ex_sd=round(ent[n]["Ex"][1], 4),
                         Ey_mean=round(ent[n]["Ey"][0], 4), Ey_sd=round(ent[n]["Ey"][1], 4))
                 for n in names},
        entropy_overall=dict(
            Ex_mean=round(float(np.mean([ent[n]["Ex"][0] for n in names])), 4),
            Ey_mean=round(float(np.mean([ent[n]["Ey"][0] for n in names])), 4), ideal=1.0),
        bit_population_pct={n: {str(v): round(bits[n][v], 2) for v in range(S)} for n in names},
        bit_uniformity=dict(
            {str(v): dict(mean=round(float(np.mean([bits[n][v] for n in names])), 2),
                          sd=round(float(np.std([bits[n][v] for n in names])), 2))
             for v in range(S)}, ideal=round(100 / S, 1)),
        inter_HD={k: round(v, 4) for k, v in inter.items()},
        inter_HD_mean=round(float(iv.mean()), 4) if inter else None,
        inter_HD_sd=round(float(iv.std()), 4) if inter else None,
        ideal_inter_ternary=round((S - 1) / S, 4),
        pearson={k: round(v, 4) for k, v in pear.items()},
        pearson_mean=round(float(np.mean(list(pear.values()))), 4) if pear else None,
        ideal_pearson=0.0,
    )
    if not inter:
        rep["note"] = "Only one image, so inter-HD/Pearson (tag-to-tag comparison) cannot be computed"
    if raws is not None:
        per = intra_hd(raws, keys, R)
        av = np.array([v for vs in per.values() for v in vs])
        rep["intra_HD"] = dict(
            per_sample={n: round(float(np.mean(v)), 4) for n, v in per.items()},
            mean=round(float(av.mean()), 4), sd=round(float(av.std()), 4),
            reads_per_sample=R, ideal=0.0,
            note="Estimated by perturbation (noise/rotation/translation) simulation since no real re-captured images are available")
        if inter:
            rep["separation_inter_minus_intra"] = round(float(iv.mean() - av.mean()), 4)
    rep["data_capacity"] = dict(
        nominal_cells=int(keys[names[0]].size),
        degree_of_freedom=(round(degree_of_freedom(float(iv.mean()), float(iv.std())), 1)
                           if inter and iv.std() > 0 else None),
        note="DoF = p(1-p)/σ² (paper Eq. 5); statistical confidence is low when there are few tags")
    return rep


def main():
    keys, raws, _ = E.extract_all()                 # auto-process the whole input folder
    if not keys:
        print("No images found. Please put them in this folder:\n  " + E.INPUT_DIR)
        return
    rep = full_report(keys, raws)
    os.makedirs(E.OUTDIR, exist_ok=True)
    with open(os.path.join(E.OUTDIR, "metrics.json"), "w") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)
    print(json.dumps(rep, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
