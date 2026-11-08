#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
puf_plots.py  —  [3] 지표 시각화 (논문 Fig 4f/4g 스타일 포함)
EN: puf_plots.py  —  [3] Metric visualization (including paper Fig 4f/4g style)

그림
EN: Figures
  plot_entropy_g(keys)        행별 Ex / 열별 Ey 산점도        -> FIG_entropy_g.png      [Fig 4g]
  EN: plot_entropy_g(keys): per-row Ex / per-column Ey scatter plot -> FIG_entropy_g.png [Fig 4g]
  plot_bit_population(keys)   태그별 비트 0/1/2 점유율 산점도  -> FIG_bit_population.png [Fig 4f]
  EN: plot_bit_population(keys): scatter of bit 0/1/2 share per tag -> FIG_bit_population.png [Fig 4f]
  plot_bit_each(keys)         비트별 분리 패널 + 공간분포 맵   -> FIG_bit_each_*.png
  EN: plot_bit_each(keys): separate panel per bit + spatial distribution map -> FIG_bit_each_*.png
  plot_hd(keys, intra)        inter/intra HD 히스토그램·행렬·막대 -> FIG_HD_*.png
  EN: plot_hd(keys, intra): inter/intra HD histogram, matrix, bars -> FIG_HD_*.png
  plot_all(keys, raws)        위 전부
  EN: plot_all(keys, raws): all of the above

CLI:  py puf_plots.py         # 추출 → 전 그림 생성 → PUF_최종결과/FIG_*.png
EN: CLI: py puf_plots.py   # extract -> generate all figures -> PUF_최종결과 (PUF final results)/FIG_*.png
"""
import os, itertools
import numpy as np
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import puf_extract as E
import puf_metrics as M

# 논문 색: '0'=노랑, '1'=청록, '2'=자주
# EN: Paper colors: '0'=yellow, '1'=teal, '2'=purple
CBIT = {0: "#E8C400", 1: "#17A589", 2: "#7D3C98"}
BNAME = {0: "'0' bit (none/faint)", 1: "'1' bit (medium)", 2: "'2' bit (large)"}


def _save(fig, path):
    """한글 경로 대응 저장.  (EN: Save in a way that works with Korean (non-ASCII) paths.)"""
    tmp = os.path.join(os.environ.get("TEMP", E.OUTDIR), "_plt.png")
    fig.savefig(tmp, dpi=140); plt.close(fig)
    with open(tmp, "rb") as r, open(path, "wb") as w:
        w.write(r.read())


# ---------------------------------------------------------------- Fig 4g ---
def plot_entropy_g(keys, outdir):
    names = list(keys); n = len(names)
    fig, axes = plt.subplots(2, n, figsize=(4 * n, 7), squeeze=False)
    for j, f in enumerate(names):
        ex, ey = M.entropy_profile(keys[f])
        N = len(ex)
        for ax, arr, xl, yl in ((axes[0, j], ex, "Row", "$E_x$"),
                                (axes[1, j], ey, "Column", "$E_y$")):
            ax.scatter(np.arange(1, N + 1), arr, s=55, facecolors="none",
                       edgecolors="red", linewidths=1.5)
            ax.set_ylim(0, 1.08); ax.set_xlim(0, N + 1)
            ax.set_yticks(np.arange(0, 1.01, 0.2))
            ax.set_xlabel(xl, fontsize=12, fontweight="bold")
            ax.set_ylabel(yl, fontsize=13, fontweight="bold")
        axes[0, j].set_title(f, fontsize=12)
    fig.suptitle("Per-row $E_x$ / per-column $E_y$  (paper Fig.4g)", fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    _save(fig, os.path.join(outdir, "FIG_entropy_g.png"))


# ---------------------------------------------------------------- Fig 4f ---
def plot_bit_population(keys, outdir):
    names = list(keys); n = len(names)
    x = np.arange(1, n + 1)
    pct = {v: [float((keys[f] == v).mean() * 100) for f in names] for v in (0, 1, 2)}
    dodge = {0: -0.16, 1: 0.0, 2: 0.16}                  # 33%에 겹치므로 살짝 어긋나게  | EN: nudge slightly sideways because the points overlap near 33%
    for zoom, suffix in ((False, ""), (True, "_zoom")):
        fig, ax = plt.subplots(figsize=(8.5, 5.0))
        for v in (0, 1, 2):
            ax.scatter(x + dodge[v], pct[v], s=100, facecolors="none",
                       edgecolors=CBIT[v], linewidths=2, label="'%d' bit" % v)
        ax.axhline(100 / 3, color="gray", ls=":", lw=1, label="ideal 33.3%")
        ax.set_xlim(0, n + 1); ax.set_ylim((28, 40) if zoom else (0, 100))
        ax.set_xticks(x)
        ax.set_xlabel("2D tags", fontsize=13, fontweight="bold")
        ax.set_ylabel("Bits population (%)" + (" [zoom]" if zoom else ""),
                      fontsize=13, fontweight="bold")
        ax.legend(fontsize=11, loc="upper right")
        fig.tight_layout()
        _save(fig, os.path.join(outdir, "FIG_bit_population%s.png" % suffix))


def plot_bit_each(keys, outdir):
    """비트별 분리 패널 + 20x20 공간분포 맵.  (EN: Separate panel per bit + 20x20 spatial distribution map.)"""
    names = list(keys); n = len(names); x = np.arange(1, n + 1)
    pct = {v: [float((keys[f] == v).mean() * 100) for f in names] for v in (0, 1, 2)}
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), sharey=True)
    for j, v in enumerate((0, 1, 2)):
        axes[j].scatter(x, pct[v], s=110, facecolors="none", edgecolors=CBIT[v], linewidths=2)
        axes[j].axhline(100 / 3, color="gray", ls=":", lw=1)
        axes[j].set_xlim(0, n + 1); axes[j].set_ylim(0, 100); axes[j].set_xticks(x)
        axes[j].set_xlabel("2D tags", fontsize=12, fontweight="bold")
        axes[j].set_title(BNAME[v], fontsize=12)
    axes[0].set_ylabel("Bits population (%)", fontsize=12, fontweight="bold")
    fig.tight_layout(); _save(fig, os.path.join(outdir, "FIG_bit_each_population.png"))

    N = keys[names[0]].shape[0]
    fig, axes = plt.subplots(n, 3, figsize=(10.5, 3.2 * n), squeeze=False)
    for i, f in enumerate(names):
        for j, v in enumerate((0, 1, 2)):
            ax = axes[i, j]; mask = (keys[f] == v).astype(int)
            ax.imshow(mask, cmap=ListedColormap(["#EDEDED", CBIT[v]]), vmin=0, vmax=1)
            ax.set_xticks([]); ax.set_yticks([])
            ax.set_xlabel("%d cells (%.1f%%)" % (mask.sum(), mask.sum() / (N * N) * 100), fontsize=9)
            if i == 0: ax.set_title(BNAME[v], fontsize=12)
            if j == 0: ax.set_ylabel(f, fontsize=11)
    fig.suptitle("Where each bit sits on the %dx%d map" % (N, N), fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    _save(fig, os.path.join(outdir, "FIG_bit_each_map.png"))


# ------------------------------------------------------------ HD figures ---
def plot_hd(keys, intra_per, outdir):
    names = list(keys); n = len(names)
    inter = M.inter_hd(keys)
    iv = np.array(list(inter.values()))
    av = np.array([v for vs in intra_per.values() for v in vs]) if intra_per else np.array([])
    if not inter and not av.size:
        return                                    # 이미지 1장 + intra 없음 → 그릴 것 없음  | EN: 1 image and no intra -> nothing to plot

    # 분포 히스토그램
    # EN: Distribution histogram
    fig, ax = plt.subplots(figsize=(8, 4.6))
    bins = np.linspace(0, 1, 26)
    if av.size:
        ax.hist(av, bins=bins, color="#2E86C1", alpha=0.85,
                label="Intra-HD (reliability)\nmean=%.3f" % av.mean())
    if iv.size:
        ax.hist(iv, bins=bins, color="#E74C3C", alpha=0.85,
                label="Inter-HD (uniqueness)\nmean=%.3f" % iv.mean())
    ax.axvline(2 / 3, color="green", ls=":", lw=1.8, label="ideal inter 0.667")
    ax.set_xlim(0, 1); ax.set_xlabel("Fractional Hamming distance"); ax.set_ylabel("Count")
    ax.set_title("Inter- vs Intra-Hamming distance"); ax.legend(fontsize=9, loc="upper center")
    fig.tight_layout(); _save(fig, os.path.join(outdir, "FIG_HD_distribution.png"))

    # HD 행렬 (대각=intra, 비대각=inter)
    # EN: HD matrix (diagonal=intra, off-diagonal=inter)
    mat = np.zeros((n, n))
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            mat[i, j] = np.mean(intra_per[a]) if (i == j and intra_per) else \
                        (0 if i == j else M.fractional_hd(keys[a], keys[b]))
    fig, ax = plt.subplots(figsize=(5.8, 5.0))
    im = ax.imshow(mat, cmap="viridis", vmin=0, vmax=0.75)
    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels(names, rotation=30, ha="right"); ax.set_yticklabels(names)
    for i in range(n):
        for j in range(n):
            ax.text(j, i, "%.2f" % mat[i, j], ha="center", va="center",
                    color="white" if mat[i, j] < 0.45 else "black")
    ax.set_title("Pairwise HD matrix\n(diag = mean intra, off-diag = inter)")
    fig.colorbar(im, ax=ax, fraction=0.046, label="Hamming distance")
    fig.tight_layout(); _save(fig, os.path.join(outdir, "FIG_HD_matrix.png"))

    # 막대: 샘플별 intra / 쌍별 inter
    # EN: Bars: intra per sample / inter per pair
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
    if intra_per:
        a1.bar(range(n), [np.mean(intra_per[f]) for f in names],
               yerr=[np.std(intra_per[f]) for f in names], capsize=5, color="#2E86C1")
    a1.set_xticks(range(n)); a1.set_xticklabels(names, rotation=20)
    a1.set_ylabel("Intra-HD"); a1.set_title("Reliability per sample (lower=better)")
    pairs = list(inter)
    a2.bar(range(len(pairs)), list(inter.values()), color="#E74C3C")
    a2.axhline(2 / 3, color="green", ls=":", lw=1.8, label="ideal 0.667")
    a2.set_xticks(range(len(pairs)))
    a2.set_xticklabels([p.replace(" vs ", "\nvs ") for p in pairs], fontsize=8)
    a2.set_ylim(0, 0.8); a2.set_ylabel("Inter-HD")
    a2.set_title("Uniqueness per pair (higher=better)"); a2.legend(fontsize=9)
    fig.tight_layout(); _save(fig, os.path.join(outdir, "FIG_HD_bars.png"))


def plot_all(keys, raws=None, outdir=None, R=25):
    outdir = outdir or E.OUTDIR
    os.makedirs(outdir, exist_ok=True)
    plot_entropy_g(keys, outdir)
    plot_bit_population(keys, outdir)
    plot_bit_each(keys, outdir)
    intra = M.intra_hd(raws, keys, R) if raws is not None else {}
    plot_hd(keys, intra, outdir)
    return intra


def main():
    keys, raws, _ = E.extract_all()                  # 입력 폴더 전체 자동 처리  | EN: automatically process everything in the input folder
    if not keys:
        print("이미지가 없습니다. 다음 폴더에 넣어주세요:\n  " + E.INPUT_DIR)  # EN: prints: "No images found. Please put them in this folder:"
        return
    plot_all(keys, raws)
    print("figures -> %s/FIG_*.png" % E.OUTDIR)


if __name__ == "__main__":
    main()
