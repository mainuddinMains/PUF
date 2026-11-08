#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all.py  —  [4] Run everything (extraction → metrics → plots) at once

★ Usage
   1) Put images in the default input img/ folder (any number of supported image files)
   2) py run_all_english.py             → automatically process all images

   py run_all_english.py --fast         # skip intra-HD simulation (faster)
   py run_all_english.py <folder_path>  # process images from another folder

Outputs -> the folder configured by E.OUTDIR in puf_extract.py
   <name>_key.csv, <name>_tricolor.png, <name>_spots.png    (extraction)
   metrics.json                                            (metrics)
   FIG_*.png                                               (plots)
"""
import os, sys, json
import puf_extract as E
import puf_metrics as M
import puf_plots as V


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    fast = "--fast" in sys.argv
    input_dir = args[0] if args else None

    os.makedirs(E.OUTDIR, exist_ok=True)
    imgs = E.list_images(input_dir)      # If None, automatically search for the input img/ folder
    if not imgs:
        print("No images found. Put images in the following folder and run again:\n  %s" % E.INPUT_DIR)
        return
    print("Input folder: %s" % os.path.dirname(imgs[0][1]))
    print("Images      : %d file(s)  (%s)" % (len(imgs), ", ".join(n for n, _ in imgs)))

    # ---- [1] Extraction -----------------------------------------------------------
    print("\n[1] Image → key extraction")
    keys, raws = {}, {}
    for name, path in imgs:
        raw = E.imread_u(path)
        if raw is None:
            print("   [skip] Failed to read: %s" % os.path.basename(path)); continue
        key, cells, info = E.extract_key(raw)
        keys[name], raws[name] = key, raw
        E.save_outputs(name, key, cells, info["img"])
        print("   %-14s spots=%3d  thr=%s  bits=%s"
              % (name, info["meta"]["n_spots"], info["meta"]["size_thr"],
                 info["meta"]["bit_pct"]))
    if not keys:
        print("No processable images found."); return

    # ---- [2] Metrics -----------------------------------------------------------
    print("\n[2] Calculate metrics" + (" (skip intra-HD)" if fast else " (including intra-HD simulation, may take time)"))
    rep = M.full_report(keys, None if fast else raws)
    with open(os.path.join(E.OUTDIR, "metrics.json"), "w") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)

    # ---- [3] Plots -----------------------------------------------------------
    print("[3] Generate plots")
    V.plot_all(keys, None if fast else raws)

    # ---- Summary ---------------------------------------------------------------
    print("\n=== Summary (%d images) ===" % len(keys))
    print("  Ex/Ey average    : %.3f / %.3f  (ideal 1.0)"
          % (rep["entropy_overall"]["Ex_mean"], rep["entropy_overall"]["Ey_mean"]))
    print("  Bit uniformity   : " + ", ".join(
        "%s=%.1f%%" % (v, rep["bit_uniformity"][v]["mean"]) for v in ("0", "1", "2")))
    if rep.get("inter_HD_mean") is not None:
        print("  inter-HD        : %.3f ± %.3f  (ideal 0.667)"
              % (rep["inter_HD_mean"], rep["inter_HD_sd"]))
        print("  Pearson         : %.3f  (ideal 0)" % rep["pearson_mean"])
    else:
        print("  inter-HD        : - (requires at least 2 images)")
    if "intra_HD" in rep:
        print("  intra-HD (sim.)  : %.3f ± %.3f  (ideal 0)"
              % (rep["intra_HD"]["mean"], rep["intra_HD"]["sd"]))
        if "separation_inter_minus_intra" in rep:
            print("  Separation      : %.3f" % rep["separation_inter_minus_intra"])
    print("\nOutputs -> %s" % E.OUTDIR)


if __name__ == "__main__":
    main()
