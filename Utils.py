# -*- coding: utf-8 -*-

"""
/***************************************************************************
Name                 : Omero RT
Description          : Omero plugin
Date                 : August 15, 2010 
copyright            : (C) 2010 by Giuseppe Sucameli (Faunalia)
email                : sucameli@faunalia.it
 ***************************************************************************/

This code has been extracted and adapted from rt_omero plugin to be resused 
in rt_geosisma_offline plugin

Works done from Faunalia (http://www.faunalia.it) with funding from Regione 
Toscana - Servizio Sismico (http://www.rete.toscana.it/sett/pta/sismica/)

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import *
import qgis.gui


class MapTool(QObject):
	canvas = None
	registeredToolStatusMsg = {}

	def __init__(self, mapToolClass, canvas=None):
		QObject.__init__(self)
		if canvas == None:
			if MapTool.canvas == None:
				raise Exception( "MapTool.canvas is None" )
			else:
				self.canvas = MapTool.canvas
		else:
			self.canvas = canvas
			if MapTool.canvas == None:
				MapTool.canvas = canvas

		self.tool = mapToolClass( self.canvas )
		QObject.connect(self.tool, SIGNAL( "geometryDrawingEnded" ), self.onEnd)

	def deleteLater(self):
		self.unregisterStatusMsg()
		self.stopCapture()
		self.tool.deleteLater()
		del self.tool
		return QObject.deleteLater(self)


	def registerStatusMsg(self, statusMessage):
		MapTool.registeredToolStatusMsg[self] = statusMessage

	def unregisterStatusMsg(self):
		if not MapTool.registeredToolStatusMsg.has_key( self ):
			return
		del MapTool.registeredToolStatusMsg[self]


	def onEnd(self, geometry):
		self.stopCapture()
		if geometry == None:
			return
		self.emit( SIGNAL( "geometryEmitted" ), geometry )

	def isActive(self):
		return self.canvas != None and self.canvas.mapTool() == self.tool

	def startCapture(self):
		self.canvas.setMapTool( self.tool )

	def stopCapture(self):
		self.canvas.unsetMapTool( self.tool )

	class Drawer(qgis.gui.QgsMapToolEmitPoint):
		def __init__(self, canvas, isPolygon=False):
			self.canvas = canvas
			self.isPolygon = isPolygon
			qgis.gui.QgsMapToolEmitPoint.__init__(self, self.canvas)

			self.rubberBand = qgis.gui.QgsRubberBand( self.canvas, self.isPolygon )
			self.rubberBand.setColor( Qt.red )
			self.rubberBand.setBrushStyle(Qt.DiagCrossPattern)
			self.rubberBand.setWidth( 1 )

			# imposta lo snap a snap to vertex with tollerance 0.9 map units
			customSnapOptions = { 'mode' : "to vertex", 'tolerance' : 0.3, 'unit' : 0 }
			self.oldSnapOptions = self.customizeSnapping( customSnapOptions )
			self.snapper = qgis.gui.QgsMapCanvasSnapper( self.canvas )

			self.isEmittingPoints = False

		def __del__(self):
			if self.oldSnapOptions:
				self.customizeSnapping( self.oldSnapOptions )
			del self.rubberBand
			del self.snapper
			self.deleteLater()

		def reset(self):
			self.isEmittingPoints = False
			self.rubberBand.reset( self.isPolygon )

		def customizeSnapping(self, option):
			oldSnap = {}
			settings = QSettings()
			oldSnap['mode'] = settings.value( "/Qgis/digitizing/default_snap_mode", "to vertex", type=str)
			oldSnap['tolerance'] = settings.value( "/Qgis/digitizing/default_snapping_tolerance", 0, type=float)
			oldSnap['unit'] = settings.value( "/Qgis/digitizing/default_snapping_tolerance_unit", 1, type=int )
			settings.setValue( "/Qgis/digitizing/default_snap_mode", option['mode'] )
			settings.setValue( "/Qgis/digitizing/default_snapping_tolerance", option['tolerance'] )
			settings.setValue( "/Qgis/digitizing/default_snapping_tolerance_unit", option['unit'] )
			return oldSnap
	
		def canvasPressEvent(self, e):
			if e.button() == Qt.RightButton:
				self.isEmittingPoints = False
				self.emit( SIGNAL("geometryDrawingEnded"), self.geometry() )
				return

			if e.button() == Qt.LeftButton:
				self.isEmittingPoints = True
			else:
				return
			point = self.toMapCoordinates( e.pos() )
			self.rubberBand.addPoint( point, True )	# true to update canvas
			self.rubberBand.show()

		def canvasMoveEvent(self, e):
			if not self.isEmittingPoints:
				return

			retval, snapResults = self.snapper.snapToBackgroundLayers( e.pos() )
			if retval == 0 and len(snapResults) > 0:
				point = snapResults[0].snappedVertex
			else:
				point = self.toMapCoordinates( e.pos() )

			self.rubberBand.movePoint( point )

		def isValid(self):
			return self.rubberBand.numberOfVertices() > 0

		def geometry(self):
			if not self.isValid():
				return None
			geom = self.rubberBand.asGeometry()
			if geom == None:
				return
			return QgsGeometry.fromWkt( geom.exportToWkt() )

		def deactivate(self):
			qgis.gui.QgsMapTool.deactivate(self)
			self.reset()
			self.emit(SIGNAL("deactivated()"))


class FeatureFinder(MapTool):

	def __init__(self, canvas=None):
		MapTool.__init__(self, qgis.gui.QgsMapToolEmitPoint, canvas=canvas)
		QObject.connect(self.tool, SIGNAL( "canvasClicked(const QgsPoint &, Qt::MouseButton)" ), self.onEnd)

	def onEnd(self, point, button):
		self.stopCapture()
		self.emit( SIGNAL("pointEmitted"), point, button )

	@classmethod
	def findAtPoint(self, layer, point, onlyTheClosestOne=True, onlyIds=False):
		QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

		point = MapTool.canvas.mapSettings().mapToLayerCoordinates(layer, point)

		# recupera il valore del raggio di ricerca
		settings = QSettings()
		radius = settings.value( "/Map/identifyRadius", QGis.DEFAULT_IDENTIFY_RADIUS, float )
		if radius <= 0:
			# XXX: in QGis 1.8 QGis.DEFAULT_IDENTIFY_RADIUS is 0, 
			# this cause the rectangle is empty and the select 
			# returns all the features...
			radius = 0.5	# it means 0.50% of the canvas extent
		radius = MapTool.canvas.extent().width() * radius/100.0

		# crea il rettangolo da usare per la ricerca
		rect = QgsRectangle()
		rect.setXMinimum(point.x() - radius)
		rect.setXMaximum(point.x() + radius)
		rect.setYMinimum(point.y() - radius)
		rect.setYMaximum(point.y() + radius)

		# recupera le feature che intersecano il rettangolo
		#layer.select([], rect, True, True)
		layer.select( rect, True )

		ret = None

		if onlyTheClosestOne:
			minDist = -1
			featureId = None
			rect2 = QgsGeometry.fromRect(rect)

			for f in layer.getFeatures(QgsFeatureRequest(rect)):
				if onlyTheClosestOne:
					geom = f.geometry()
					distance = geom.distance(rect2)
					if minDist < 0 or distance < minDist:
						minDist = distance
						featureId = f.id()

			if onlyIds:
				ret = featureId
			elif featureId != None:
				f = layer.getFeatures(QgsFeatureRequest().setFilterFid( featureId ))
				ret = f.next()

		else:
			IDs = [f.id() for f in layer.getFeatures(QgsFeatureRequest(rect))]

			if onlyIds:
				ret = IDs
			else:
				ret = []
				for featureId in IDs:
					f = layer.getFeatures(QgsFeatureRequest().setFilterFid( featureId ))
					ret.append( f )

		QApplication.restoreOverrideCursor()
		return ret


class PolygonDrawer(MapTool):

	class PolygonDrawer(MapTool.Drawer):
		def __init__(self, canvas):
			MapTool.Drawer.__init__(self, canvas, QGis.Polygon)

	def __init__(self, canvas=None):
		MapTool.__init__(self, self.PolygonDrawer, canvas)


class LineDrawer(MapTool):

	class LineDrawer(MapTool.Drawer):
		def __init__(self, canvas):
			MapTool.Drawer.__init__(self, canvas, QGis.Line)

	def __init__(self, canvas=None):
		MapTool.__init__(self, self.LineDrawer, canvas)