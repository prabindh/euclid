# euclid labeller
Euclid object labeller for object detection training purposes based on Python. Tested on Linux, Windows, and Mac.

- Supports Kitti format
- Supports Yolo darknet format (Generates bounding boxes, as well as training list file)

Dynamic selection of format is now supported.

Optimised box selection using keyboard shortcuts.

# Typical object labelling workflow using Euclid:

Create a folder containing the images
 
- Ensure images are of uniform (not too big) shape using a command for resize like below. (Linux)

Resize all jpg images to 256x256, rename to sz-256-<original-name>.jpg

  `for file in *.jpg; do convert $file -resize 256x256 sz-256-$file; done`

- `$python euclid.py`

- Select the folder containing the images

- Euclid will show the first image in the folder.

- Select the class ID, and start labelling. Once done for this image, move to the next image, till all imagea are done.

- Euclid also generates a supplementary file "train.txt", containing the class ID and full path of training file. This can be used in YOLO format training.

# YOLO training and detection.

Refer below link for YOLO training and detection on Linux and Windows.

https://github.com/prabindh/darknet

# Dependencies

 Python 2.7
 `pip install pillow`
 `pip install image`
 Python 3
 Python 3 + Pillow on Ubuntu, do the below
 `sudo apt-get install python-imaging-tk`
 `sudo apt-get install python3-pil.imagetk`

# Converting to TensorFlow format
After labelling the images, the labels can be read and converted to TFRecord using Python scripts available in Tensorflow, using tf.train.Example and tf.train.Features. Note: Yolo and TF share the same bounding box notations (normalised).
