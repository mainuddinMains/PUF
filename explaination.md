## Physical Unclonable Function (PUF)
*In the project, the image contan many small circular or spot like structures, program analyzes these patterns and converts them into numerical keys.*
<img width="1000" height="435" alt="image" src="https://github.com/user-attachments/assets/485271bb-98c2-472c-b1e8-12d74addb596" />

### How the complete system works

*Four original sample images*
⬇️
### Image preprocessing
*Find circular area → crop → resize → remove noise → smooth → puf_extract.py*
⬇️
### Detect microscopic spots
*Enhance dark spots → threshold → filter → measure spot sizes → puf_extract.py*
⬇️
### Generate a ternary key
*20×20 cells → select one representative spot per cell → assign 0, 1, or 2 → puf_extract.py*
⬇️
### Evaluate generated keys
*Graphs · heatmaps · population charts · Hamming distance distributions → puf_plots.py*
⬆️ 
# run_all.py *coordinates the entire pipeline.*

# Input Images
<img width="279" height="329" alt="Sample1" src="https://github.com/user-attachments/assets/6ae0f765-48a2-46b7-8f9a-9c42f169219c" />.<img width="279" height="332" alt="sample2" src="https://github.com/user-attachments/assets/00c6693d-fd0d-459d-988c-04e0eb43bf1a" />.<img width="282" height="330" alt="sample3" src="https://github.com/user-attachments/assets/f8508571-8bbd-4521-b0f4-ec0c22173b99" />.<img width="275" height="329" alt="sample4" src="https://github.com/user-attachments/assets/7c5f00a2-5e79-45f9-aaea-a508c66f7a77" />


puf_extract.py     Processes microscope images and creates PUF keys

[puf_extract.py](puf_extract.py)   Processes microscope images and creates PUF keysn\
[puf_metrics.py](puf_metrics.py).  Calculates performance and statistical metrics
[puf_plots.py](puf_plots.py)   Generates all the experimental graphs
[run_all.py](run_all.py).   Runs the entire project in sequence
