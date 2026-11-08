#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
puf_metrics.py  —  [2] PUF 분석 지표 (순수 계산, 그림 없음)
EN: puf_metrics.py  —  [2] PUF analysis metrics (pure computation, no plots)

지표
EN: Metrics
  entropy_axis(key, axis)      행/열별 Shannon 엔트로피 (log2(3) 정규화)  [논문 식1-4]
  EN: entropy_axis(key, axis): Shannon entropy per row/column (normalized by log2(3)) [paper eq. 1-4]
  entropy_profile(key)         행별 Ex 배열, 열별 Ey 배열 (Fig 4g용)
  EN: entropy_profile(key): array of per-row Ex, array of per-column Ey (for Fig 4g)
  fractional_hd(a, b)          Fractional Hamming Distance (다른 칸 비율)
  EN: fractional_hd(a, b): Fractional Hamming Distance (fraction of cells that differ)
  inter_hd(keys)               태그 쌍별 inter-HD (고유성, 이상 0.667)
  EN: inter_hd(keys): inter-HD for each pair of tags (uniqueness, ideal 0.667)
  intra_hd(raws, ref, R)       재촬영 시뮬레이션 intra-HD (신뢰성, 이상 0)
  EN: intra_hd(raws, ref, R): re-capture simulation intra-HD (reliability, ideal 0)
  pearson_keys(a, b)           키 간 Pearson 상관 (이상 0)
  EN: pearson_keys(a, b): Pearson correlation between keys (ideal 0)
  bit_population(keys)         비트 0/1/2 점유율 (이상 33.3%)
  EN: bit_population(keys): share of bits 0/1/2 (ideal 33.3%)
  degree_of_freedom(p, sd)     자유도/데이터 용량 [논문 식5]
  EN: degree_of_freedom(p, sd): degrees of freedom / data capacity [paper eq. 5]
  full_report(keys, raws)      위 전부를 dict로
  EN: full_report(keys, raws): all of the above as a dict

CLI:  py puf_metrics.py        # 추출 → 전체 지표 계산 → PUF_최종결과/metrics.json
EN: CLI: py puf_metrics.py   # extract -> compute all metrics -> PUF_최종결과 (PUF final results)/metrics.json
"""
import os, json, itertools
import numpy as np
import cv2
import puf_extract as E

S = 3                       # 삼진  | EN: ternary (3 possible values: 0/1/2)
RNG = np.random.default_rng(42)


# ===========================================================================
# 엔트로피 (논문 식 1-4)
# EN: Entropy (paper eq. 1-4)
# ===========================================================================
def _line_entropy(line):
    p = np.array([(line == v).mean() for v in range(S)])
    p = p[p > 0]
    return float(-np.sum(p * np.log2(p)) / np.log2(S))      # log2(S)로 정규화  | EN: normalize by log2(S)


def entropy_profile(key):
    """반환: (행별 Ex 배열, 열별 Ey 배열) — 논문 Fig 4g.  (EN: Returns: (per-row Ex array, per-column Ey array) — paper Fig 4g.)"""
    ex = np.array([_line_entropy(key[r, :]) for r in range(key.shape[0])])
    ey = np.array([_line_entropy(key[:, c]) for c in range(key.shape[1])])
    return ex, ey


def entropy_axis(key, axis):
    """반환: (평균, 표준편차). axis=0 → 행(Ex), axis=1 → 열(Ey).  (EN: Returns: (mean, standard deviation). axis=0 -> rows (Ex), axis=1 -> columns (Ey).)"""
    ex, ey = entropy_profile(key)
    arr = ex if axis == 0 else ey
    return float(arr.mean()), float(arr.std())


# ===========================================================================
# 해밍 거리 / 상관
# EN: Hamming distance / correlation
# ===========================================================================
def fractional_hd(a, b):
    """다른 칸의 비율 (0=동일, 1=전부 다름). 삼진 이상값 = 0.667.  (EN: Fraction of cells that differ (0=identical, 1=all different). Ideal value for ternary = 0.667.)"""
    return float((a != b).mean())


def pearson_keys(a, b):
    x, y = a.flatten().astype(float), b.flatten().astype(float)
    return 0.0 if x.std() == 0 or y.std() == 0 else float(np.corrcoef(x, y)[0, 1])


def inter_hd(keys):
    """태그 쌍별 inter-HD (고유성). keys = {name: key}.  (EN: inter-HD for each pair of tags (uniqueness). keys = {name: key}.)"""
    names = list(keys)
    return {a + " vs " + b: fractional_hd(keys[a], keys[b])
            for a, b in itertools.combinations(names, 2)}


def perturb(raw, s=1.0):
    """재촬영 섭동 시뮬레이션: 밝기·노이즈·초점·회전·이동.  (EN: Simulated re-capture perturbation: brightness, noise, focus, rotation, shift.)"""
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
    """재촬영 시뮬레이션 intra-HD (신뢰성). 실제 재촬영본이 없어 섭동으로 추정.  (EN: Simulated re-capture intra-HD (reliability). No real re-captured photos exist, so it is estimated with perturbations.)"""
    out = {}
    for name, raw in raws.items():
        out[name] = [fractional_hd(refs[name], E.extract_key(perturb(raw))[0])
                     for _ in range(R)]
    return out


# ===========================================================================
# 비트 균일도 / 데이터 용량
# EN: Bit uniformity / data capacity
# ===========================================================================
def bit_population(keys):
    """반환: {name: {0:%,1:%,2:%}} — 이상 33.3%.  (EN: Returns: {name: {0:%,1:%,2:%}} — ideal 33.3%.)"""
    return {n: {v: float((k == v).mean() * 100) for v in range(S)} for n, k in keys.items()}


def degree_of_freedom(p, sd):
    """논문 식5: DoF = p(1-p)/σ² (독립 비트 수). 데이터 용량 = S^DoF.  (EN: Paper eq. 5: DoF = p(1-p)/σ² (number of independent bits). Data capacity = S^DoF.)"""
    return float(p * (1 - p) / (sd ** 2)) if sd > 0 else float("inf")


# ===========================================================================
# 통합 리포트
# EN: Combined report
# ===========================================================================
def full_report(keys, raws=None, R=25):
    names = list(keys)
    inter = inter_hd(keys)                       # 이미지 1장이면 빈 dict  | EN: empty dict if there is only 1 image
    iv = np.array(list(inter.values())) if inter else np.array([np.nan])
    pear = {a + " vs " + b: pearson_keys(keys[a], keys[b])
            for a, b in itertools.combinations(names, 2)}
    ent = {n: dict(Ex=entropy_axis(keys[n], 0), Ey=entropy_axis(keys[n], 1)) for n in names}
    bits = bit_population(keys)

    rep = dict(
        method="방식4: 격자고정 20x20 + 크기 삼진",  # EN: text means: "Method 4: fixed 20x20 grid + size-based ternary"
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
        rep["note"] = "이미지가 1장이라 inter-HD/Pearson(태그 간 비교)은 계산 불가"  # EN: text means: "Only 1 image, so inter-HD/Pearson (comparison between tags) cannot be computed"
    if raws is not None:
        per = intra_hd(raws, keys, R)
        av = np.array([v for vs in per.values() for v in vs])
        rep["intra_HD"] = dict(
            per_sample={n: round(float(np.mean(v)), 4) for n, v in per.items()},
            mean=round(float(av.mean()), 4), sd=round(float(av.std()), 4),
            reads_per_sample=R, ideal=0.0,
            note="실제 재촬영본이 없어 섭동(노이즈/회전/이동) 시뮬레이션으로 추정")  # EN: text means: "No real re-captured photos, so estimated with a perturbation (noise/rotation/shift) simulation"
        if inter:
            rep["separation_inter_minus_intra"] = round(float(iv.mean() - av.mean()), 4)
    rep["data_capacity"] = dict(
        nominal_cells=int(keys[names[0]].size),
        degree_of_freedom=(round(degree_of_freedom(float(iv.mean()), float(iv.std())), 1)
                           if inter and iv.std() > 0 else None),
        note="DoF = p(1-p)/σ² (논문 식5); 태그 수가 적으면 통계 신뢰도 낮음")  # EN: text means: "DoF = p(1-p)/σ² (paper eq. 5); with few tags, statistical reliability is low"
    return rep


def main():
    keys, raws, _ = E.extract_all()                 # 입력 폴더 전체 자동 처리  | EN: automatically process everything in the input folder
    if not keys:
        print("이미지가 없습니다. 다음 폴더에 넣어주세요:\n  " + E.INPUT_DIR)  # EN: prints: "No images found. Please put them in this folder:"
        return
    rep = full_report(keys, raws)
    os.makedirs(E.OUTDIR, exist_ok=True)
    with open(os.path.join(E.OUTDIR, "metrics.json"), "w") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)
    print(json.dumps(rep, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
