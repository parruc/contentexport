# -*- coding: UTF-8 -*-
import base64
from collective.exportimport.export_content import ExportContent

import logging

logger = logging.getLogger(__name__)

# Content for test-migrations
PATHS_TO_EXPORT = ["/magazine/archivio", "/magazine/comunicati-stampa"]

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
        item["tiles"] = self.extract_tiles(obj)
        item["is_folderish"] = False
        return item

    def extract_image(self, subobj):
        image_data = subobj.image.data
        encoded_data = base64.b64encode(image_data)
        return {
            "title": subobj.title,
            "id": subobj.id,
            "description": subobj.description,
            "image": encoded_data.decode('utf-8'),
            "old_type": subobj.portal_type
        }

    def extract_link(self, subobj):
        return {"title": subobj.title,
                "id": subobj.id,
                "old_type": subobj.portal_type,
                "link": subobj.remoteUrl,
        }

    def extract_inrete(self, subobj):
        return self.extract_link(subobj)

    def extract_file(self, subobj):
        file_data = subobj.file.data  # bytes of the file
        encoded_data = base64.b64encode(file_data)
        return {"title": subobj.title,
                "description": subobj.description,
                "id": subobj.id,
                "old_type": subobj.portal_type,
                "file": encoded_data.decode('utf-8')
        }

    def extract_tiles(self, obj):
        tiles = []
        for subbrain in obj.getFolderContents():
            subobj = subbrain.getObject()
            if subobj.portal_type == "File":
                tiles.append(self.extract_file(subobj))
            elif subobj.portal_type == "Image":
                tiles.append(self.extract_image(subobj))
            elif subobj.portal_type == "Link":
                tiles.append(self.extract_link(subobj))
            elif subobj.portal_type == "inrete":
                tiles.append(self.extract_inrete(subobj))
            else:
                logger.error("Unsupported portal_type "+ subobj.portal_type + " for item " + obj.absolute_url())
        return tiles


    def dict_hook_articolo(self, item, obj):
        """Used this to modify the serialized data for articles.
        Return None if you want to skip this particular object.
        """
        item["@type"] = "Articolo"
        item["alt"] = item.pop("titolo_immagine")
        item["image"] = item.pop("immagine", None)
        item["brief"] = item.pop("testo", None)
        item.pop("canale", None)
        item.pop("rubrica", None)
        item.pop("event", None)
        item.pop("escludi_dal_portale", None)
        return item

    def dict_hook_fotoracconto(self, item, obj):
        """Used this to modify the serialized data for fotoracconti.
        Return None if you want to skip this particular object.
        """
        item["@type"] = "Articolo"
        item["image"] = item.pop("immagine", None)
        item["brief"] = item.pop("testo", None)
        item["alt"] = item.pop("titolo_immagine")
        item.pop("articoli_correlati", None)
        return item

    def dict_hook_comunicatostampa(self, item, obj):
        """Used this to modify the serialized data for comunicati stampa.
        Return None if you want to skip this particular object.
        """
        item["@type"] = "Comunicato stampa"
        return item
