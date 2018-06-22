#############################################################################
# Purpose:
# To significantly augment availability of annotated data,
# specially 2D shapes for object recognition.
# Targeted for  Yolov2
#
# How to run:
# - Place all object png images in the folder 'objects' (should be named 0.png, 1.png, .. for each object class)
# - Place all background png images in the folder 'bg' (can be any name)
# - Update cfgWidth, cfgHeight, numClasses - in the script, to match the framework requirements
# - Invoke this script as "python <script> <object-folder-name> <bg folder name>"
# - output image files will be written to 'output_images' and 'output_labels'
# - Note: The labels are in Yolo format
#############################################################################

from PIL import Image
import glob
import random
from rectpack import newPacker
import sys, os
import io
import ntpath
import time

################## USER CONFIGURATION ########################
# Target framework image size for annotated data
cfgWidth = 416
cfgHeight = 416
numClasses = 26
numTargetImagesPerClass = 50
imageFolderName = 'out_images'
labelFolderName = 'out_labels'
##############################################################
##################### EUCLIDAUG ##############################
##############################################################
def convert2Yolo(imageSize, boxCoords):
    invWidth = 1./imageSize[0]
    invHeight = 1./imageSize[1]
    x = invWidth * (boxCoords[0] + boxCoords[2])/2.0
    y = invHeight * (boxCoords[1] + boxCoords[3])/2.0
    boxWidth = invWidth * (boxCoords[2] - boxCoords[0])
    boxHeight = invHeight * (boxCoords[3] - boxCoords[1])
    return (x,y,boxWidth,boxHeight)

def write2Yolo(imageSize, boxCoords, writeObj, classLabel):
    ##class1 center_box_x_ratio center_box_y_ratio width_ratio height_ratio            
    cx, cy, bw, bh = convert2Yolo(
                imageSize, 
                boxCoords
                );
    writeObj.write('%s' % classLabel)               
    writeObj.write(' %.7f %.7f %.7f %.7f' % (cx, cy, bw, bh))
    writeObj.write('\n')
     
def printHelp():
    return "Usage: name <objects full path> <background full path>"
    
def get_object_file_list(imageDir):
    imageList = []

    for id in range(0, numClasses):
        imageList.extend(glob.glob(os.path.join(imageDir, str(id) + '.png')) )

    return imageList
        
def get_file_list(imageDir):
    imageList = []
    imageList.extend(glob.glob(os.path.join(imageDir, '*.png')) )
    return imageList
                
def generateOne(iterationId, imageArray, baseImgName, baseImgObj):
    imageId = 0
    deltaW = 0
    deltaH = 0
    writeObj = io.StringIO()
    objectBoundary = [5,5]
    doRandomScale = True
    doRandomAlpha = True
       
    packer = newPacker(rotation=False)
    format = 'RGBA'
    #create a list of PIL Image objects
    images = []
    scales = [1.1, 1.3, 1.5, 1.7, 1.8]
    for img in imageArray:
        deltaW = random.randrange(5, 20)
        deltaH = random.randrange(5, 20)
        scaleW = 1
        scaleH = 1
        if(True == doRandomScale):
            scaleW = scales[random.randrange(0, 5)]
        if(True == doRandomScale):
            scaleH = scales[random.randrange(0, 5)]
        
        packer.add_rect(int(img.size[0]*scaleW) + deltaW, int(img.size[1]*scaleH) + deltaH, imageId)
        imageId = imageId + 1

    # Add the bins where the rectangles will be placed
    for b in [(cfgWidth, cfgHeight)]:
        packer.add_bin(*b)

    # Start packing
    packer.pack()
    # Open the target background image
    finalImage = Image.open(baseImgName).convert(format)
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
        alphas = [0.7, 0.75, 0.8, 0.85, 0.9]
        alpha = 0.8
        if(True == doRandomScale):
            alpha = alphas[random.randrange(0, 5)]    
        
        blended = Image.blend(cropped, imageArray[rid], alpha)
        finalImage.paste(blended, area2)
        # Generate yolo notation
        write2Yolo([cfgWidth, cfgHeight], area1,writeObj, rid)

    return finalImage, writeObj

##############################################################
##############################################################
##############################################################
if __name__ == "__main__":
    objectImageArray = []
    baseImageArray = []
    format = 'RGBA'
    
    if len(sys.argv) != 3:
        printHelp()
        sys.exit(printHelp())
    # create base folders
    imageDir = os.path.join(os.getcwd(), imageFolderName)
    labelDir = os.path.join(os.getcwd(), labelFolderName)    
    if not os.path.isdir(imageDir):
        os.mkdir(imageDir)
    if not os.path.isdir(labelDir):
        os.mkdir(labelDir)
        
    #get object file names
    object_file_names = get_object_file_list(sys.argv[1])
    if len(object_file_names) == 0:
        print( 'Error: No image files found in the specified dir [' + sys.argv[1] + ']')
        sys.exit(printHelp())
    for name in object_file_names:
        try:
            img = Image.open(name).convert(format)
            objectImageArray.append(img)
        except:
            print("Error: Cannot open image " + name)
            sys.exit(printHelp())
    print("Info: Added [" + str(len(objectImageArray)) + "] object images")          
    #get background file names
    baseImageFileNames = get_file_list(sys.argv[2])   
    if len(baseImageFileNames) == 0:
        print( 'Error: No image files found in the specified dir [' + sys.argv[2] + ']')
        sys.exit(printHelp())      
    for name in baseImageFileNames:
        img = Image.open(name).convert(format)
        baseImageArray.append(img)        
    print("Info: Added [" + str(len(baseImageFileNames)) + "] base images")    
    
    # Loop across background images, then runs
    adjnumTargetImagesPerClass = int ((numTargetImagesPerClass /len(baseImageFileNames) ) + 1) 
    timeStart = time.process_time()
    print("Info: Beginning [" + str(adjnumTargetImagesPerClass*len(baseImageFileNames)) + "] images @ " + str(timeStart) + " (sec)" )
    for bgId in range(0, len(baseImageFileNames)):
        bgFileNameFull = ntpath.basename(baseImageFileNames[bgId])   
        bgFileName, bgFileNameExt = os.path.splitext(bgFileNameFull)
        for runId in range(0, adjnumTargetImagesPerClass):
            genImage, genText = generateOne(runId, objectImageArray, baseImageFileNames[bgId], baseImageArray[bgId])
            #genImage.show()
            genImage.save(imageDir + '\\' + bgFileName+ "_" + str(bgId)+ "_" + str(runId) + ".png", "png")            
            with open(labelDir + "\\" + bgFileName+ "_" + str(bgId) + "_" + str(runId) + ".txt", 'w') as f:
                f.write(genText.getvalue())
            print('.', end='', flush=True)
    timeEnd = time.process_time() - timeStart            
    print("")    
    print("Info: Completed @ " + str(timeEnd - timeStart) + " (sec)" )