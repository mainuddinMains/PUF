# Random fractal-enabled physical unclonable functions with dynamic AI authentication
 https://www.nature.com/articles/s41467-023-37588-5

Code_GiyHub  
https://github.com/Seven-year-promise/PUF_authentication
   
 * A PUF (Physical Unclonable Function) is a physical pattern, here a random fractal, that can't be copied. Each one acts as a unique fingerprint. The code photographs these patterns and checks whether a new photo matches a registered PUF, and which one. It works in two stages

In the code base author did not add the .pth file so to run the code or get the output it require training the from beginning  

To run this code I needed to add/update these 

# Changes I made before starting  
Image paths: the training list pointed at the authors' computer (/srv/yanke/...). I added a small helper, local_path in config.py, and Dataloader.py now uses it to load images from your data/ folder.  
Separate output folder: I added a --save_dir option to train_class_only_init.py, so your results go to results/class_init_mine/ and the authors' saved files stay untouched.  
Faster image loading: I added a --num_workers option so images are prepared on 12 CPU cores instead of 1.  
Python environment: I created a Python 3.9 environment in .venv/ with PyTorch 1.12.1 for GPU. To make it, I installed a tool called uv into ~/.local/share/uv-tool/.  
# What to expect
About 8–10 hours for 2500 epochs, at roughly 10 seconds per epoch. I stopped at 2500 because the authors reached about 99% accuracy by then.
A .pth file is saved every 100 epochs in results/class_init_mine/.  
Accuracy will sit near 0% for the first couple of hundred epochs. That's normal: the authors' log shows only about 9% at epoch 239, 55% at epoch 489, and 99% around epoch 2000–2500.  
It keeps running even if you close VS Code. It stops if the computer shuts down, sleeps or restarts, so keep it powered on.   
