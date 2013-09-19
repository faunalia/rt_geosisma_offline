# -*- coding: utf-8 -*-
# Copyright (C) 2013 Luca Casagrande (Gfosservices)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from qgis.core import *
from qgis.utils import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import QWebView

class GeosismaBridge(QObject):

    def __init__(self):
        QObject.__init__(self)

    
    @pyqtSlot(str)
    def showFeature(self, feature): 
        '''
        Highlight the feature in QGis when moving the mouse
        over an element of the graph
        '''
 
        layer = iface.activeLayer()
        layer.setSelectedFeatures([int(feature)])

        return

    @pyqtSlot()
    def zoomToFeature(self):
        '''
        Click on the graph and zoom to feature
        '''

        iface.mapCanvas().zoomToSelected()
        return

    def _inputDataJSON(self):
        '''
        This is a json object created from attribute table
        using all the fields coming from input_list
        '''

        output = []

        #Add Active and vector layer check
        layer = iface.activeLayer()

        #Create a json from selected attribute
        for row in layer.getFeatures():
            attribute = {}
            for aindex,avalue in enumerate(self.input_list):
                attribute[aindex] = row[avalue]
            output.append(attribute)
        
        json_output = json.dumps(output)
        return json_output

    inputDataJSON = pyqtProperty(str, fget=_inputDataJSON)

    def _inputDataTSV(self):
        '''
        This is a tsv output created from attribute table
        using all the fields coming from input_list. The file is created
        in the template/data folder with the name input.tsv
        '''

        tsv_path = os.path.dirname(os.path.realpath(__file__))+'/template/data/'+'input.tsv'

        #Add Active and vector layer check
        layer = iface.activeLayer()

        with open(tsv_path, 'wb') as csvfile:
            tsvwriter = csv.writer(csvfile, delimiter='\t',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)

            #Header of TSV file
            tsvwriter.writerow(self.input_list)

            #Line of the TSV file

            for row in layer.getFeatures():
                attribute = []
                for aindex,avalue in enumerate(self.input_list):
                    attribute.append(row[avalue])
                
                tsvwriter.writerow(attribute)
        
        return 'input.tsv'

    inputDataTSV = pyqtProperty(str, fget=_inputDataTSV)

    def _inputDataCSV(self):
        '''
        This is a csv output created from attribute table
        using all the fields coming from input_list. The file is created
        in the template/data folder with the name input.csv
        '''

        csv_path = os.path.dirname(os.path.realpath(__file__))+'/template/data/'+'input.csv'

        #Add Active and vector layer check
        layer = iface.activeLayer()

        with open(csv_path, 'wb') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)

            #Header of TSV file
            csvwriter.writerow(self.input_list)

            #Line of the TSV file

            for row in layer.getFeatures():
                attribute = []
                for aindex,avalue in enumerate(self.input_list):
                    attribute.append(row[avalue])
                
                csvwriter.writerow(attribute)
        
        return 'input.csv'

    inputDataCSV = pyqtProperty(str, fget=_inputDataCSV)

class Geosisma:

    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()

    def initGui(self):
        self.action = QAction(QIcon(":/plugins/"), "&Geosisma-prototype", self.iface.mainWindow())
        QObject.connect(self.action, SIGNAL("activated()"), self.show_graph) 
        self.iface.addPluginToMenu("Geosisma-prototype", self.action)

    def unload(self):
        self.iface.removePluginMenu("Geosisma-prototype",self.action)


    def show_graph(self):
        GeosismaWebForm = 'GeosismaSchedaAgibilita.html'
        template_path = os.path.dirname(os.path.realpath(__file__))+'/template/'+GeosismaWebForm
        self.web = QWebView()
        self.web.load(QUrl(template_path))
        self.web.show()

if __name__ == "__main__":
    pass
