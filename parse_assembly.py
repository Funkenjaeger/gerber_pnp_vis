import pandas
import sys
import os
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QMainWindow, QTreeWidgetItem, QGraphicsScene, QFileDialog, \
    QGraphicsPixmapItem
from PySide2.QtGui import QPixmap, QPen
from PySide2.QtCore import QFile, Qt
import gerber_render
import configparser


def populatebomtree():
    global bom, assy_top, assy_bot, viewtop
    bom = pandas.read_csv(os.path.join(BASE_FOLDER, 'Assembly\\bom.csv'), header=0)
    assy_top = pandas.read_csv(os.path.join(BASE_FOLDER, 'Assembly\\PnP_front.csv'), header=0)
    assy_bot = pandas.read_csv(os.path.join(BASE_FOLDER, 'Assembly\\PnP_back.csv'), header=0)

    tw = window.treeWidget_bom
    tw.clearSelection()
    tw.clear()
    assy_side = assy_top if viewtop else assy_bot
    for index, row in bom.iterrows():
        selected = str.split(row['Parts'], ', ')
        pnp_refdes = assy_side['Name']
        pnp_count = 0
        parts_thisside = ''
        for refdes in selected:
            pnp_row = assy_side[pnp_refdes == refdes]
            if len(pnp_row) > 0:
                if pnp_count == 0:
                    twi = QTreeWidgetItem(tw, [row['Parts'], row['Value'], row['Device'], row['Package'],
                                               row['Description']])
                parts_thisside = parts_thisside + ',' + refdes if pnp_count > 0 else refdes
                pnp_count = pnp_count + 1
                twi.addChild(QTreeWidgetItem(twi, [pnp_row['Name'].values[0]]))
        if pnp_count > 0 and pnp_count < len(selected):
            twi.setData(0, Qt.DisplayRole, parts_thisside)
        if pnp_count == 1:
            twi.removeChild(twi.child(0))


class TestWindow(QMainWindow):
    def __init__(self, parent=None):
        super(TestWindow, self).__init__(parent)
        loader = QUiLoader()
        file = QFile("ui_gerber_pnp_vis.ui")
        if file.open(QFile.ReadOnly):
            self.window = loader.load(file, parent)
            file.close()
            self.setCentralWidget(self.window)
            self.show()

    def resizeEvent(self, event):
        scaleboardimage()


def scaleboardimage():
    try:
        if len(scene.items()) > 0:
            view = window.graphicsView
            scale = 0.99*min(view.width() / scene.width(), view.height() / scene.height())
            window.graphicsView.setScene(scene)
            window.graphicsView.resetTransform()
            window.graphicsView.scale(scale, scale)
    except NameError:
        return


def highlightparts():
    for sceneItem in scene.items():
        if type(sceneItem) not in [QGraphicsPixmapItem]:
            scene.removeItem(sceneItem)
    if len(window.treeWidget_bom.selectedItems()) > 0:
        item = window.treeWidget_bom.selectedItems()[0]
        if item.childCount() == 0:
            highlightpart(item)
        else:
            for index in range(item.childCount()):
                highlightpart(item.child(index))
            window.graphicsView.setScene(scene)


def highlightpart(item):
    global origin_in, ppi, viewtop
    rectsize = [25, 25]
    assy_side = assy_top if viewtop else assy_bot
    pnp_refdes = assy_side['Name']
    refdes = item.data(0, 0)
    pnp_row = assy_side[pnp_refdes == refdes]
    if len(pnp_row) > 0:
        x = (pnp_row['X']/25.4 - origin_in[0]) * ppi
        if not viewtop:
            x = scene.width() - x
        y = scene.height() - (pnp_row['Y']/25.4 - origin_in[1]) * ppi
        pen = QPen(Qt.yellow, 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        scene.addLine(x - rectsize[0], y - rectsize[1], x + rectsize[0], y + rectsize[1], pen)
        scene.addLine(x - rectsize[0], y + rectsize[1], x + rectsize[0], y - rectsize[1], pen)
        pen = QPen(Qt.red, 10, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        scene.addRect(x - rectsize[0] / 2, y - rectsize[1] / 2, rectsize[0], rectsize[1], pen)


def loadboard():
    global viewtop, pixmap_top, pixmap_bot, BASE_FOLDER, origin_in, ppi

    dialog = QFileDialog()
    BASE_FOLDER = dialog.getExistingDirectory(window, "Select CAMOutputs directory to process...",
                                              '.', QFileDialog.ShowDirsOnly)

    window.statusbar.showMessage('Processing ' + BASE_FOLDER)
    window.statusbar.repaint()
    if gerber_render.isrendercurrent(BASE_FOLDER):
        print('Render is current')
    else:
        gerber_render.render(BASE_FOLDER)

    config = configparser.ConfigParser()
    config.read(os.path.join(BASE_FOLDER, 'board.ini'))
    origin_in = [float(config['DIMENSIONS']['origin_x_in']), float(config['DIMENSIONS']['origin_y_in'])]
    ppi = float(config['DIMENSIONS']['ppi'])

    pixmap_top = QPixmap(os.path.join(BASE_FOLDER, 'board_top.png'))
    pixmap_bot = QPixmap(os.path.join(BASE_FOLDER, 'board_bottom.png'))
    setboardtop()

    window.actionSideTop.setChecked(True)
    window.actionSideBottom.setChecked(False)
    window.statusbar.showMessage('Done processing board', 10000)


def setboardtop():
    global viewtop
    viewtop = True
    window.actionSideTop.setChecked(True)
    window.actionSideBottom.setChecked(False)
    setboardside()


def setboardbot():
    global viewtop
    viewtop = False
    window.actionSideTop.setChecked(False)
    window.actionSideBottom.setChecked(True)
    setboardside()


def setboardside():
    global viewtop
    try:
        scene.clear()
        if viewtop:
            scene.addPixmap(pixmap_top)
        else:
            scene.addPixmap(pixmap_bot)
        scaleboardimage()
        populatebomtree()
    except NameError:
        window.actionSideTop.setChecked(False)
        window.actionSideBottom.setChecked(False)
        window.statusbar.showMessage('No board loaded', 3000)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    BASE_FOLDER = '.'
    viewtop = True

    test = TestWindow()
    window = test.window
    scene = QGraphicsScene()
    window.splitter.splitterMoved.connect(scaleboardimage)
    window.treeWidget_bom.itemSelectionChanged.connect(highlightparts)
    window.action_processgerbers.triggered.connect(loadboard)
    window.actionSideTop.triggered.connect(setboardtop)
    window.actionSideBottom.triggered.connect(setboardbot)

    window.statusbar.showMessage('No board loaded')

    sys.exit(app.exec_())
