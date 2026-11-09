#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all.py  —  [4] 전체 실행 (추출 → 지표 → 그림)  한 번에

★ 사용법
   1) PUF_논문재현/입력이미지/  폴더에 이미지를 넣는다 (몇 장이든, 확장자 무관)
   2) py run_all.py             → 자동으로 전부 처리

   py run_all.py --fast         # intra-HD 시뮬레이션 생략(빠름)
   py run_all.py <폴더경로>      # 다른 폴더의 이미지를 처리

산출 -> PUF_최종결과/
   <이름>_key.csv, <이름>_tricolor.png, <이름>_spots.png     (추출)
   metrics.json                                            (지표)
   FIG_*.png                                               (그림)
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
    imgs = E.list_images(input_dir)      # None이면 input img/ 폴더 자동 탐색
    if not imgs:
        print("이미지가 없습니다. 다음 폴더에 이미지를 넣고 다시 실행하세요:\n  %s" % E.INPUT_DIR)
        return
    print("입력 폴더 : %s" % os.path.dirname(imgs[0][1]))
    print("이미지     : %d장  (%s)" % (len(imgs), ", ".join(n for n, _ in imgs)))

    # ---- [1] 추출 -----------------------------------------------------------
    print("\n[1] 이미지 → 키 추출")
    keys, raws = {}, {}
    for name, path in imgs:
        raw = E.imread_u(path)
        if raw is None:
            print("   [skip] 읽기 실패: %s" % os.path.basename(path)); continue
        key, cells, info = E.extract_key(raw)
        keys[name], raws[name] = key, raw
        E.save_outputs(name, key, cells, info["img"])
        print("   %-14s spots=%3d  thr=%s  bits=%s"
              % (name, info["meta"]["n_spots"], info["meta"]["size_thr"],
                 info["meta"]["bit_pct"]))
    if not keys:
        print("처리 가능한 이미지가 없습니다."); return

    # ---- [2] 지표 -----------------------------------------------------------
    print("\n[2] 지표 계산" + (" (intra 생략)" if fast else " (intra 시뮬 포함, 시간 소요)"))
    rep = M.full_report(keys, None if fast else raws)
    with open(os.path.join(E.OUTDIR, "metrics.json"), "w") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)

    # ---- [3] 그림 -----------------------------------------------------------
    print("[3] 그림 생성")
    V.plot_all(keys, None if fast else raws)

    # ---- 요약 ---------------------------------------------------------------
    print("\n=== 요약 (이미지 %d장) ===" % len(keys))
    print("  Ex/Ey 평균      : %.3f / %.3f  (이상 1.0)"
          % (rep["entropy_overall"]["Ex_mean"], rep["entropy_overall"]["Ey_mean"]))
    print("  비트 균일도     : " + ", ".join(
        "%s=%.1f%%" % (v, rep["bit_uniformity"][v]["mean"]) for v in ("0", "1", "2")))
    if rep.get("inter_HD_mean") is not None:
        print("  inter-HD        : %.3f ± %.3f  (이상 0.667)"
              % (rep["inter_HD_mean"], rep["inter_HD_sd"]))
        print("  Pearson         : %.3f  (이상 0)" % rep["pearson_mean"])
    else:
        print("  inter-HD        : - (이미지 2장 이상이어야 계산)")
    if "intra_HD" in rep:
        print("  intra-HD (시뮬) : %.3f ± %.3f  (이상 0)"
              % (rep["intra_HD"]["mean"], rep["intra_HD"]["sd"]))
        if "separation_inter_minus_intra" in rep:
            print("  분리도          : %.3f" % rep["separation_inter_minus_intra"])
    print("\n산출물 -> %s" % E.OUTDIR)


if __name__ == "__main__":
    main()
