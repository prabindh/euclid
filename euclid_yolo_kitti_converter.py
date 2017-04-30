#-------------------------------------------------------------------------------
# Euclid - Labelling tool
# Create and label bounding boxes
#    prabindh@yahoo.com, 2016
#        Initial code taken from github.com/puzzledqs/BBox-Label-Tool
#        Significantly modified to add more image types, image folders, labelling saves, and format, and format selection
#        Currently supports 8 classes, and Kitti and YOLO(darknet) output formats
# Python 2.7
# pip install pillow
# pip install image
#
#-------------------------------------------------------------------------------


#-------------------------------------------------------------------------------
# The DetectNet/ Kitti Database format
# Taken from https://github.com/NVIDIA/DIGITS/blob/master/digits/extensions/data/objectDetection/README.md#label-format
# All values (numerical or strings) are separated via spaces,
# each row corresponds to one object. The 15 columns represent:
#
#Values    Name      Description
#----------------------------------------------------------------------------
#   1    type         Describes the type of object: 'Car', 'Van', 'Truck',
#                     'Pedestrian', 'Person_sitting', 'Cyclist', 'Tram',
#                     'Misc' or 'DontCare'
#   1    truncated    Float from 0 (non-truncated) to 1 (truncated), where
#                     truncated refers to the object leaving image boundaries
#   1    occluded     Integer (0,1,2,3) indicating occlusion state:
#                     0 = fully visible, 1 = partly occluded
#                     2 = largely occluded, 3 = unknown
#   1    alpha        Observation angle of object, ranging [-pi..pi]
#   4    bbox         2D bounding box of object in the image (0-based index):
#                     contains left, top, right, bottom pixel coordinates
#   3    dimensions   3D object dimensions: height, width, length (in meters)
#   3    location     3D object location x,y,z in camera coordinates (in meters)
#   1    rotation_y   Rotation ry around Y-axis in camera coordinates [-pi..pi]
#   1    score        Only for results: Float, indicating confidence in
#                     detection, needed for p/r curves, higher is better.
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# The YOLO format
# All values (numerical or strings) are separated via spaces,
# each row corresponds to one object. The 5 columns represent:
#
#Values    Name      Description
#----------------------------------------------------------------------------
#   1    Class ID     Describes the class number of object, as an integer number (0 based)
#   1    Center_X     Float from 0 to 1, X coordinate of b-box center, normalised to image width
#   1    Center_Y     Float from 0 to 1, Y coordinate of b-box center, normalised to image height
#   1    Bbox_Width   Float from 0 to 1, Width of b-box, normalised to image width
#   1    Bbox_Height  Float from 0 to 1, Height of b-box, normalised to image height
#-------------------------------------------------------------------------------
import sys
if sys.version_info[0] < 3:
    from Tkinter import *
    import tkMessageBox
    import tkFileDialog
else:
    from tkinter import *
    import messagebox as tkMessageBox
    import filedialog as tkFileDialog
from PIL import Image, ImageTk
import os
import glob
import random

    
# Usage
USAGE = " \
1. Select a Directory of labels, or Enter the path directly and click Load\n \
2. Click Convert. The labels will be converted and stored in current directory \n \
"


# Object Classes (No spaces in name)
CLASSES = ['Class0', 'Class1', 'Class2', 'Class3', 'Class4', 'Class5', 'Class6', 'Class7']

class EuclidConverter():

    def askDirectory(self):
      self.imageDir = tkFileDialog.askdirectory()
      self.entry.insert(0, self.imageDir)
      self.loadDir(self)
        

    def loadDir(self, dbg = False):
        self.imageDir = self.entry.get()
        self.parent.focus()
        if not os.path.isdir(self.imageDir):
            tkMessageBox.showerror("Folder error", message = "The specified directory doesn't exist!")
            return        
         #get label list
        labelFileTypes = ('*.txt') # the tuple of file types
        self.labelFileList = []
    
        # load labels
        for files in labelFileTypes:
            self.labelFileList.extend(glob.glob(os.path.join(self.imageDir, files.lower())) )
            if (False == self.is_windows):
                self.labelFileList.extend(glob.glob(os.path.join(self.imageDir, files)) )
            
        if len(self.labelFileList) == 0:
            tkMessageBox.showerror("Label files not found", message = "No labels (.txt) found in folder!")
            self.updateStatus( 'No label files found in the specified dir!')
            return
        # Change title
        self.parent.title("Euclid Label Converter (" + self.imageDir + ") " + str(len(self.labelFileList)) + " label files")
    def showHelp(self, event):
        tkMessageBox.showinfo("Help", USAGE)

        
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title("Euclid Labeller (Press F1 for Help)")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width = TRUE, height = TRUE)
        self.is_windows = hasattr(sys, 'getwindowsversion')


        # initialize global state
        self.imageDir = ''
        self.imageList= []
        self.outDir = ''
        self.cur = 0
        self.total = 0
        self.imagename = ''
        self.labelfilename = ''
        self.currLabelMode = 'YOLO' #'KITTI' #'YOLO' # Other modes TODO
        self.imagefilename = ''
        self.tkimg = None

        # initialize mouse state
        self.STATE = {}
        self.STATE['click'] = 0
        self.STATE['x'], self.STATE['y'] = 0, 0
        self.currentMouseX = 0;
        self.currentMouseY = 0;

        #colors
        self.redColor = self.blueColor = self.greenColor = 128
        
        # reference to bbox
        self.bboxIdList = []
        self.bboxId = None
        self.bboxList = []
        self.currClassLabel = 0
        self.classLabelList = []
        self.hl = None
        self.vl = None

        self.parent.bind("<F1>", self.showHelp)  # press <F1> to show help
        
        # ----------------- GUI stuff ---------------------

        # dir entry & load File control panel
        self.FileControlPanelFrame = Frame(self.frame)
        self.FileControlPanelFrame.grid(row = 0, column = 0, sticky = W)

        self.FileControlPanelLabel = Label(self.FileControlPanelFrame, text = '1. Select a directory (or) Enter input path, and click Load')
        self.FileControlPanelLabel.grid(row = 0, column = 0,  sticky = W+N)
        
        self.browserBtn = Button(self.FileControlPanelFrame, text = "Select Dir", command = self.askDirectory)
        self.browserBtn.grid(row = 1, column = 0, sticky = N)        
        
        self.entry = Entry(self.FileControlPanelFrame)
        self.entry.grid(row = 1, column = 1, sticky = N)
        self.ldBtn = Button(self.FileControlPanelFrame, text = "Load", command = self.loadDir)
        self.ldBtn.grid(row = 1, column = 2, sticky = N)
        
        self.ConvertBtn = Button(self.FileControlPanelFrame, text = "Convert", command = self.ConvertLabels)
        self.ConvertBtn.grid(row = 2, column = 0, sticky = N)
                          
        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row = 1, column = 0, columnspan = 2, sticky = W+N)
 
        self.progLabel = Label(self.ctrPanel, text = "Progress: [  0   /  0  ]")
        self.progLabel.pack(side = LEFT, padx = 5)

        # Status panel for image navigation
        self.statusPanel = Frame(self.frame)
        self.statusPanel.grid(row = 2, column = 0, columnspan = 3, sticky = W)
        self.statusText = StringVar()
        self.statusLabel = Label(self.statusPanel, textvariable = self.statusText)
        self.statusLabel.grid(row = 0, column = 0, sticky = W+E+N)
        self.updateStatus("Directory not selected.")

        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side = RIGHT)

        self.frame.columnconfigure(1, weight = 1)
        self.frame.rowconfigure(4, weight = 1)

    def GetBoundariesFromYoloFile(self, centerX, centerY, width, height, imageWidth, imageHeight):
        topLeftX = (int)(centerX*imageWidth - (width*imageWidth)/2)
        topLeftY = (int)(centerY*imageHeight - (height*imageHeight)/2)
        bottomRightX = (int)(centerX*imageWidth + (width*imageWidth)/2)
        bottomRightY = (int)(centerY*imageHeight + (height*imageHeight)/2)
        return topLeftX, topLeftY, bottomRightX, bottomRightY
    

    def convert2Yolo(self, image, boxCoords):
        
        invWidth = 1./image[0]
        invHeight = 1./image[1]
        x = invWidth * (boxCoords[0] + boxCoords[2])/2.0
        y = invHeight * (boxCoords[1] + boxCoords[3])/2.0
        boxWidth = invWidth * (boxCoords[2] - boxCoords[0])
        boxHeight = invHeight * (boxCoords[3] - boxCoords[1])
        return (x,y,boxWidth,boxHeight)
 
    def updateStatus(self, newStatus):
        self.statusText.set("Status: " + newStatus)

    def YoloLabelWriteOut(self, filename, classname, topLeftX, topLeftY, bottomRightX, bottomRightY):
        labelFile = open(filename, "a+")
        #TODO - get image w/h
        yoloOut = self.convert2Yolo([1000,1000], 
                                [topLeftX, topLeftY, bottomRightX, bottomRightY] );
        labelFile.write('%s' %classname)               
        labelFile.write(' %.7f %.7f %.7f %.7f\n' % (yoloOut[0], yoloOut[1], yoloOut[2], yoloOut[3]))                                  
        labelFile.close()
    def KittiLabelWriteOut(self, filename, classname, topLeftX, topLeftY, bottomRightX, bottomRightY):
        labelFile = open(filename, "a+")
        #TODO - get image w/h
        labelFile.write('%s' %classname)               
        labelFile.write(' 0.0 0 0.0 ')
        labelFile.write('%.2f %.2f %.2f %.2f' % (topLeftX, topLeftY, bottomRightX, bottomRightY))                 
        labelFile.write(' 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 ')
        labelFile.write('\n')    
        labelFile.close()
        
        
    # Convert label formats
    def ConvertLabels(self):          
         #get image list
        labelFileTypes = ('*.txt') # the tuple of file types
        self.labelFileList = []
    
        # load labels
        for files in labelFileTypes:
            self.labelFileList.extend(glob.glob(os.path.join(self.imageDir, files.lower())) )
        #    if (False == self.is_windows):
        #        self.labelFileList.extend(glob.glob(os.path.join(self.imageDir, files)) )
            
        if len(self.labelFileList) == 0:
            tkMessageBox.showerror("Label files not found", message = "No labels (.txt) found in folder!")
            self.updateStatus( 'No label files found in the specified dir!')
            return
        # Change title
        self.parent.title("Euclid Label Converter (" + self.imageDir + ") " + str(len(self.labelFileList)) + " label files")

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.labelFileList)

         # set up output dir
        self.outDir = os.path.join(self.imageDir + '/ConvertedLabelData')
        if not os.path.exists(self.outDir):
            os.mkdir(self.outDir)

        self.updateStatus( '%d label files located from %s' %(self.total, self.imageDir))

        # Convert one file
        self.labelfilename = self.labelFileList[self.cur - 1]
        lastPartFileName, lastPartFileExtension = os.path.splitext(os.path.split(self.labelfilename)[-1])
        newFileName = self.outDir + '/' + lastPartFileName + lastPartFileExtension
        bbox_cnt = 0
        if os.path.exists(self.labelfilename):
            with open(self.labelfilename) as f:
                for (i, line) in enumerate(f):
                    bbox_cnt = len(line)
                    tmp = [elements.strip() for elements in line.split()]
                    
                    # for each line, convert and writeout
                    
                    if(len(tmp) > 5):
                        self.currLabelMode='KITTI'
                        self.YoloLabelWriteOut(newFileName, CLASSES.index(tmp[0]), float(tmp[4]), float(tmp[5]), float(tmp[6]), float(tmp[7]) )
                        
                    elif(len(tmp) == 5):
                        self.currLabelMode='YOLO'
                        bbTuple = self.GetBoundariesFromYoloFile(float(tmp[1]),float(tmp[2]), float(tmp[3]),float(tmp[4]), 
                                                            self.tkimg.width(), self.tkimg.height() )
                        KittiLabelWriteOut(self.labelfilename, tmp[0], float(tmp[4]), float(tmp[5]), float(tmp[6]), float(tmp[7]) )
                                           
        
if __name__ == '__main__':
    root = Tk()
    tool = EuclidConverter(root)
    root.mainloop()

