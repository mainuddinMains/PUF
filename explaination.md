## Physical Unclonable Function (PUF)
*What this project produces*

The pipeline [run_all.py](run_all.py) takes 4 microscope of spot patterns (Sample1 to sample4) and turns each one into a 20*20 ternary key: 400 cells, each holding the digit 0, 1, 2. it then measures how good those keys are as PUF fingerprints.
Everything is saved in [ PUF_최종결과]( PUF_최종결과).

*In the project, the image contan many small circular or spot like structures, program analyzes these patterns and converts them into numerical keys.*
<img width="1000" height="435" alt="image" src="https://github.com/user-attachments/assets/485271bb-98c2-472c-b1e8-12d74addb596" />

### How the complete system works

*Four original sample images*
⬇️
### Image preprocessing
*Find circular area → crop → resize → remove noise → smooth . puf_extract.py*
⬇️
### Detect microscopic spots
*Enhance dark spots → threshold → filter → measure spot sizes . puf_extract.py*
⬇️
### Generate a ternary key
*20×20 cells → select one representative spot per cell → assign 0, 1, or 2 . puf_extract.py*
⬇️
### Evaluate generated keys
*Graphs · heatmaps · population charts · Hamming distance distributions . puf_plots.py*
 
# run_all.py *coordinates the entire pipeline.*

# Input Images
<img width="279" height="329" alt="Sample1" src="https://github.com/user-attachments/assets/6ae0f765-48a2-46b7-8f9a-9c42f169219c" />.<img width="279" height="332" alt="sample2" src="https://github.com/user-attachments/assets/00c6693d-fd0d-459d-988c-04e0eb43bf1a" />.<img width="282" height="330" alt="sample3" src="https://github.com/user-attachments/assets/f8508571-8bbd-4521-b0f4-ec0c22173b99" />.<img width="275" height="329" alt="sample4" src="https://github.com/user-attachments/assets/7c5f00a2-5e79-45f9-aaea-a508c66f7a77" />


# Code files

[puf_extract.py](puf_extract.py)   Processes microscope images and creates PUF keysn\
[puf_metrics.py](puf_metrics.py).  Calculates performance and statistical metricsn\
[puf_plots.py](puf_plots.py)   Generates all the experimental graphsn\
[run_all.py](run_all.py).   Runs the entire project in sequence

[metrics.json](PUF_최종결과/metrics.json).  store numerical experimental resultsn\
[Sample1_key.csv](PUF_최종결과/Sample1_key.csv).  Numerical 20×20 PUF keysn\
[Sample1_spots.png](PUF_최종결과/Sample1_spots.png).  Images showing selected detected spotsn\
[Sample1_tricolor.png](PUF_최종결과/Sample1_tricolor.png).   Color-coded digital keys

# Define the image-processing in 
[puf_extract_english.py](puf_extract_english.py)
```text
N = 20                        Divides the image into 20 rows and 20 columns
CANON_SIDE = 3024.            Resizes the cropped image to 3024×3024 pixels
DENOISE_H = 7.                Sets the noise-removal strength
SMOOTH_SIG = 5.               Controls Gaussian smoothing
BG_SIG = 80.                  Estimates broad background illumination
FLOOR = 14.                   Minimum contrast needed for an initial spot candidate
MIN_AREA = 120                Discards detected components smaller than 120 processed-image pixels
TERCILE = (33.3333, 66.6667). Divides the spot-size measurements into three categories
```
<img width="992" height="382" alt="image" src="https://github.com/user-attachments/assets/796bd7d1-2acd-4f78-9f04-a00e360f191f" />


# How Output gets saved 
* after generating the key, the program saves three files per input
```text
Sample1_key.csv. store the 400 numeric values.
Sample1_tricolor.png  displys these values with colors.
Sample1_spots.png shows the selected spot locations and sizes on the processed image.
```
* Here is the output sample 
  
  <img width="684" height="366" alt="image" src="https://github.com/user-attachments/assets/f4c72f96-5e0d-4c12-b7ea-e1648d7f4b62" />

* The key might be change based on the code running in different machine/computer. The code has no random steps. Same image, different computer or OpenCV version it can change a little

**Every line in a text file ends with an invisible "new line" marker, and Windows and Linux write it differently:**
```text
 Windows ends each line with two characters, \r\n (CRLF).
 Linux ends each line with one character, \n (LF).
```
The committed **CSVs** were made on Windows. Your run on Linux rewrote them with Linux endings, so every line counts as different to git even though the numbers are exactly the same.

The data is unaffected, and Excel, Python and pandas read both styles the same way.
-----
# Intra-HD (simulated retakes)
*There are no real retake photos, so the code makes fake retakes by editing the same original photo.*

[puf_metrics.py](puf_metrics.py) `perturb()` makes one altered copy of the original photo:
```text
brightness ±3%      lighter or darker
noise               adds grain
blur (50% chance)   imitates bad focus
rotation ±1°        small tilt
shift ±2 px         small move
```
`intra_hd()` makes **25 copies per sample**, extracts a key from each one and compares it to the original key.
The result is the fraction of the 400 cells that changed (0 = same key, 0.667 = completely different key).

**The copies are made in puf_metrics.py:71-91.**

*perturb(), lines 71–82, makes one altered copy*
```text
Line 75:   makes it brighter or darker by up to ±3%.
Line 76:   adds grain (noise).
Lines 78–79: blurs it half the time, to imitate bad focus.
Line 80:   tilts it by up to ±1°.
Line 81:   shifts it by up to ±2 pixels.
```
 <img width="621" height="226" alt="image" src="https://github.com/user-attachments/assets/98ff566e-6e51-4689-843e-080bbcab0788" />

```text
intra_hd(), lines 85–91, makes 25 copies per sample (R=25), 
extracts a key from each and compares it to the original key with fractional_hd.
```
 <img width="644" height="139" alt="image" src="https://github.com/user-attachments/assets/ace83c38-252a-421f-8e9b-76b52aeba1e8" />

* Separation (inter − intra) shows how easy it is to tell tags apart.*
```text
Inter-HD = 0.66 is how different two different tags are.
Intra-HD = 0.28 is how different the same tag is from its retakes.
Separation = 0.66 − 0.28 = 0.38.
```
* The random numbers use a fixed seed `np.random.default_rng(42)`, so the same computer gives the same 25 copies every time. Changing 42 to another number gives a different set of copies, and only intra-HD changes a little.

 <img width="287" height="163" alt="image" src="https://github.com/user-attachments/assets/50effd2e-6d50-4031-accc-0ce7967c8c89" />


### The 25 copies are made twice (issue)
1. [run_all.py](run_all.py) → `M.full_report(...)` makes 25 copies → numbers go into **metrics.json**
   <img width="683" height="105" alt="image" src="https://github.com/user-attachments/assets/5cb125a5-7ad4-4e0f-ab71-e90c7a72cf1b" />

2. [run_all.py](run_all.py) → `V.plot_all(...)` → calls `M.intra_hd(...)` in [puf_plots.py](puf_plots.py) → makes **25 new copies** → numbers go into the **figures** (FIG_HD_bars.png, FIG_HD_matrix.png)

   <img width="605" height="108" alt="image" src="https://github.com/user-attachments/assets/c73c13e3-f48c-463d-a907-ec1267705295" />


The seed is set only once, so the second round gets different random numbers. That's why the intra-HD in the figures is slightly different from metrics.json.

-----

**The numbers changed because the code makes random copies, and this run produced slightly different ones.**

The code fixes the randomness with a seed (42), so the same computer setup should give the same copies every time. n\
The old results were made on a different computer, probably Windows, and possibly with different versions of the Python libraries (numpy, OpenCV). Different versions can produce slightly different random grain or slightly different tilted images.

Slightly different copies give slightly different keys, so the intra-HD numbers shift a little.
*code and photos* didn't change. Only the computer setup did, and the differences are tiny, at most about 0.01.

-----
**Each fake copy is read by the same key-making code, and small edits to the photo can flip some cells.**

Each cell gets 0, 1 or 2 depending on the size of its spot (small, medium or large).

Some spots are close to the cut-off between two sizes. For example, a spot right at the edge between "small" and "medium".n\
A tiny edit (a bit of blur, a slight tilt) can push that spot just over the cut-off, so the cell flips, say from 0 to 1.n\
Different copies get different random edits, so different cells flip:
```text
copy 1 might flip 110 cells, which gives 0.275
copy 2 might flip 125 cells, which gives 0.31
...
intra-HD is the average over all 25 copies.
```
If you change the seed or the computer setup, you get a different set of 25 copies. Slightly different cells flip, so the average comes out a little different (0.2784 vs 0.2908, for example).


```text
why it gets generating the numbers?
check the code if it generate the random number?
more understanding of the code.
```



























