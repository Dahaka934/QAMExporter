import tkinter as tk
from tkinter import filedialog

from mpl_toolkits.mplot3d import axes3d
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, TextBox

from approximator import Approximator

from numpy import array

root = tk.Tk()
root.withdraw()

class Transform:
    def __init__(self, timings, lists):
        self.timings = timings
        self.lists = lists
        self.dim = len(lists)

def readTestTransform(file_path):
    with open(file_path) as f:
        content = f.readlines()

    content = [x.strip() for x in content]

    defTimings = [float(x) for x in content[2].split()]
    defTranslation = [[float(x) for x in content[5 + i * 2].split()] for i in range(0, 3)]
    defRotation = [[float(x) for x in content[12 + i * 2].split()] for i in range(0, 4)]
    defScale = [[float(x) for x in content[21 + i * 2].split()] for i in range(0, 3)]

    apprTranslationT = [float(x) for x in content[29 + 0 * 2].split()]
    apprRotationT = [float(x) for x in content[38 + 0 * 2].split()]
    apprScaleT = [float(x) for x in content[49 + 0 * 2].split()]

    apprTranslation = [[float(x) for x in content[29 + i * 2].split()] for i in range(1, 4)]
    apprRotation = [[float(x) for x in content[38 + i * 2].split()] for i in range(1, 5)]
    apprScale = [[float(x) for x in content[49 + i * 2].split()] for i in range(1, 4)]

    return Transform(defTimings, defTranslation), \
           Transform(defTimings, defRotation), \
           Transform(defTimings, defScale), \
           Transform(apprTranslationT, apprTranslation), \
           Transform(apprRotationT, apprRotation), \
           Transform(apprScaleT, apprScale)

file_path = filedialog.askopenfilename()
defTranslation, defRotation, defScale, apprTranslation, apprRotation, apprScale = readTestTransform(file_path)
fig = plt.figure()

class IterableApproxArray:
    def __init__(self, lists):
        if isinstance(lists, Transform):
            group = lists.lists + [lists.timings]
            self.srcArray = array(list(zip(*group)))
            self.dimSize = len(group)
        else:
            self.srcArray = array(list(zip(*lists)))
            self.dimSize = len(lists)
        self.indices = None
        self.weights = None
        self.approx = [None for i in range(0, self.dimSize)]
        self.approximator = Approximator(self.dimSize)
        self.maxError = None

    def approximate(self):
        self.indices, self.weights = self.approximator.approximateIterable(self.srcArray, self.indices, self.weights)
        for i in range(0, self.dimSize):
            self.approx[i] = [self.srcArray[j][i] for j in self.indices]
        item = self.approximator.findMaxError(self.weights)
        self.maxError = self.weights[item][1]

    def approximateByError(self, err):
        indices = self.approximator.approximate(self.srcArray, err)
        for i in range(0, self.dimSize):
            self.approx[i] = [self.srcArray[j][i] for j in indices]
        self.maxError = None

    def clean(self):
        self.indices = None
        self.weights = None
        self.approx = [None for i in range(0, self.dimSize)]
        self.maxError = None

class Plot(object):
    ind = 0
    max = 10

    ax = None
    text = None

    apprTranslationArray = IterableApproxArray(defTranslation)
    apprRotationArray = IterableApproxArray(defRotation)
    apprScaleArray = IterableApproxArray(defScale)
    apprTransformArray = None

    def __init__(self, ind):
        self.ind = ind

    def plot2DTransform(self, index, defTransform, apprTransform, apprArray):
        self.ax.plot(defTransform.timings, defTransform.lists[index], 'k-s', label='default')
        self.ax.plot(apprTransform.timings, apprTransform.lists[index], 'c-s', label='approx')
        apprTimingsNew = apprArray.approx[len(apprArray.approx) - 1]
        apprTransformNew = apprArray.approx[index]
        if apprTimingsNew is not None and apprTransformNew is not None:
            self.ax.plot(apprTimingsNew, apprTransformNew, 'r-x', label='approx new')

    def setError(self):
        if self.apprTransformArray.maxError is not None:
            self.text.set_text("Error: %f" % self.apprTransformArray.maxError)
        else:
            self.text.set_text("")

    def setup(self):
        if self.ax is not None:
            fig.delaxes(self.ax)
            self.ax = None
        if self.text is None:
            self.text = plt.text(-1, 16.00, '')

        if self.ind >= 10:
            self.ax = fig.add_subplot(111, projection='3d')
            self.ax.set_zlabel('z zxis')
        else:
            self.ax = fig.add_subplot(111)
        self.ax.set_xlabel('x zxis')
        self.ax.set_ylabel('y zxis')

        if self.ind == 0:
            self.plot2DTransform(0, defTranslation, apprTranslation, self.apprTranslationArray)
            self.apprTransformArray = self.apprTranslationArray
            plt.title('2D Translation X')
        elif self.ind == 1:
            self.plot2DTransform(1, defTranslation, apprTranslation, self.apprTranslationArray)
            self.apprTransformArray = self.apprTranslationArray
            plt.title('2D Translation Y')
        elif self.ind == 2:
            self.plot2DTransform(2, defTranslation, apprTranslation, self.apprTranslationArray)
            self.apprTransformArray = self.apprTranslationArray
            plt.title('2D Translation Z')
        elif self.ind == 3:
            self.plot2DTransform(0, defRotation, apprRotation, self.apprRotationArray)
            self.apprTransformArray = self.apprRotationArray
            plt.title('2D Rotation X')
        elif self.ind == 4:
            self.plot2DTransform(1, defRotation, apprRotation, self.apprRotationArray)
            self.apprTransformArray = self.apprRotationArray
            plt.title('2D Rotation Y')
        elif self.ind == 5:
            self.plot2DTransform(2, defRotation, apprRotation, self.apprRotationArray)
            self.apprTransformArray = self.apprRotationArray
            plt.title('2D Rotation Z')
        elif self.ind == 6:
            self.plot2DTransform(3, defRotation, apprRotation, self.apprRotationArray)
            self.apprTransformArray = self.apprRotationArray
            plt.title('2D Rotation W')
        elif self.ind == 7:
            self.plot2DTransform(0, defScale, apprScale, self.apprScaleArray)
            self.apprTransformArray = self.apprScaleArray
            plt.title('2D Scale X')
        elif self.ind == 8:
            self.plot2DTransform(1, defScale, apprScale, self.apprScaleArray)
            self.apprTransformArray = self.apprScaleArray
            plt.title('2D Scale Y')
        elif self.ind == 9:
            self.plot2DTransform(2, defScale, apprScale, self.apprScaleArray)
            self.apprTransformArray = self.apprScaleArray
            plt.title('2D Scale Z')
        elif self.ind == 10:
            self.apprTransformArray = self.apprTranslationArray
            plt.title('3D Translation XYZ')
        elif self.ind == 11:
            self.apprTransformArray = self.apprRotationArray
            plt.title('3D Rotation XYZ')
        elif self.ind == 12:
            self.apprTransformArray = self.apprRotationArray
            plt.title('3D Rotation YZW')
        elif self.ind == 13:
            self.apprTransformArray = self.apprScaleArray
            plt.title('3D Scale XYZ')

        leg = self.ax.legend(shadow=True, fancybox=True)
        leg.get_frame().set_alpha(0.5)
        self.setError()

        plt.draw()

    def approx1(self, event):
        self.apprTransformArray.approximate()
        self.setup()

    def approx(self, event):
        try:
            self.apprTransformArray.approximateByError(float(event))
            self.setup()
        except:
            pass

    def clean(self, event):
        self.apprTransformArray.clean()
        self.setup()

    def next(self, event):
        self.ind += 1
        if self.ind >= self.max:
            self.ind = 0
        self.setup()

    def prev(self, event):
        self.ind -= 1
        if self.ind < 0:
            self.ind = self.max - 1
        self.setup()

callback = Plot(0)
bprev = Button(plt.axes([0.01, 0.00, 0.06, 0.06]), 'Prev')
bnext = Button(plt.axes([0.07, 0.00, 0.06, 0.06]), 'Next')
bapprox1 = Button(plt.axes([0.13, 0.00, 0.10, 0.06]), 'Approx1')
bclean = Button(plt.axes([0.23, 0.00, 0.10, 0.06]), 'Clean')
text_box = TextBox(plt.axes([0.90, 0.00, 0.10, 0.06]), 'Approx')
bprev.on_clicked(callback.prev)
bnext.on_clicked(callback.next)
bapprox1.on_clicked(callback.approx1)
bclean.on_clicked(callback.clean)
text_box.on_submit(callback.approx)

callback.setup()
plt.show()
