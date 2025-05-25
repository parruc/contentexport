# -*- coding: UTF-8 -*-
from collective.exportimport.export_content import ExportContent
from z3c.relationfield.interfaces import IRelationChoice
from z3c.relationfield.interfaces import IRelationList
from zope.schema import getFields
from plone.dexterity.utils import iterSchemata
from base64 import b64encode

import logging

logger = logging.getLogger(__name__)

TYPES_TO_EXPORT = []

# Content for test-migrations
PATHS_TO_EXPORT = ["/CUE/it/lectures-e-seminari"]

MARKER_INTERFACES_TO_EXPORT = []

ANNOTATIONS_TO_EXPORT = []

ANNOTATIONS_KEY = "exportimport.annotations"

MARKER_INTERFACES_KEY = "exportimport.marker_interfaces"


class CustomExportContent(ExportContent):

    QUERY = {
    }

    DROP_PATHS = [
    ]

    DROP_UIDS = [
    ]

    def update_query(self, query):
        return query

    def update(self):
        self.portal_type = self.portal_type or TYPES_TO_EXPORT

    def global_obj_hook(self, obj):
        """Used this to inspect the content item before serialisation data.
        Bad: Changing the content-item is a bad idea.
        Good: Return None if you want to skip this particular object.
        """
        return obj

    def global_dict_hook(self, item, obj):
        """Used this to modify the serialized data.
        Return None if you want to skip this particular object.
        """
        if item["start"] > "2023":
            return None
        return item

    def update_data_for_migration(self, item, obj):
        for schema in iterSchemata(obj):
            for name, field in getFields(schema).items():
                if IRelationChoice.providedBy(field) or IRelationList.providedBy(
                    field
                ):
                    if name == "leadimage":
                        leadimage = obj.leadimage.to_object
                        if leadimage:
                            item["leadimage"] = b64encode(leadimage.image.data).decode("utf-8")
        return super(CustomExportContent, self).update_data_for_migration(item, obj)
