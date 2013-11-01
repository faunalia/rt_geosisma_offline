# -*- coding: utf-8 -*-

def classFactory(iface):
    from GeosismaOffline import GeosismaOffline
    return GeosismaOffline(iface)
