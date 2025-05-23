# -*- coding: UTF-8 -*-
from plone.theme.interfaces import IDefaultPloneLayer
from collective.exportimport.interfaces import IMigrationMarker


class IContentexportLayer(IMigrationMarker, IDefaultPloneLayer):
    """Marker interface that defines a Zope 3 browser layer.
    """
