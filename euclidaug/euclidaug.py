#############################################################################
# Purpose:
# To significantly augment availability of annotated data,
# specially 2D shapes for object recognition.
# Targeted for  Yolov2 and Yolov3. Can be modified trivially for KITTI and others for Caffe.
#
# How to run:
# - Place all object png images in the folder 'objects' (should be named 0.png, 1.png, .. for each object class)
# - Place all background png images in the folder 'bg' (can be any name)
# - Update cfgWidth, cfgHeight, numClasses - in the script, to match the framework requirements
# - Invoke this script as "python <script> <object-folder-name> <bg folder name> <output train list name>"
# - output image files will be written to 'output_images' and 'output_labels'
# - output training list file will be written containing all image paths
# - Note: The labels are in Yolo format (centerx,centery, w,h)
#
# Prabindh Sundareson, prabindh@yahoo.com
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
numClasses = 3
numTargetImagesPerClass = 10
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

def write2Kitti(imageSize, boxCoords, writeObj, classLabel): # writing type/class and bbox coordinates and ignoring others           
    writeObj.write('%s' % classLabel)      
    writeObj.write(' 0.0 0 0.0 ')           
    writeObj.write('%.2f %.2f %.2f %.2f' % (boxCoords[0], boxCoords[1], boxCoords[2], boxCoords[3]))
    writeObj.write(' 0.0 0.0 0.0 0.0 0.0 0.0 0.0')
    writeObj.write('\n')     

def printHelp():
    return "Usage: name <input objects dir fullpath> <input backgrounds dir fullpath> <output training file fullpath>"
    
    
def get_object_file_list2(imageDir):
    imageList = []
    count = 0
    perClassImageCount = 0
    maxPerClassImageCount = 0
    for id in range(0, numClasses):
        imagesPerClass = [] 
        perClassImageCount = 0
        imagesPerClass.extend(glob.glob(os.path.join(imageDir+"\\"+str(id), '*.png')) )
        imageList.append(imagesPerClass)
        perClassImageCount = len(imagesPerClass)
        if (perClassImageCount > maxPerClassImageCount):
            maxPerClassImageCount = perClassImageCount
        count = count + 1

    return imageList, count, maxPerClassImageCount
    
def get_object_file_list(imageDir):
    imageList = []

    for id in range(0, numClasses):
        imageList.extend(glob.glob(os.path.join(imageDir, str(id) + '.png')) )

    return imageList
        
def get_file_list(imageDir):
    imageList = []
    imageList.extend(glob.glob(os.path.join(imageDir, '*.png')) )
    return imageList
                
def generateOne(iterationId, imageArrayAllClasses, baseImgName, baseImgObj):
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
    scaledImageArray = []
    scales = [1.1, 1.3, 1.5, 1.7, 1.8]
       
    # imageArrayAllClasses[numClasses][imagesPerClass] - for all classes, Choose a random image in each class
    for classId in range(0, numClasses):
        perClassCount = len(imageArrayAllClasses[classId])
        selectedInClass = random.randrange(0, perClassCount)
        img = imageArrayAllClasses[classId][selectedInClass]

        deltaW = random.randrange(10, 20)
        deltaH = random.randrange(10, 20)
        scaleW = 1
        scaleH = 1
        if(True == doRandomScale):
            scaleW = scaleH = scales[random.randrange(0, 5)]           
        
        img = img.resize((int(img.size[0]*scaleW),int(img.size[1]*scaleH)), Image.BICUBIC)
        scaledImageArray.append(img)        
        packer.add_rect( img.size[0] + deltaW,  img.size[1] + deltaH, imageId)
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
            x+objectBoundary[0]+scaledImageArray[rid].size[0], 
            y+objectBoundary[1]+scaledImageArray[rid].size[1]]
        area2 = (area1[0], area1[1], area1[2], area1[3])
        # crop original for blend
        cropped = finalImage.crop(area2)
        alphas = [0.7, 0.73, 0.75, 0.78, 0.8]
        alpha = 0.8
        if(True == doRandomAlpha):
            alpha = alphas[random.randrange(0, 5)]    
        
        blended = Image.blend(cropped, scaledImageArray[rid], alpha)
        finalImage.paste(blended, area2)
        # Generate yolo notation
        write2Yolo([cfgWidth, cfgHeight], area1,writeObj, rid)
        # Generate kitti notation
        # write2Kitti([cfgWidth, cfgHeight], area1,writeObj, rid)

    return finalImage, writeObj

##############################################################
##############################################################
##############################################################
if __name__ == "__main__":

    baseImageArray = []
    format = 'RGBA'
    trainListObj = io.StringIO()
    
    if len(sys.argv) != 4:
        printHelp()
        sys.exit(printHelp())
    # create base folders
    imageDir = os.path.join(os.getcwd(), imageFolderName)
    labelDir = os.path.join(os.getcwd(), labelFolderName)  
    trainFileName = sys.argv[3]
    
    if not os.path.isdir(imageDir):
        os.mkdir(imageDir)
    if not os.path.isdir(labelDir):
        os.mkdir(labelDir)
        
    #get ImageName[classCount][ImagesPerClass]
    perClassImageNamesArray, imageCount, MAX_IMAGES_PER_CLASS = get_object_file_list2(sys.argv[1])
    if imageCount == 0:
        print( 'Error: No image files found in the specified dir [' + sys.argv[1] + ']')
        sys.exit(printHelp())
        
    
    objectImageArrayAllClasses = []      #array[numClasses][imagesPerClass]    
    for classId in range(0, numClasses):
        for classImageName in perClassImageNamesArray[classId]:
            try:
                img = Image.open(classImageName).convert(format)
            except:
                print("Error: Cannot open image " + classImageName)
                sys.exit(printHelp())
            objectImageArrayAllClasses.append([])
            objectImageArrayAllClasses[classId].append(img)
        
    print("Info: Added [" + str(len(objectImageArrayAllClasses)) + "] object images, Max obj/class of [" + str(MAX_IMAGES_PER_CLASS) + "]")
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
            genImage, genText = generateOne(runId, objectImageArrayAllClasses, baseImageFileNames[bgId], baseImageArray[bgId])
            #genImage.show()
            genImageName = imageDir + '\\' + bgFileName+ "_" + str(bgId)+ "_" + str(runId) + ".png"
            genImage.save(genImageName, "png")            
            with open(labelDir + "\\" + bgFileName+ "_" + str(bgId) + "_" + str(runId) + ".txt", 'w') as f:
                f.write(genText.getvalue())
            trainListObj.write('%s\n' % genImageName)
            print('.', end='', flush=True)
    with open(trainFileName, "w") as f:
        f.write(trainListObj.getvalue())
    timeEnd = time.process_time() - timeStart
    print("")    
    print("Info: Completed @ " + str(timeEnd - timeStart) + " (sec)" )
