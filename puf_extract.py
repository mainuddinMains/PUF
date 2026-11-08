#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
puf_extract.py  —  [1] 이미지 → PUF 키 추출  (방식4: 격자고정 20x20 + 크기 삼진)
EN: puf_extract.py  —  [1] Image -> PUF key extraction (Method 4: fixed 20x20 grid + size-based ternary)

파이프라인
EN: Pipeline
  [A] 전처리   : 원형시야 내접 정사각 크롭 → 리사이즈 → 노이즈제거 → Gaussian smoothing
  EN: [A] Preprocessing      : crop the square inscribed in the circular field of view -> resize -> denoise -> Gaussian smoothing
  [B] 스팟강조 : 큰 blur 배경추정 → background subtraction (= contrast 이미지)
  EN: [B] Spot enhancement   : estimate background with a large blur -> background subtraction (= contrast image)
  [C] 스팟검출 : 이진화 → closing/opening → 연결성분(스팟=한 덩어리) → 모양필터 → 등가지름 W
  EN: [C] Spot detection     : binarize -> closing/opening -> connected components (one spot = one blob) -> shape filter -> equivalent diameter W
  [D] 키 생성  : 20x20 격자 배정(중심, 셀당 1개) → 크기 삼분위(33/67%) → 0/1/2
  EN: [D] Key generation     : assign to 20x20 grid (by center, 1 per cell) -> size terciles (33/67%) -> 0/1/2

★ 사용법 : 이 코드와 같은 폴더의  input img/  에 이미지를 넣기만 하면 자동으로 전부 처리됩니다.
EN: ★ How to use: just put images in the  input img/  folder next to this code and they are all processed automatically.
   (png/jpg/jpeg/bmp/tif/webp 지원 · 장수 제한 없음 · 파일명 자유)
   EN: (supports png/jpg/jpeg/bmp/tif/webp · no limit on number of images · any file name)
   결과는 같은 폴더의  PUF_최종결과/  에 저장됩니다.
   EN: Results are saved in the  PUF_최종결과/ (PUF final results)  folder next to this code.

공개 함수
EN: Public functions
  list_images(dir=None)        -> [(이름, 경로), ...]     # 입력 폴더 자동 탐색
  EN: list_images(dir=None)       -> [(name, path), ...]   # auto-scan the input folder
  extract_key(raw_bgr)         -> (key, cells, info)     # numpy 이미지 1장 → 키
  EN: extract_key(raw_bgr)        -> (key, cells, info)    # one numpy image -> key
  extract_from_file(path)      -> (key, cells, info)     # 파일 경로 → 키
  EN: extract_from_file(path)     -> (key, cells, info)    # file path -> key
  extract_all(dir=None)        -> (keys, raws, metas)    # 폴더 전체 일괄 처리
  EN: extract_all(dir=None)       -> (keys, raws, metas)   # batch-process a whole folder
  render_tricolor(key)         -> BGR 이미지
  EN: render_tricolor(key)        -> BGR image
  render_spots(img,cells,key)  -> BGR 오버레이(스캔라인+동그라미)
  EN: render_spots(img,cells,key) -> BGR overlay (scan lines + circles)

CLI:  py puf_extract.py            # 입력 폴더 전체 추출 → PUF_최종결과/ 저장
EN: CLI: py puf_extract.py   # extract everything in the input folder -> save to PUF_최종결과/ (PUF final results)
의존: numpy, opencv-python
EN: Dependencies: numpy, opencv-python
"""
import os, csv, json
import numpy as np
import cv2

# ---------------------------------------------------------------------------
# 설정 (모든 파라미터를 한곳에)
# EN: Settings (all parameters in one place)
# ---------------------------------------------------------------------------
N          = 20            # 격자 크기 (20x20 고정 map)  | EN: grid size (fixed 20x20 map)
CANON_SIDE = 3024          # 크롭 정사각형 리사이즈 크기  | EN: size (px) the cropped square is resized to
DENOISE_H  = 7             # [A] fastNlMeans 강도  | EN: [A] fastNlMeans denoising strength
SMOOTH_SIG = 5             # [A] Gaussian smoothing σ
BG_SIG     = 80            # [B] 배경 추정 blur σ  | EN: [B] blur σ for background estimation
FLOOR      = 14            # [C] 스팟 최소 국소대비  | EN: [C] minimum local contrast for a spot
CLOSE_K    = 11            # [C] closing 커널(큰 스팟 구멍 메움)  | EN: [C] closing kernel (fills holes in large spots)
OPEN_K     = 3             # [C] opening 커널(점 노이즈 제거)  | EN: [C] opening kernel (removes dot noise)
MIN_AREA   = 120           # [C] 최소 스팟 면적(px)  | EN: [C] minimum spot area (px)
ASPECT_MIN = 0.45          # [C] 종횡비 하한(길쭉한 요철 배제)  | EN: [C] minimum aspect ratio (rejects elongated bumps)
EXTENT_MIN = 0.45          # [C] 채움도 하한(불규칙 요철 배제)  | EN: [C] minimum fill ratio (rejects irregular bumps)
TERCILE    = (33.3333, 66.6667)   # [D] 크기 삼분위(%)  | EN: [D] size terciles (%)

COLORS = {0: (170, 220, 150), 1: (40, 210, 240), 2: (130, 60, 50)}  # BGR 민트/노랑/남색  | EN: BGR mint/yellow/navy

HERE  = os.path.dirname(os.path.abspath(__file__))
# ---------------------------------------------------------------------------
# 입출력 폴더 : 이미지를 INPUT_DIR 에 넣기만 하면 자동으로 전부 처리됨
# EN: Input/output folders: just put images in INPUT_DIR and everything is processed automatically
# ---------------------------------------------------------------------------
EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp")

# ★ 이미지를 넣는 폴더 : 코드와 같은 폴더의  input img/   (없으면 아래 후보를 순서대로 탐색)
# EN: ★ Folder for images: input img/ next to this code (if missing, the candidates below are searched in order)
INPUT_DIR = os.path.join(HERE, "input img")
INPUT_CANDIDATES = [
    INPUT_DIR,                                                  # 코드/input img/  (기본)  | EN: code/input img/ (default)
    os.path.join(HERE, "입력이미지"),  # EN: "입력이미지" means "input images"
    os.path.normpath(os.path.join(HERE, "..", "input img")),    # 상위/input img/  | EN: parent/input img/
    os.path.normpath(os.path.join(HERE, "..", "..", "input img")),
    os.path.normpath(os.path.join(HERE, "..", "..", "..", "input img")),
]

# 산출물 폴더 : 코드와 같은 폴더의  PUF_최종결과/
# EN: Output folder: PUF_최종결과/ (PUF final results) next to this code
OUTDIR = os.path.join(HERE, "PUF_최종결과")  # EN: "PUF_최종결과" means "PUF final results"


def imwrite_u(path, img):
    """한글 경로 대응 저장(cv2.imwrite는 Windows 비ASCII 경로 실패).  (EN: Save with Korean-path support (cv2.imwrite fails on non-ASCII paths on Windows).)"""
    ok, buf = cv2.imencode(os.path.splitext(path)[1], img)
    if ok:
        buf.tofile(path)


def imread_u(path):
    """한글 경로 대응 읽기.  (EN: Read with Korean-path support.)"""
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def _scan(d):
    """폴더 안 이미지 파일 목록(정렬).  (EN: List of image files in a folder (sorted).)"""
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d) if f.lower().endswith(EXTS))


def list_images(input_dir=None):
    """이미지를 자동 탐색. 반환: [(이름, 경로), ...]  (이름 = 확장자 없는 파일명)
    EN: Auto-find images. Returns: [(name, path), ...]  (name = file name without extension)

    input_dir 를 주면 그 폴더만 사용하고,
    EN: If input_dir is given, only that folder is used;
    없으면 INPUT_CANDIDATES 를 순서대로 확인해 '이미지가 있는 첫 폴더'를 씁니다.
    EN: otherwise INPUT_CANDIDATES are checked in order and 'the first folder that has images' is used.
    """
    if input_dir:
        return [(os.path.splitext(f)[0], os.path.join(input_dir, f))
                for f in _scan(input_dir)]
    for d in INPUT_CANDIDATES:
        files = _scan(d)
        if files:
            return [(os.path.splitext(f)[0], os.path.join(d, f)) for f in files]
    os.makedirs(INPUT_DIR, exist_ok=True)                        # 하나도 없으면 폴더 생성  | EN: create the folder if none is found
    return []


# ===========================================================================
# [A] 전처리  +  [B] 스팟강조
# EN: [A] Preprocessing  +  [B] Spot enhancement
# ===========================================================================
def preprocess(raw):
    """반환: (정사각 BGR, field_mask, contrast). [A]크롭·smoothing + [B]배경제거.  (EN: Returns: (square BGR, field_mask, contrast). [A] crop + smoothing + [B] background removal.)"""
    gray0 = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(cv2.GaussianBlur(gray0, (5, 5), 0), 0, 255,
                          cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    (cx, cy), r = cv2.minEnclosingCircle(max(cnts, key=cv2.contourArea))
    half = int(r * 0.96 / (2 ** 0.5))                       # 내접 정사각형 반변  | EN: half-side of the inscribed square
    x0, y0 = max(0, int(cx - half)), max(0, int(cy - half))
    x1, y1 = min(raw.shape[1], int(cx + half)), min(raw.shape[0], int(cy + half))
    img = cv2.resize(raw[y0:y1, x0:x1], (CANON_SIDE, CANON_SIDE), interpolation=cv2.INTER_CUBIC)
    img = cv2.fastNlMeansDenoisingColored(img, None, DENOISE_H, DENOISE_H, 7, 21)
    field_mask = np.full((CANON_SIDE, CANON_SIDE), 255, np.uint8)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sm = cv2.GaussianBlur(gray, (0, 0), SMOOTH_SIG)         # [A] smoothing
    bg = cv2.GaussianBlur(sm, (0, 0), BG_SIG)               # [B] 조명 배경  | EN: [B] lighting background
    contrast = np.clip(bg.astype(np.int16) - sm.astype(np.int16), 0, 255).astype(np.uint8)
    return img, field_mask, contrast


# ===========================================================================
# [C] 스팟 검출
# EN: [C] Spot detection
# ===========================================================================
def detect_spots(contrast, field_mask):
    """반환: (스팟 리스트[{cx,cy,area,w}], 이진영상). 큰 스팟도 한 덩어리 = 1개.  (EN: Returns: (spot list [{cx,cy,area,w}], binary image). A large spot is still one blob = 1 spot.)"""
    binar = ((contrast > FLOOR).astype(np.uint8) * 255) & field_mask
    binar = cv2.morphologyEx(binar, cv2.MORPH_CLOSE,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (CLOSE_K, CLOSE_K)))
    binar = cv2.morphologyEx(binar, cv2.MORPH_OPEN,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (OPEN_K, OPEN_K)))
    n, lab, stats, cent = cv2.connectedComponentsWithStats(binar, 8)
    spots = []
    for i in range(1, n):
        area = float(stats[i, cv2.CC_STAT_AREA])
        if area < MIN_AREA:
            continue
        bw, bh = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        if min(bw, bh) / max(bw, bh) < ASPECT_MIN or area / (bw * bh) < EXTENT_MIN:
            continue
        cx, cy = cent[i]
        spots.append(dict(cx=float(cx), cy=float(cy), area=area,
                          w=2.0 * (area / np.pi) ** 0.5))    # 등가지름  | EN: equivalent diameter
    return spots, binar


# ===========================================================================
# [D] 키 생성
# EN: [D] Key generation
# ===========================================================================
def build_key(spots, side):
    """반환: (key NxN, cells, 셀크기, t1, t2). 스팟을 격자에 넣고 크기 삼분위로 삼진화.  (EN: Returns: (NxN key, cells, cell size, t1, t2). Puts spots into the grid and turns sizes into 0/1/2 using terciles.)"""
    cw = side / N
    cells = [[None] * N for _ in range(N)]
    for s in spots:
        r, c = min(N - 1, int(s["cy"] // cw)), min(N - 1, int(s["cx"] // cw))
        if cells[r][c] is None or s["area"] > cells[r][c]["area"]:
            cells[r][c] = s                                 # 셀당 면적 최대 1개  | EN: at most 1 spot per cell (the one with the largest area)
    W = np.zeros((N, N))
    for r in range(N):
        for c in range(N):
            if cells[r][c] is None:
                cells[r][c] = dict(w=0.0, area=0.0, cx=(c + .5) * cw, cy=(r + .5) * cw)
            W[r, c] = cells[r][c]["w"]
    t1, t2 = np.percentile(W, TERCILE)                      # 크기 삼분위  | EN: size terciles
    key = np.zeros((N, N), int)
    key[W >= t1] = 1
    key[W >= t2] = 2
    return key, cells, cw, float(t1), float(t2)


# ===========================================================================
# 공개 진입점
# EN: Public entry points
# ===========================================================================
def extract_key(raw):
    """numpy BGR 이미지 1장 → (key, cells, meta).  (EN: One numpy BGR image -> (key, cells, meta).)"""
    img, fm, contrast = preprocess(raw)
    spots, _ = detect_spots(contrast, fm)
    key, cells, cw, t1, t2 = build_key(spots, img.shape[0])
    meta = dict(n_spots=len(spots), size_thr=[round(t1, 1), round(t2, 1)],
                bit_pct={v: round(float((key == v).mean() * 100), 2) for v in (0, 1, 2)})
    return key, cells, dict(img=img, meta=meta, cells=cells)


def extract_from_file(path):
    """이미지 파일 경로 → (key, cells, info).  (EN: Image file path -> (key, cells, info).)"""
    raw = imread_u(path)
    if raw is None:
        raise SystemExit("cannot read " + path)
    return extract_key(raw)


def extract_all(input_dir=None):
    """입력 폴더의 모든 이미지를 처리.
    EN: Process all images in the input folder.
    반환: (keys{이름:key}, raws{이름:원본}, metas{이름:meta})  (EN: Returns: (keys{name:key}, raws{name:original}, metas{name:meta}))"""
    keys, raws, metas = {}, {}, {}
    for name, path in list_images(input_dir):
        raw = imread_u(path)
        if raw is None:
            print("  [skip] 읽기 실패:", os.path.basename(path))  # EN: prints: "[skip] failed to read:"
            continue
        key, cells, info = extract_key(raw)
        keys[name], raws[name], metas[name] = key, raw, info["meta"]
        metas[name]["_img"], metas[name]["_cells"] = info["img"], cells
    return keys, raws, metas


# ===========================================================================
# 렌더링
# EN: Rendering
# ===========================================================================
def render_tricolor(key, cell=26):
    img = np.zeros((N * cell, N * cell, 3), np.uint8)
    fs = cell / 45.0
    for r in range(N):
        for c in range(N):
            v = int(key[r][c])
            cv2.rectangle(img, (c * cell, r * cell), ((c+1)*cell-1, (r+1)*cell-1), COLORS[v], -1)
            cv2.rectangle(img, (c * cell, r * cell), ((c+1)*cell-1, (r+1)*cell-1), (60, 60, 60), 1)
            tc = (255, 255, 255) if v == 2 else (40, 40, 40)
            (tw, tht), _ = cv2.getTextSize(str(v), cv2.FONT_HERSHEY_SIMPLEX, fs, 1)
            cv2.putText(img, str(v), (c*cell+(cell-tw)//2, r*cell+(cell+tht)//2),
                        cv2.FONT_HERSHEY_SIMPLEX, fs, tc, 1, cv2.LINE_AA)
    return img


def render_spots(img, cells, key, side):
    ov = img.copy(); cw = side / N
    for r in range(N):
        cv2.line(ov, (0, int((r + .5) * cw)), (side, int((r + .5) * cw)), (40, 40, 235), 2)
    for r in range(N):
        for c in range(N):
            s = cells[r][c]
            cv2.circle(ov, (int(s["cx"]), int(s["cy"])), max(4, int(s["w"] / 2)),
                       COLORS[int(key[r][c])], 3)
    return ov


# ===========================================================================
# CLI : 입력 폴더의 모든 이미지 → 키/이미지/메타 저장
# EN: CLI: all images in the input folder -> save key/image/meta
# ===========================================================================
def save_outputs(name, key, cells, img, outdir=None):
    """한 이미지의 산출물(키 CSV·삼색키·스팟오버레이) 저장.  (EN: Save the outputs of one image (key CSV, tricolor key, spot overlay).)"""
    outdir = outdir or OUTDIR
    os.makedirs(outdir, exist_ok=True)
    np.savetxt(os.path.join(outdir, name + "_key.csv"), key, fmt="%d", delimiter=",")
    imwrite_u(os.path.join(outdir, name + "_tricolor.png"), render_tricolor(key))
    imwrite_u(os.path.join(outdir, name + "_spots.png"),
              render_spots(img, cells, key, img.shape[1]))


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    imgs = list_images()
    if not imgs:
        print("이미지가 없습니다. 다음 폴더에 이미지를 넣어주세요:\n  " + INPUT_DIR)  # EN: prints: "No images found. Please put images in this folder:"
        return
    print("입력 폴더: %s  (이미지 %d장)" % (os.path.dirname(imgs[0][1]), len(imgs)))  # EN: prints: "Input folder: %s  (%d images)"
    allmeta = {}
    for name, path in imgs:
        key, cells, info = extract_from_file(path)
        save_outputs(name, key, cells, info["img"])
        allmeta[name] = info["meta"]
        print("  %-14s %s" % (name, json.dumps(info["meta"], ensure_ascii=False)))
    with open(os.path.join(OUTDIR, "extract_meta.json"), "w") as f:
        json.dump(allmeta, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
