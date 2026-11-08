#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all.py  —  [4] 전체 실행 (추출 → 지표 → 그림)  한 번에
EN: run_all.py  —  [4] Run everything (extract -> metrics -> figures) in one go

★ 사용법
EN: ★ How to use
   1) PUF_논문재현/입력이미지/  폴더에 이미지를 넣는다 (몇 장이든, 확장자 무관)
   EN: 1) Put images in the PUF_논문재현/입력이미지/ (PUF_paper_reproduction/input_images/) folder (any number, any extension)
   2) py run_all.py             → 자동으로 전부 처리
   EN: 2) py run_all.py             -> processes everything automatically

   py run_all.py --fast         # intra-HD 시뮬레이션 생략(빠름)
   EN: py run_all.py --fast         # skip the intra-HD simulation (fast)
   py run_all.py <폴더경로>      # 다른 폴더의 이미지를 처리
   EN: py run_all.py <folder path>  # process images in a different folder

산출 -> PUF_최종결과/
EN: Outputs -> PUF_최종결과/ (PUF final results)
   <이름>_key.csv, <이름>_tricolor.png, <이름>_spots.png     (추출)
   EN: <name>_key.csv, <name>_tricolor.png, <name>_spots.png     (extraction)
   metrics.json                                            (지표)
   EN: metrics.json                                            (metrics)
   FIG_*.png                                               (그림)
   EN: FIG_*.png                                               (figures)
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
    imgs = E.list_images(input_dir)      # None이면 input img/ 폴더 자동 탐색  | EN: if None, automatically searches the input img/ folder
    if not imgs:
        print("이미지가 없습니다. 다음 폴더에 이미지를 넣고 다시 실행하세요:\n  %s" % E.INPUT_DIR)  # EN: prints: "No images found. Put images in this folder and run again:"
        return
    print("입력 폴더 : %s" % os.path.dirname(imgs[0][1]))  # EN: prints: "Input folder : %s"
    print("이미지     : %d장  (%s)" % (len(imgs), ", ".join(n for n, _ in imgs)))  # EN: prints: "Images : %d  (names)"

    # ---- [1] 추출 -----------------------------------------------------------
    # EN: ---- [1] Extraction
    print("\n[1] 이미지 → 키 추출")  # EN: prints: "[1] Image -> key extraction"
    keys, raws = {}, {}
    for name, path in imgs:
        raw = E.imread_u(path)
        if raw is None:
            print("   [skip] 읽기 실패: %s" % os.path.basename(path)); continue  # EN: prints: "[skip] failed to read: %s"
        key, cells, info = E.extract_key(raw)
        keys[name], raws[name] = key, raw
        E.save_outputs(name, key, cells, info["img"])
        print("   %-14s spots=%3d  thr=%s  bits=%s"
              % (name, info["meta"]["n_spots"], info["meta"]["size_thr"],
                 info["meta"]["bit_pct"]))
    if not keys:
        print("처리 가능한 이미지가 없습니다."); return  # EN: prints: "No images could be processed."

    # ---- [2] 지표 -----------------------------------------------------------
    # EN: ---- [2] Metrics
    print("\n[2] 지표 계산" + (" (intra 생략)" if fast else " (intra 시뮬 포함, 시간 소요)"))  # EN: prints: "[2] Computing metrics" + " (intra skipped)" or " (includes intra simulation, takes time)"
    rep = M.full_report(keys, None if fast else raws)
    with open(os.path.join(E.OUTDIR, "metrics.json"), "w") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)

    # ---- [3] 그림 -----------------------------------------------------------
    # EN: ---- [3] Figures
    print("[3] 그림 생성")  # EN: prints: "[3] Generating figures"
    V.plot_all(keys, None if fast else raws)

    # ---- 요약 ---------------------------------------------------------------
    # EN: ---- Summary
    print("\n=== 요약 (이미지 %d장) ===" % len(keys))  # EN: prints: "=== Summary (%d images) ==="
    print("  Ex/Ey 평균      : %.3f / %.3f  (이상 1.0)"  # EN: prints: "Ex/Ey mean : ... (ideal 1.0)"
          % (rep["entropy_overall"]["Ex_mean"], rep["entropy_overall"]["Ey_mean"]))
    print("  비트 균일도     : " + ", ".join(  # EN: prints: "Bit uniformity : ..."
        "%s=%.1f%%" % (v, rep["bit_uniformity"][v]["mean"]) for v in ("0", "1", "2")))
    if rep.get("inter_HD_mean") is not None:
        print("  inter-HD        : %.3f ± %.3f  (이상 0.667)"  # EN: prints: "inter-HD : ... (ideal 0.667)"
              % (rep["inter_HD_mean"], rep["inter_HD_sd"]))
        print("  Pearson         : %.3f  (이상 0)" % rep["pearson_mean"])  # EN: prints: "Pearson : ... (ideal 0)"
    else:
        print("  inter-HD        : - (이미지 2장 이상이어야 계산)")  # EN: prints: "inter-HD : - (needs at least 2 images to compute)"
    if "intra_HD" in rep:
        print("  intra-HD (시뮬) : %.3f ± %.3f  (이상 0)"  # EN: prints: "intra-HD (simulated) : ... (ideal 0)"
              % (rep["intra_HD"]["mean"], rep["intra_HD"]["sd"]))
        if "separation_inter_minus_intra" in rep:
            print("  분리도          : %.3f" % rep["separation_inter_minus_intra"])  # EN: prints: "Separation : ..."
    print("\n산출물 -> %s" % E.OUTDIR)  # EN: prints: "Outputs -> %s"


if __name__ == "__main__":
    main()
