#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
puf_extract.py  —  [1] Image → PUF key extraction  (Method 4: fixed 20x20 grid + size-based ternary)

Pipeline
  [A] Preprocessing     : crop inscribed square of the circular field of view → resize → denoise → Gaussian smoothing
  [B] Spot enhancement  : large-blur background estimate → background subtraction (= contrast image)
  [C] Spot detection    : binarize → closing/opening → connected components (spot = one blob) → shape filter → equivalent diameter W
  [D] Key generation    : assign to 20x20 grid (by center, one per cell) → size terciles (33/67%) → 0/1/2

★ Usage: just put images in the  input img/  folder next to this script and they are all processed automatically.
   (supports png/jpg/jpeg/bmp/tif/webp · no limit on number of images · any file name)
   Results are saved to  PUF_최종결과/  (final PUF results) in the same folder.

Public functions
  list_images(dir=None)        -> [(name, path), ...]     # auto-scan the input folder
  extract_key(raw_bgr)         -> (key, cells, info)     # one numpy image → key
  extract_from_file(path)      -> (key, cells, info)     # file path → key
  extract_all(dir=None)        -> (keys, raws, metas)    # batch-process the whole folder
  render_tricolor(key)         -> BGR image
  render_spots(img,cells,key)  -> BGR overlay (scan lines + circles)

CLI:  py puf_extract.py            # extract from the whole input folder → save to PUF_최종결과/
Deps: numpy, opencv-python
"""
import os, csv, json
import numpy as np
import cv2

# ---------------------------------------------------------------------------
# Settings (all parameters in one place)
# ---------------------------------------------------------------------------
N          = 20            # grid size (fixed 20x20 map)
CANON_SIDE = 3024          # resize size of the cropped square
DENOISE_H  = 7             # [A] fastNlMeans strength
SMOOTH_SIG = 5             # [A] Gaussian smoothing σ
BG_SIG     = 80            # [B] background estimation blur σ
FLOOR      = 14            # [C] minimum local contrast for a spot
CLOSE_K    = 11            # [C] closing kernel (fills holes in large spots)
OPEN_K     = 3             # [C] opening kernel (removes speck noise)
MIN_AREA   = 120           # [C] minimum spot area (px)
ASPECT_MIN = 0.45          # [C] aspect ratio lower bound (excludes elongated bumps)
EXTENT_MIN = 0.45          # [C] fill ratio lower bound (excludes irregular bumps)
TERCILE    = (33.3333, 66.6667)   # [D] size terciles (%)

COLORS = {0: (170, 220, 150), 1: (40, 210, 240), 2: (130, 60, 50)}  # BGR mint/yellow/navy

HERE  = os.path.dirname(os.path.abspath(__file__))
# ---------------------------------------------------------------------------
# Input/output folders: just put images in INPUT_DIR and they are all processed automatically
# ---------------------------------------------------------------------------
EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp")

# ★ Folder for images: input img/ next to this script (if empty, the candidates below are checked in order)
INPUT_DIR = os.path.join(HERE, "input img")
INPUT_CANDIDATES = [
    INPUT_DIR,                                                  # script/input img/  (default)
    os.path.join(HERE, "입력이미지"),
    os.path.normpath(os.path.join(HERE, "..", "input img")),    # parent/input img/
    os.path.normpath(os.path.join(HERE, "..", "..", "input img")),
    os.path.normpath(os.path.join(HERE, "..", "..", "..", "input img")),
]

# Output folder: PUF_최종결과/ next to this script
OUTDIR = os.path.join(HERE, "PUF_최종결과")


def imwrite_u(path, img):
    """Save with Korean/non-ASCII path support (cv2.imwrite fails on non-ASCII paths on Windows)."""
    ok, buf = cv2.imencode(os.path.splitext(path)[1], img)
    if ok:
        buf.tofile(path)


def imread_u(path):
    """Read with Korean/non-ASCII path support."""
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def _scan(d):
    """Sorted list of image files in a folder."""
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d) if f.lower().endswith(EXTS))


def list_images(input_dir=None):
    """Auto-discover images. Returns: [(name, path), ...]  (name = file name without extension)

    If input_dir is given, only that folder is used;
    otherwise INPUT_CANDIDATES are checked in order and the first folder that contains images is used.
    """
    if input_dir:
        return [(os.path.splitext(f)[0], os.path.join(input_dir, f))
                for f in _scan(input_dir)]
    for d in INPUT_CANDIDATES:
        files = _scan(d)
        if files:
            return [(os.path.splitext(f)[0], os.path.join(d, f)) for f in files]
    os.makedirs(INPUT_DIR, exist_ok=True)                        # create the folder if none found
    return []


# ===========================================================================
# [A] Preprocessing  +  [B] Spot enhancement
# ===========================================================================
def preprocess(raw):
    """Returns: (square BGR, field_mask, contrast). [A] crop/smoothing + [B] background removal."""
    gray0 = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(cv2.GaussianBlur(gray0, (5, 5), 0), 0, 255,
                          cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    (cx, cy), r = cv2.minEnclosingCircle(max(cnts, key=cv2.contourArea))
    half = int(r * 0.96 / (2 ** 0.5))                       # half-side of the inscribed square
    x0, y0 = max(0, int(cx - half)), max(0, int(cy - half))
    x1, y1 = min(raw.shape[1], int(cx + half)), min(raw.shape[0], int(cy + half))
    img = cv2.resize(raw[y0:y1, x0:x1], (CANON_SIDE, CANON_SIDE), interpolation=cv2.INTER_CUBIC)
    img = cv2.fastNlMeansDenoisingColored(img, None, DENOISE_H, DENOISE_H, 7, 21)
    field_mask = np.full((CANON_SIDE, CANON_SIDE), 255, np.uint8)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sm = cv2.GaussianBlur(gray, (0, 0), SMOOTH_SIG)         # [A] smoothing
    bg = cv2.GaussianBlur(sm, (0, 0), BG_SIG)               # [B] illumination background
    contrast = np.clip(bg.astype(np.int16) - sm.astype(np.int16), 0, 255).astype(np.uint8)
    return img, field_mask, contrast


# ===========================================================================
# [C] Spot detection
# ===========================================================================
def detect_spots(contrast, field_mask):
    """Returns: (spot list [{cx,cy,area,w}], binary image). A large spot is one blob = 1 spot."""
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
                          w=2.0 * (area / np.pi) ** 0.5))    # equivalent diameter
    return spots, binar


# ===========================================================================
# [D] Key generation
# ===========================================================================
def build_key(spots, side):
    """Returns: (NxN key, cells, cell size, t1, t2). Places spots on the grid and ternarizes by size terciles."""
    cw = side / N
    cells = [[None] * N for _ in range(N)]
    for s in spots:
        r, c = min(N - 1, int(s["cy"] // cw)), min(N - 1, int(s["cx"] // cw))
        if cells[r][c] is None or s["area"] > cells[r][c]["area"]:
            cells[r][c] = s                                 # keep only the largest-area spot per cell
    W = np.zeros((N, N))
    for r in range(N):
        for c in range(N):
            if cells[r][c] is None:
                cells[r][c] = dict(w=0.0, area=0.0, cx=(c + .5) * cw, cy=(r + .5) * cw)
            W[r, c] = cells[r][c]["w"]
    t1, t2 = np.percentile(W, TERCILE)                      # size terciles
    key = np.zeros((N, N), int)
    key[W >= t1] = 1
    key[W >= t2] = 2
    return key, cells, cw, float(t1), float(t2)


# ===========================================================================
# Public entry points
# ===========================================================================
def extract_key(raw):
    """One numpy BGR image → (key, cells, meta)."""
    img, fm, contrast = preprocess(raw)
    spots, _ = detect_spots(contrast, fm)
    key, cells, cw, t1, t2 = build_key(spots, img.shape[0])
    meta = dict(n_spots=len(spots), size_thr=[round(t1, 1), round(t2, 1)],
                bit_pct={v: round(float((key == v).mean() * 100), 2) for v in (0, 1, 2)})
    return key, cells, dict(img=img, meta=meta, cells=cells)


def extract_from_file(path):
    """Image file path → (key, cells, info)."""
    raw = imread_u(path)
    if raw is None:
        raise SystemExit("cannot read " + path)
    return extract_key(raw)


def extract_all(input_dir=None):
    """Process all images in the input folder.
    Returns: (keys{name:key}, raws{name:original}, metas{name:meta})"""
    keys, raws, metas = {}, {}, {}
    for name, path in list_images(input_dir):
        raw = imread_u(path)
        if raw is None:
            print("  [skip] failed to read:", os.path.basename(path))
            continue
        key, cells, info = extract_key(raw)
        keys[name], raws[name], metas[name] = key, raw, info["meta"]
        metas[name]["_img"], metas[name]["_cells"] = info["img"], cells
    return keys, raws, metas


# ===========================================================================
# Rendering
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
# CLI: all images in the input folder → save keys/images/meta
# ===========================================================================
def save_outputs(name, key, cells, img, outdir=None):
    """Save outputs for one image (key CSV, tricolor key, spot overlay)."""
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
        print("No images found. Please put images in this folder:\n  " + INPUT_DIR)
        return
    print("Input folder: %s  (%d images)" % (os.path.dirname(imgs[0][1]), len(imgs)))
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
