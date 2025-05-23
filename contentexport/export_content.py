# -*- coding: UTF-8 -*-
from collective.exportimport.export_content import ExportContent
from plone.formwidget.geolocation.geolocation import Geolocation
from DateTime import DateTime

import logging

logger = logging.getLogger(__name__)

TYPES_TO_EXPORT = []

# Content for test-migrations
PATHS_TO_EXPORT = ["/CUE/it/lectures-e-seminari"]

MARKER_INTERFACES_TO_EXPORT = []

ANNOTATIONS_TO_EXPORT = []

IGNORED_FIELDS = [
    'vedi_anche',
    'contacts',
    # aggiungi tutti i campi del behavior IVediache
]

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

    def serialize_field_value(self, obj, fieldname, value):
        # Converti Geolocation in dizionario JSON-compatibile
        if isinstance(value, Geolocation):
            return {
                'latitude': value.latitude,
                'longitude': value.longitude
            }

        # Tutto il resto usa il metodo originale
        return super(CustomExportContent, self).serialize_field_value(obj, fieldname, value)

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
        for key, value in item.get('fields', {}).items():
            if key in IGNORED_FIELDS:
                del item['fields'][key]
            if key == "geolocation":
                item['fields'][key] = {
                    'latitude': value.latitude,
                    'longitude': value.longitude,
                }
        return item
