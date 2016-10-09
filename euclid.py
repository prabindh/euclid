#-------------------------------------------------------------------------------
# Euclid - Labelling tool
# Create and label bounding boxes
#    prabindh@yahoo.com
#        Initial code taken from github.com/puzzledqs/BBox-Label-Tool
#        Modified to add more image types, image folders, labelling saves, and format
# Python 2.7
# pip install pillow
# pip install image
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

from Tkinter import *
import tkMessageBox
import tkFileDialog
from PIL import Image, ImageTk
import os
import glob
import random

# Object Classes (No spaces in name)
CLASSES = ['Class0', 'Class1', 'Class2']

class Euclid():

    #set class label 
    def setClass0(self):
        self.currClassLabel=0;
    def setClass1(self):
        self.currClassLabel=1;
    def setClass2(self):
        self.currClassLabel=2;

    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title("Euclid Labeller")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width = TRUE, height = TRUE)

        # initialize global state
        self.imageDir = ''
        self.imageList= []
        self.outDir = ''
        self.cur = 0
        self.total = 0
        self.imagename = ''
        self.labelfilename = ''
        self.imagefilename = ''
        self.tkimg = None

        # initialize mouse state
        self.STATE = {}
        self.STATE['click'] = 0
        self.STATE['x'], self.STATE['y'] = 0, 0

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

        # ----------------- GUI stuff ---------------------
        # dir entry & load
        self.browserBtn = Button(self.frame, text = "Select Dir", command = self.askDirectory)
        self.browserBtn.grid(row = 0, column = 0, sticky = W+E)        
        
        self.entry = Entry(self.frame)
        self.entry.grid(row = 0, column = 1, sticky = W+E)
        self.ldBtn = Button(self.frame, text = "Load", command = self.loadDir)
        self.ldBtn.grid(row = 0, column = 2, sticky = W+E)

	    #Class labels selection
        count = 0
        CLASSHANDLERS = [self.setClass0, self.setClass1, self.setClass2]
        for classLabel in CLASSES:
            classBtn = Button(self.frame, text = classLabel, command = CLASSHANDLERS[count])
            classBtn.grid(row = count, column = 3, sticky = W+E)
            count = count + 1


        # main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor='tcross', borderwidth=2, background='white')
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)
        self.parent.bind("<Escape>", self.cancelBBox)  # press <Escape> to cancel current bbox
        self.parent.bind("s", self.cancelBBox)
        self.parent.bind("a", self.prevImage) # press 'a' to go backforward
        self.parent.bind("d", self.nextImage) # press 'd' to go forward
        self.mainPanel.grid(row = 1, column = 1, rowspan = 4, sticky = W+N)

        # showing bbox info & delete bbox
        self.lb1 = Label(self.frame, text = 'Bounding boxes:')
        self.lb1.grid(row = 1, column = 2,  sticky = W+N)
        self.listbox = Listbox(self.frame, width = 32, height = 10)
        self.listbox.grid(row = 2, column = 2, sticky = N)
        self.btnDel = Button(self.frame, text = 'Delete', command = self.delBBox)
        self.btnDel.grid(row = 3, column = 2, sticky = W+E+N)
        self.btnClear = Button(self.frame, text = 'Clear All', command = self.clearBBox)
        self.btnClear.grid(row = 4, column = 2, sticky = W+E+N)
        self.saveLabelBtn = Button(self.frame, text = 'Save Label', command = self.saveLabel)
        self.saveLabelBtn.grid(row = 5, column = 2, sticky = W+E+N)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row = 6, column = 1, columnspan = 2, sticky = W+E)
        self.navLabel = Label(self.ctrPanel, text = 'File Navigation')
        self.navLabel.pack(side = LEFT, padx = 5, pady = 3)
        self.prevBtn = Button(self.ctrPanel, text='<< Prev', width = 10, command = self.prevImage)
        self.prevBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.nextBtn = Button(self.ctrPanel, text='Next >>', width = 10, command = self.nextImage)
        self.nextBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.progLabel = Label(self.ctrPanel, text = "Progress: [  0   /  0  ]")
        self.progLabel.pack(side = LEFT, padx = 5)
        self.tmpLabel = Label(self.ctrPanel, text = "Go to Image No.")
        self.tmpLabel.pack(side = LEFT, padx = 5)
        self.idxEntry = Entry(self.ctrPanel, width = 5)
        self.idxEntry.pack(side = LEFT)
        self.goBtn = Button(self.ctrPanel, text = 'Go', command = self.gotoImage)
        self.goBtn.pack(side = LEFT)

        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side = RIGHT)

        self.frame.columnconfigure(1, weight = 1)
        self.frame.rowconfigure(4, weight = 1)

    def askDirectory(self):
      self.imageDir = tkFileDialog.askdirectory()
      self.entry.insert(0, self.imageDir)
        
    def loadDir(self, dbg = False):
        self.imageDir = self.entry.get()
        self.parent.focus()
        if not os.path.isdir(self.imageDir):
            tkMessageBox.showerror("Error", message = "The specified directory doesn't exist!")
            return
        # get image list
	imageFileTypes = ('*.JPEG', '*.JPG', '*.PNG') # the tuple of file types
	self.imageList = []
	for files in imageFileTypes:
	    self.imageList.extend(glob.glob(os.path.join(self.imageDir, files.lower())) )
        if len(self.imageList) == 0:
            tkMessageBox.showerror("Info", message = "No images (png, jpeg, jpg) found in folder!")
            print 'No image files found in the specified dir!'
            return
        # Change title
        self.parent.title("Euclid Labeller (" + self.imageDir + ") " + str(len(self.imageList)) + " images")


        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

         # set up output dir
        self.outDir = os.path.join(self.imageDir + '/LabelData')
        if not os.path.exists(self.outDir):
            os.mkdir(self.outDir)


        self.loadImageAndLabels()
        print '%d images loaded from %s' %(self.total, self.imageDir)

    def loadImageAndLabels(self):
        # load image
        imagepath = self.imageList[self.cur - 1]
        self.imagefilename = imagepath
        self.img = Image.open(imagepath)
        self.tkimg = ImageTk.PhotoImage(self.img)
        self.mainPanel.config(width = max(self.tkimg.width(), 400), height = max(self.tkimg.height(), 400))
        self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)
        self.progLabel.config(text = "%04d/%04d" %(self.cur, self.total))

        # load labels
        self.clearBBox()
        self.imagename = os.path.split(imagepath)[-1].split('.')[0]
        labelname = self.imagename + '.txt'
        self.labelfilename = os.path.join(self.outDir, labelname)
        bbox_cnt = 0
        if os.path.exists(self.labelfilename):
            with open(self.labelfilename) as f:
                for (i, line) in enumerate(f):
                    bbox_cnt = len(line)
                    tmp = [elements.strip() for elements in line.split()]
                    bbTuple = (int(tmp[4]),int(tmp[5]), int(tmp[6]),int(tmp[7]) )
                    self.bboxList.append( bbTuple  )
                    #color set
                    currColor = '#%02x%02x%02x' % (self.redColor, self.greenColor, self.blueColor)
                    self.greenColor = (self.greenColor + 25) % 255
                    tmpId = self.mainPanel.create_rectangle(int(tmp[4]), int(tmp[5]), \
                                                            int(tmp[6]), int(tmp[7]), \
                                                            width = 2, \
                                                            outline = currColor)
                    self.bboxIdList.append(tmpId)
                    self.listbox.insert(END, '(%d, %d) -> (%d, %d) [%s]' %(int(tmp[4]), int(tmp[5]),  \
                                                        int(tmp[6]), int(tmp[7]), tmp[0]))
                    self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = currColor)

    def saveLabel(self):
        if self.labelfilename == '':
            return
        with open(self.labelfilename, 'w') as f:
            labelCnt=0
            ##class1 0 0 0 x1,y1,x2,y2 0,0,0 0,0,0 0 0  
            # fields ignored by DetectNet: alpha, scenario, roty, occlusion, dimensions, location.
            for bbox in self.bboxList:
                f.write('%s  ' %CLASSES[self.classLabelList[labelCnt]])               
                f.write(' 0.0 0 0.0 ')
                f.write(str(bbox[0])+' '+str(bbox[1])+' '+str(bbox[2])+' '+str(bbox[3]))
                f.write(' 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 ')
                f.write('\n')
                labelCnt = labelCnt+1
        print 'Image No. %d saved' %(self.cur)


    def mouseClick(self, event):
        if self.imagefilename == '':
            return
        if self.STATE['click'] == 0:
            self.STATE['x'], self.STATE['y'] = event.x, event.y
        else:
            #Got a new BB, store the class label also
            x1, x2 = min(self.STATE['x'], event.x), max(self.STATE['x'], event.x)
            y1, y2 = min(self.STATE['y'], event.y), max(self.STATE['y'], event.y)
            self.bboxList.append((x1, y1, x2, y2))
            self.bboxIdList.append(self.bboxId)
            self.classLabelList.append(self.currClassLabel)
            print self.classLabelList
            self.bboxId = None
            self.listbox.insert(END, '(%d, %d) -> (%d, %d)[Class %d]' %(x1, y1, x2, y2 , self.currClassLabel))
            #color set
            currColor = '#%02x%02x%02x' % (self.redColor, self.greenColor, self.blueColor)
            self.redColor = (self.redColor + 25) % 255         
            self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = currColor)
        self.STATE['click'] = 1 - self.STATE['click']

    def mouseMove(self, event):
        if self.imagefilename == '':
            return
        self.disp.config(text = 'x: %d, y: %d' %(event.x, event.y))
        if self.tkimg:
            if self.hl:
                self.mainPanel.delete(self.hl)
            self.hl = self.mainPanel.create_line(0, event.y, self.tkimg.width(), event.y, width = 2)
            if self.vl:
                self.mainPanel.delete(self.vl)
            self.vl = self.mainPanel.create_line(event.x, 0, event.x, self.tkimg.height(), width = 2)
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
            #color set
            currColor = '#%02x%02x%02x' % (self.redColor, self.greenColor, self.blueColor)
            self.blueColor = (self.blueColor + 25) % 255                
            self.bboxId = self.mainPanel.create_rectangle(self.STATE['x'], self.STATE['y'], \
                                                            event.x, event.y, \
                                                            width = 2, \
                                                            outline = currColor)

    def cancelBBox(self, event):
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
                self.bboxId = None
                self.STATE['click'] = 0

    def delBBox(self):
        sel = self.listbox.curselection()
        if len(sel) != 1 :
            return
        idx = int(sel[0])
        self.mainPanel.delete(self.bboxIdList[idx])
        self.bboxIdList.pop(idx)
        self.bboxList.pop(idx)
        self.listbox.delete(idx)

    def clearBBox(self):
        for idx in range(len(self.bboxIdList)):
            self.mainPanel.delete(self.bboxIdList[idx])
        self.listbox.delete(0, len(self.bboxList))
        self.bboxIdList = []
        self.bboxList = []

    def prevImage(self, event = None):
        if self.cur > 1:
            self.cur -= 1
            self.loadImageAndLabels()

    def nextImage(self, event = None):
        if self.cur < self.total:
            self.cur += 1
            self.loadImageAndLabels()

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.cur = idx
            self.loadImageAndLabels()

if __name__ == '__main__':
    root = Tk()
    tool = Euclid(root)
    root.mainloop()

