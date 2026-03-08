# -*- coding: UTF-8 -*-
from collective.exportimport.export_content import ExportContent

import logging

logger = logging.getLogger(__name__)

TYPES_TO_EXPORT = [
    "Folder",
    "Document",
    "Event",
    "File",
    "Image",
    "Link",
    "News Item",
    "Topic",
    "Collection",
    # Custom dipartimenti types
    "HomePage",
    "Banner",
    "Channel",
    "Newsletter",
    "CorsiStudio",
    "Events",
    "AgendaEventi",
    "AgendaEvento",
    "AltaFormazione",
    "Ambito",
    "Collane",
    "Contacts",
    "Dottorati",
    "EasyForm",
    "GuidaOnline",
    "LanguageFolder",
    "Masters",
    "MediaGallery",
    "NewsRoom",
    "OverviewInternazionale",
    "Personale",
    "Pubblicazioni",
    "Ricerca",
    "ScuoleSpecializzazione",
    "SiteContainer",
    "SommarioAmbiti",
    "StrilloEvento",
    "StrilloNotizia",
    "Visiting",
]

# Content for test-migrations
PATHS_TO_EXPORT = []

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
        return item
