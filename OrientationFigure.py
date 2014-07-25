from __future__ import division
import os
import unittest
import numpy as np
from __main__ import vtk, qt, ctk, slicer

#
# OrientationFigure
#

class OrientationFigure:
  def __init__(self, parent):
    parent.title = "Orientation Figure" 
    parent.categories = ["Quantification"]
    parent.dependencies = []
    parent.contributors = ["Alireza Mehrtash (SPL, BWH), Andrey Fedorov (SPL, BWH), Steve Pieper (Isomics)"]
    parent.helpText = """
    """
    parent.acknowledgementText = """
    Supported by NIH U01CA151261 (PI Fennessy) and U24 CA180918 (PIs Kikinis and Fedorov).
    """
    self.parent = parent

    # Add this test to the SelfTest module's list for discovery when the module
    # is created.  Since this module may be discovered before SelfTests itself,
    # create the list if it doesn't already exist.
    try:
      slicer.selfTests
    except AttributeError:
      slicer.selfTests = {}
    slicer.selfTests['OrientationFigure'] = self.runTest

  def runTest(self):
    tester = OrientationFigureTest()
    tester.runTest()
#
# OrientationFigureWidget
#

class OrientationFigureWidget:
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()

    self.scene = slicer.mrmlScene
    self.layoutManager = slicer.app.layoutManager()
    self.sliceViews = {}

    self.cameraPositionMultiplier = 350
    self.viewPortFinishHeight = 0.3
    self.viewPortStartWidth = 0.8

    self.humanActor = None

    #
    # Setting 3D models
    #

    # Module's Path
    # TODO: Update if moved to another module
    modulePath= slicer.modules.orientationfigure.path.replace("OrientationFigure.py","")

    # Test whether the model is already loaded into the scene or not.
    # (Useful on Reload)
    nodes = self.scene.GetNodesByName('slicer-human-model') 
    if nodes.GetNumberOfItems() == 0 :
      modelPath = modulePath + "Resources/Models/" + "slicer-human-model.stl"
      modelFiles = [ "slicer-human-model.stl","shorts-model.stl", "left-shoe.stl",
         "right-shoe.stl"]
      modelPaths = [modulePath + "Resources/Models/"+ 
          modelFile for modelFile in modelFiles]
      for modelPath in modelPaths:
        successfulLoad = slicer.util.loadModel(modelPath)
        if successfulLoad != True:
          print 'Warning: model %s did not load' %modelPath

    modelNodes = []
    # Human node
    self.humanNode = self.scene.GetNodesByName('slicer-human-model').GetItemAsObject(0)
    modelNodes.append(self.humanNode)
    # Shorts node
    self.shortsNode = self.scene.GetNodesByName('shorts-model').GetItemAsObject(0)
    modelNodes.append(self.shortsNode)
    # Left shoe node
    self.leftShoeNode = self.scene.GetNodesByName('left-shoe').GetItemAsObject(0)
    modelNodes.append(self.leftShoeNode)
    # Right shoe node
    self.rightShoeNode = self.scene.GetNodesByName('right-shoe').GetItemAsObject(0)
    modelNodes.append(self.rightShoeNode)

    for node in modelNodes:
      node.HideFromEditorsOn()
      node.SetDisplayVisibility(False)

  def setup(self):
    # Instantiate and connect widgets ...

    #
    # Reload and Test area
    #
    reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    reloadCollapsibleButton.text = "Reload && Test"
    self.layout.addWidget(reloadCollapsibleButton)
    reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

    # reload button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "OrientationFigure Reload"
    reloadFormLayout.addWidget(self.reloadButton)
    self.reloadButton.connect('clicked()', self.onReload)

    # reload and test button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadAndTestButton = qt.QPushButton("Reload and Test")
    self.reloadAndTestButton.toolTip = "Reload this module and then run the self tests."
    reloadFormLayout.addWidget(self.reloadAndTestButton)
    self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    self.showHumanModelCheckBox = qt.QCheckBox('Show Orientation Dude')
    parametersFormLayout.addRow(self.showHumanModelCheckBox)

    # camera zoom slider
    self.zoomSlider = ctk.ctkSliderWidget()
    parametersFormLayout.addRow('Camera Zoom: ', self.zoomSlider)
    self.zoomSlider.value = 35
    self.zoomSlider.minimum = 1
    self.zoomSlider.maximum = 100
    self.zoomSlider.pageStep = 1
    self.zoomSlider.enabled = False
    self.zoomSlider.connect('valueChanged(double)', self.zoomSliderValueChanged)

    # viewport width
    self.viewPortWidthSlider = ctk.ctkSliderWidget()
    parametersFormLayout.addRow('View Width: ', self.viewPortWidthSlider)
    self.viewPortWidthSlider.value = 20
    self.viewPortWidthSlider.enabled = False

    # viewport height
    self.viewPortHeightSlider = ctk.ctkSliderWidget()
    parametersFormLayout.addRow('View Height: ', self.viewPortHeightSlider)
    self.viewPortHeightSlider.value = 30
    self.viewPortHeightSlider.enabled = False

    # Add vertical spacer
    self.layout.addStretch(1)

    # connections
    self.showHumanModelCheckBox.connect('clicked()',
        self.updateSliceViewFromGUI)
    self.viewPortWidthSlider .connect('valueChanged(double)',
        self.viewPortWidthValueChanged)
    self.viewPortHeightSlider.connect('valueChanged(double)',
        self.viewPortHeightValueChanged)

  def cleanup(self):
    pass

  def zoomSliderValueChanged(self):
    self.cameraPositionMultiplier = self.zoomSlider.value*10
    self.updateSliceViewFromGUI()

  def viewPortWidthValueChanged(self, value):
    self.viewPortStartWidth = 1- value/100
    self.updateSliceViewFromGUI()

  def viewPortHeightValueChanged(self, value):
    self.viewPortFinishHeight= value/100
    self.updateSliceViewFromGUI()

  def updateSliceViewFromGUI(self):
    # Create corner annotations if have not created already
    if len(self.sliceViews.items()) == 0:
      self.setupViews()

    for sliceViewName in self.sliceViewNames:
      sliceWidget = self.layoutManager.sliceWidget(sliceViewName)
      sl = sliceWidget.sliceLogic()
      self.makeScene(sl)

    for slider in [self.zoomSlider,self.viewPortWidthSlider
        ,self.viewPortHeightSlider]:
      slider.enabled = self.showHumanModelCheckBox.checked

  def setupViews(self):
    self.sliceViewNames = []
    self.renderers = {}

    sliceViewNames = self.layoutManager.sliceViewNames()
    for sliceViewName in sliceViewNames:
      self.sliceViewNames.append(sliceViewName)
      self.addObserver(sliceViewName)

  def addObserver(self, sliceViewName):
    sliceWidget = self.layoutManager.sliceWidget(sliceViewName)
    sliceView = sliceWidget.sliceView()

    self.sliceViews[sliceViewName] = sliceView
    sliceLogic = sliceWidget.sliceLogic()

    sliceLogic.AddObserver(vtk.vtkCommand.ModifiedEvent, self.updateCornerAnnotations)

    self.renderers[sliceViewName] = vtk.vtkRenderer()

  def updateCornerAnnotations(self,caller,event):
    sliceViewNames = self.layoutManager.sliceViewNames()
    for sliceViewName in sliceViewNames:
      if sliceViewName not in self.sliceViewNames:
        self.sliceViewNames.append(sliceViewName)
        self.addObserver(sliceViewName)
        self.updateSliceViewFromGUI()
    self.makeScene(caller)

  def makeScene(self, sliceLogic):
    sliceNode = sliceLogic.GetBackgroundLayer().GetSliceNode()
    sliceViewName = sliceNode.GetLayoutName()

    if self.sliceViews[sliceViewName]:
      ren = self.renderers[sliceViewName]
      rw = self.sliceViews[sliceViewName].renderWindow()
      ren.SetViewport(self.viewPortStartWidth,0,1,self.viewPortFinishHeight)

      if self.showHumanModelCheckBox.checked:


        if self.humanActor == None:
          #
          # Making vtk mappers and actors
          #
          # Mappers
          humanMapper = vtk.vtkPolyDataMapper()
          if vtk.VTK_MAJOR_VERSION <= 5:
            humanMapper.SetInput(self.humanNode.GetPolyData())
          else:
            humanMapper.SetInputData(self.humanNode.GetPolyData())

          shortsMapper = vtk.vtkPolyDataMapper()
          if vtk.VTK_MAJOR_VERSION <= 5:
            shortsMapper.SetInput(self.shortsNode.GetPolyData())
          else:
            shortsMapper.SetInputData(self.shortsNode.GetPolyData())

          leftShoeMapper = vtk.vtkPolyDataMapper()
          if vtk.VTK_MAJOR_VERSION <= 5:
            leftShoeMapper.SetInput(self.leftShoeNode.GetPolyData())
          else:
            leftShoeMapper.SetInputData(self.leftShoeNode.GetPolyData())

          rightShoeMapper = vtk.vtkPolyDataMapper()
          if vtk.VTK_MAJOR_VERSION <= 5:
            rightShoeMapper.SetInput(self.rightShoeNode.GetPolyData())
          else:
            leftShoeMapper.SetInputData(self.leftShoeNode.GetPolyData())

          # Actors
          self.humanActor = vtk.vtkActor()
          self.humanActor.SetMapper(humanMapper)
          self.humanActor.GetProperty().SetColor(0.93,0.81,0.80)

          self.shortsActor = vtk.vtkActor()
          self.shortsActor.SetMapper(shortsMapper)
          self.shortsActor.GetProperty().SetColor(0,0,1)

          self.leftShoeActor = vtk.vtkActor()
          self.leftShoeActor.SetMapper(leftShoeMapper)
          self.leftShoeActor.GetProperty().SetColor(1,0,0)

          self.rightShoeActor = vtk.vtkActor()
          self.rightShoeActor.SetMapper(rightShoeMapper)
          self.rightShoeActor.GetProperty().SetColor(0,1,0)

        # Add actors to renderer
        ren.AddActor(self.humanActor)
        ren.AddActor(self.shortsActor)
        ren.AddActor(self.leftShoeActor)
        ren.AddActor(self.rightShoeActor)

        # Calculate the camera position and viewup based on XYToRAS matrix
        camera = vtk.vtkCamera()

        m = sliceNode.GetXYToRAS()
        x = np.matrix([[m.GetElement(0,0),m.GetElement(0,1),m.GetElement(0,2)],
            [m.GetElement(1,0),m.GetElement(1,1),m.GetElement(1,2)],
            [m.GetElement(2,0),m.GetElement(2,1),m.GetElement(2,2)]])

        # Calculating position
        y = np.array([0,0,self.cameraPositionMultiplier])
        position = np.inner(x,y)
        camera.SetPosition(-position[0,0],-position[0,1],-position[0,2])

        # Calculating viewUp
        n = np.array([0,1,0])
        viewUp = np.inner(x,n)
        camera.SetViewUp(viewUp[0,0],viewUp[0,1],viewUp[0,2])

        #ren.PreserveDepthBufferOff()
        ren.SetActiveCamera(camera)
        rw.AddRenderer(ren)

      else:
        ren.RemoveActor(self.humanActor)
        ren.RemoveActor(self.shortsActor)
        ren.RemoveActor(self.leftShoeActor)
        ren.RemoveActor(self.leftShoeActor)
        rw.RemoveRenderer(ren)

      # Refresh view
      self.sliceViews[sliceViewName].scheduleRender()

  def onReload(self,moduleName="OrientationFigure"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    globals()[moduleName] = slicer.util.reloadScriptedModule(moduleName)

  def onReloadAndTest(self,moduleName="OrientationFigure"):
    try:
      self.onReload()
      evalString = 'globals()["%s"].%sTest()' % (moduleName, moduleName)
      tester = eval(evalString)
      tester.runTest()
    except Exception, e:
      import traceback
      traceback.print_exc()
      qt.QMessageBox.warning(slicer.util.mainWindow(),
          "Reload and Test", 'Exception!\n\n' + str(e) + "\n\nSee Python Console for Stack Trace")

#
# OrientationFigureLogic
#

class OrientationFigureLogic:
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget
  """
  def __init__(self):
    pass

  def hasImageData(self,volumeNode):
    """This is a dummy logic method that
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      print('no volume node')
      return False
    if volumeNode.GetImageData() == None:
      print('no image data')
      return False
    return True

  def delayDisplay(self,message,msec=1000):
    #
    # logic version of delay display
    #
    print(message)
    self.info = qt.QDialog()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.label = qt.QLabel(message,self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()

class OrientationFigureTest(unittest.TestCase):
  """
  This is the test case for your scripted module.
  """

  def delayDisplay(self,message,msec=1000):
    """This utility method displays a small dialog and waits.
    This does two things: 1) it lets the event loop catch up
    to the state of the test so that rendering and widget updates
    have all taken place before the test continues and 2) it
    shows the user/developer/tester the state of the test
    so that we'll know when it breaks.
    """
    print(message)
    self.info = qt.QDialog()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.label = qt.QLabel(message,self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_OrientationFigure1()

  def test_OrientationFigure1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests sould exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://www.slicer.org/slicerWiki/images/4/43/MR-head.nrrd', 'MR-head.nrrd', slicer.util.loadVolume),
        )
    '''
    downloads = (
          ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
          )
     '''
    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        print('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        print('Loading %s...\n' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading\n')

    widget = OrientationFigureWidget()
    cb = widget.showHumanModelCheckBox
    cb.click()
    self.delayDisplay("Displaying orientation figure",3000)
    cb.click()
    self.delayDisplay('Test finished!')
    '''
    volumeNode = slicer.util.getNode(pattern="FA")
    logic = OrientationFigureLogic()
    self.assertTrue( logic.hasImageData(volumeNode) )
    '''
