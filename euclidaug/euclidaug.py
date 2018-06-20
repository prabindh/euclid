#############################################################################
# Purpose:
# To significantly augment availability of annotated data,
# specially 2D shapes for object recognition.
#
# How to run:
# - Place all object png images in the folder 'objects' (should be named 0.png, 1.png, .. for each object class)
# - Place all background png images in the folder 'bg' (can be any name)
# - Update cfgWidth, cfgHeight, numClasses - in the script, to match the framework
# - Invoke this script as "python <script> <object-folder-name> <bg folder name>"
# - output image files will be written to 'output-images' and 'output-labels'
# - Note: The labels are in Yolo format
#############################################################################

from PIL import Image
import glob
import random
from rectpack import newPacker
import sys, os

################## USER CONFIGURATION ########################
# Target framework image size for annotated data
cfgWidth = 416
cfgHeight = 416
numClasses = 26
numRuns = 1000
##############################################################
##################### DO NOT CHANGE ##########################
##############################################################
 
class ObjProps():
    def __init__(self, obj, prop1, prop2):
        self.obj = obj
        self.prop1 = prop1
        self.prop2 = prop2

        
###############################
def convert2Yolo(imageSize, boxCoords):
    invWidth = 1./imageSize[0]
    invHeight = 1./imageSize[1]
    x = invWidth * (boxCoords[0] + boxCoords[2])/2.0
    y = invHeight * (boxCoords[1] + boxCoords[3])/2.0
    boxWidth = invWidth * (boxCoords[2] - boxCoords[0])
    boxHeight = invHeight * (boxCoords[3] - boxCoords[1])
    return (x,y,boxWidth,boxHeight)

def write2Yolo(imageSize, boxCoords, labelfilename, classLabel):
    with open(labelfilename, 'a') as f:
        ##class1 center_box_x_ratio center_box_y_ratio width_ratio height_ratio            
        cx, cy, bw, bh = convert2Yolo(
                    imageSize, 
                    boxCoords
                    );
        f.write('%s' % classLabel)               
        f.write(' %.7f %.7f %.7f %.7f' % (cx, cy, bw, bh))                 
        f.write('\n')
        #tkMessageBox.showinfo("Save Info", message = self.classLabelList[labelCnt])
     
def printHelp():
    return "Usage: name <objects full path> <background full path>"
    
def get_object_file_list(imageDir):
    imageList = []

    for id in range(0, numClasses-1):
        imageList.extend(glob.glob(os.path.join(imageDir, str(id) + '.png')) )

    if len(imageList) == 0:
        print( 'Error: No image files found in the specified dir [' + imageDir + ']')
    return imageList
        
def get_file_list(imageDir):
    imageList = []

    for id in range(0, numClasses-1):
        imageList.extend(glob.glob(os.path.join(imageDir, '*.png')) )

    if len(imageList) == 0:
        print( 'Error: No image files found in the specified dir [' + imageDir + ']')
    return imageList
                
def generateOne(iterationId):
    imageId = 0
    imageArray = []
    deltaW = 0
    deltaH = 0
    objectBoundary = [5,5]
       
    packer = newPacker(rotation=False)
    format = 'RGBA'
    #get object file names
    object_file_names = get_object_file_list(sys.argv[1])
    #get background file names
    background_file_names = get_file_list(sys.argv[2])
    #create a list of PIL Image objects
    images = []
    for x in object_file_names:
        img = Image.open(x).convert(format)
        imageArray.append(img)
        deltaW = random.randrange(5, 32)
        deltaH = random.randrange(5, 32)
        packer.add_rect(img.size[0] + deltaW, img.size[1] + deltaH, imageId)
        imageId = imageId + 1
    print("Info: Added [" + str(imageId) + "] objects")

    # Add the bins where the rectangles will be placed
    #cfgWidth = cfgWidth - objectBoundary[0]
    #cfgHeight = cfgHeight - objectBoundary[1]
    for b in [(cfgWidth, cfgHeight)]:
        packer.add_bin(*b)

    # Start packing
    packer.pack()
    # Open the target background image
    finalImage = Image.open(background_file_names[0]).convert(format)
    all_rects = packer.rect_list()
    for rect in all_rects:
        b, x, y, w, h, rid = rect
        # left, top, right, bottom       
        area1 = [
            x+objectBoundary[0],
            y+objectBoundary[1],
            x+objectBoundary[0]+imageArray[rid].size[0], 
            y+objectBoundary[1]+imageArray[rid].size[1]]
        area2 = (area1[0], area1[1], area1[2], area1[3])
        # crop original for blend
        cropped = finalImage.crop(area2)
        blended = Image.blend(cropped, imageArray[rid], 0.8)
        finalImage.paste(blended, area2)
        # Generate yolo notation
        write2Yolo([cfgWidth, cfgHeight], area1,background_file_names[0]+".output.txt", rid)

    #finalImage.show()
    finalImage.save(background_file_names[0]+".output" + str(iterationId) + ".png", "png")                
                
if __name__ == "__main__":
    if len(sys.argv) != 3:
        printHelp()
        sys.exit(printHelp())
    for id in range(0, numRuns-1):
        generateOne(id)