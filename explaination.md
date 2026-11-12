## Physical Unclonable Function (PUF)
*In the project, the image contan many small circular or spot like structures, program analyzes these patterns and converts them into numerical keys.*
<img width="1000" height="435" alt="image" src="https://github.com/user-attachments/assets/485271bb-98c2-472c-b1e8-12d74addb596" />

### How the complete system works
*Four original sample images*
           * :arrow_down: *
# Image preprocessing
*Find circular area → crop →resize → remove noise →smooth puf_extract.py*
          * :arrow_down: *
### Detect microscopic spots
*Enhance dark spots → threshold → filter → measure spot sizes → puf_extract.py*
           * :arrow_down:*
### Generate a ternary key
*20*20 cells → select one representative spot pre cell → assign 0, 1, or 2 → put_extract.py*
           * :arrow_down:*
### Evaluate generated keys
*Graph . heatmaps . population charts . Hamming distance distributions → puf_plots.py*
          
# run_all.py *coordinates the entire pipeline.*
