#/***************************************************************************
# rt_geosisma_offline
# 
# Gestione offline delle scede di vulnerabilita' di Geosisma
#                             -------------------
#        begin                : 2013-10-21
#        copyright            : (C) 2013 by Luigi Pirelli
#        email                : luipir@gmail.com
# ***************************************************************************/
# 
#/***************************************************************************
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or     *
# *   (at your option) any later version.                                   *
# *                                                                         *
# ***************************************************************************/

# CONFIGURATION
PLUGIN_UPLOAD = $(CURDIR)/plugin_upload.py

# Makefile for a PyQGIS plugin 

# translation
SOURCES = $(wildcard *.py)
#TRANSLATIONS = i18n/geosismaofflineexportdb_en.ts
TRANSLATIONS = 

# global

PLUGINNAME = rt_geosisma_offline

EXTRAS = incons/icon.png metadata.txt

UI_SOURCES=$(wildcard *.ui)
UI_FILES=$(patsubst %.ui,%_ui.py,$(UI_SOURCES))

RC_SOURCES=$(wildcard *.qrc)
RC_FILES=$(patsubst %.qrc,%_rc.py,$(RC_SOURCES))

HELP = help/build/html

default: compile

compile: $(UI_FILES) $(RC_FILES)

%_rc.py : %.qrc
	pyrcc4 -o $*_rc.py  $<

$(UI_FILES): %_ui.py: %.ui
	pyuic4 -o $@ $<

%.qm : %.ts
	lrelease $<

# The deploy  target only works on unix like operating system where
# the Python plugin directory is located at:
# $HOME/.qgis/python/plugins
deploy: compile doc transcompile
	mkdir -p $(HOME)/.qgis/python/plugins/$(PLUGINNAME)
	cp -vf $(PY_FILES) $(HOME)/.qgis/python/plugins/$(PLUGINNAME)
	cp -vf $(UI_FILES) $(HOME)/.qgis/python/plugins/$(PLUGINNAME)
	cp -vf $(RC_FILES) $(HOME)/.qgis/python/plugins/$(PLUGINNAME)
	cp -vf $(EXTRAS) $(HOME)/.qgis/python/plugins/$(PLUGINNAME)
	cp -vfr i18n $(HOME)/.qgis/python/plugins/$(PLUGINNAME)
	cp -vfr $(HELP) $(HOME)/.qgis/python/plugins/$(PLUGINNAME)/help

# The dclean target removes compiled python files from plugin directory
# also delets any .svn entry
dclean:
	find $(HOME)/.qgis/python/plugins/$(PLUGINNAME) -iname "*.pyc" -delete
	find $(HOME)/.qgis/python/plugins/$(PLUGINNAME) -iname ".svn" -prune -exec rm -Rf {} \;

# The derase deletes deployed plugin
derase:
	rm -Rf $(HOME)/.qgis/python/plugins/$(PLUGINNAME)

# The zip target deploys the plugin and creates a zip file with the deployed
# content. You can then upload the zip file on http://plugins.qgis.org
zip: deploy dclean 
	rm -f $(PLUGINNAME).zip
	cd $(HOME)/.qgis/python/plugins; zip -9r $(CURDIR)/$(PLUGINNAME).zip $(PLUGINNAME)

# Create a zip package of the plugin named $(PLUGINNAME).zip. 
# This requires use of git (your plugin development directory must be a 
# git repository).
# To use, pass a valid commit or tag as follows:
#   make package VERSION=Version_0.3.2
package: compile
		rm -f $(PLUGINNAME).zip
		git archive --prefix=$(PLUGINNAME)/ --format zip -o $(PLUGINNAME).zip $(VERSION)
		echo "Created package: $(PLUGINNAME).zip"

upload: zip
	$(PLUGIN_UPLOAD) $(PLUGINNAME).zip

# transup
# update .ts translation files
transup:
	pylupdate4 Makefile

# transcompile
# compile translation files into .qm binary format
transcompile: $(TRANSLATIONS:.ts=.qm)

# transclean
# deletes all .qm files
transclean:
	rm -f i18n/*.qm

clean:
	rm $(UI_FILES) $(RC_FILES)

# build documentation with sphinx
doc: 
	cd help; make html
