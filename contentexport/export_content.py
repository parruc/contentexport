# -*- coding: UTF-8 -*-
from collective.exportimport.export_content import ExportContent
from DateTime import DateTime

import logging

logger = logging.getLogger(__name__)

TYPES_TO_EXPORT = [
    "Event",
    "strilloevento",
]

# Content for test-migrations
PATHS_TO_EXPORT = ["/CUE/it/lectures-e-seminari"]

MARKER_INTERFACES_TO_EXPORT = []

ANNOTATIONS_TO_EXPORT = []

ANNOTATIONS_KEY = "exportimport.annotations"

MARKER_INTERFACES_KEY = "exportimport.marker_interfaces"


class CustomExportContent(ExportContent):

    QUERY = {
        'start': {'query': DateTime('2023-01-01'), 'range': 'max'}
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
        return item
