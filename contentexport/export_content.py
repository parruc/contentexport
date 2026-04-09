# -*- coding: UTF-8 -*-
import base64
import logging
from collections.abc import Mapping
from urllib.parse import urlparse

from collective.exportimport.export_content import ExportContent
from plone.app.textfield.interfaces import IRichTextValue
from plone.namedfile.file import NamedBlobFile, NamedBlobImage
from plone.restapi.interfaces import IJsonCompatible
from plone.tiles.data import ANNOTATIONS_KEY_PREFIX
from unibo.api.content import last_modifier
from unibo.tiles.field import TilesField
from z3c.relationfield.interfaces import IRelationValue
from zope.annotation.interfaces import IAnnotations
from plone.dexterity.utils import iterSchemata
from zope.interface import directlyProvidedBy
from zope.schema import getFieldsInOrder
from plone.formwidget.geolocation.geolocation import Geolocation

logger = logging.getLogger(__name__)

MARKER_INTERFACES_TO_EXPORT = ["unibo.mailup.interfaces.INewsletterFolder"]

ANNOTATIONS_TO_EXPORT = []

ANNOTATIONS_KEY = "exportimport.annotations"

MARKER_INTERFACES_KEY = "exportimport.marker_interfaces"

SUPPORTED_LANGUAGES = ("it", "en")

TILES_KEY = "exportimport.tiles_data"


class CustomExportContent(ExportContent):

    QUERY = {
    }

    DROP_PATHS = [
    ]

    DROP_UIDS = [
    ]

    def update_query(self, query):
        return query

    def export_marker_interfaces(self, item, obj):
        interfaces = [i.__identifier__ for i in directlyProvidedBy(obj) if i.__identifier__ in MARKER_INTERFACES_TO_EXPORT]
        if interfaces:
            item[MARKER_INTERFACES_KEY] = interfaces
        return item

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
        SITE_ROOT = "http://cms01:4081/dipartimenti/"
        RESOURCES = f"{SITE_ROOT}resources/"
        if item.get("@id") == RESOURCES:
            return None  # Skip this item entirely
        
        if item.get("@id") in (f"{RESOURCES}it", f"{RESOURCES}en"):
            item["@type"] = "LanguageFolder"

        if item.get("@id").startswith(f"{RESOURCES}it"):
            item["language"] = "it"
            item["@id"] = item["@id"].replace(f"{RESOURCES}it", f"{SITE_ROOT}it")
            if item["parent"]["@id"] == f"{RESOURCES}it":
                item["parent"]["@type"] = "LanguageFolder"
            item["parent"]["@id"] = item["parent"]["@id"].replace(f"{RESOURCES}it", f"{SITE_ROOT}it")
        
        if item.get("@id").startswith(f"{RESOURCES}en"):
            item["language"] = "en"
            item["@id"] = item["@id"].replace(f"{RESOURCES}en", f"{SITE_ROOT}en")
            if item["parent"]["@id"] == f"{RESOURCES}en":
                item["parent"]["@type"] = "LanguageFolder"
            item["parent"]["@id"] = item["parent"]["@id"].replace(f"{RESOURCES}en", f"{SITE_ROOT}en")

        modifier_id = last_modifier(obj)
        if modifier_id:
            item["last_modifier"] = modifier_id

        item_url = item.get("@id", "")
        path = urlparse(item_url).path if isinstance(item_url, str) else ""
        segments = [seg.lower() for seg in path.split("/") if seg]
        if len(segments) >= 3 and segments[2] in SUPPORTED_LANGUAGES:
            item["language"] = segments[2]
        else:
            logger.warning("Could not determine language for item with URL: %s", item_url)
        item = self.export_marker_interfaces(item, obj)
        item = self.handle_tiles(item, obj)
        return item

    def dict_hook_event(self, item, obj):
        """Used this to modify the serialized data after the event is fired.
        Return None if you want to skip this particular object.
        """
        item.pop("categoria")
        return item

    def dict_hook_strilloevento(self, item, obj):
        """Used this to modify the serialized data after the event is fired.
        Return None if you want to skip this particular object.
        """
        item.pop("categoria")
        return item

    def handle_tiles(self, item, obj):
        """Export tile annotation data from all TilesField fields on the object."""
        annotations = IAnnotations(obj, None)
        if annotations is None:
            return item

        tiles_data = {}

        for schema in iterSchemata(obj):
            for fieldname, field in getFieldsInOrder(schema):
                if not isinstance(field, TilesField):
                    continue
                tile_refs = getattr(obj, fieldname, None) or []
                for tile_ref in tile_refs:
                    # tile_ref format: @@{tile_type}/{tile_id}
                    try:
                        stripped = tile_ref.lstrip("@")
                        tile_type, tile_id = stripped.split("/", 1)
                        tile_id = tile_id.split("?")[0]
                    except (ValueError, AttributeError):
                        continue

                    if tile_type == "unibo.tiles.rss_eventi":
                        continue
                    annotation_key = "{}.{}".format(ANNOTATIONS_KEY_PREFIX, tile_id)
                    annotation = annotations.get(annotation_key)
                    if annotation is None:
                        continue

                    try:
                        serialized = {}
                        for key, value in annotation.items():
                            if key == "objects_dict":
                                serialized[key] = self._serialize_objects_dict(value)
                            else:
                                serialized[key] = self._safe_serialize(value)

                        serialized["__tile_type__"] = tile_type
                        tiles_data[tile_id] = serialized
                    except Exception:
                        logger.exception(
                            "Could not export tile %s (%s) on %s",
                            tile_id, tile_type, obj.absolute_url(),
                        )

        if tiles_data:
            item[TILES_KEY] = tiles_data

        return item

    def _serialize_objects_dict(self, objects_dict):
        """Serialize the objects_dict of a multi-object tile."""
        if not objects_dict:
            return {}

        result = {}
        for uid, obj in objects_dict.items():
            obj._p_activate()  # Ensure ghost is loaded from ZODB before reading __dict__
            obj_data = {}
            for attr, value in vars(obj).items():
                if attr.startswith("_"):
                    continue
                obj_data[attr] = self._safe_serialize(value)

            result[uid] = obj_data

        return result

    def _safe_serialize(self, value):
        """Recursively serialize a value, handling blobs and richtext at any depth."""
        if value is None:
            return None
        if IRichTextValue.providedBy(value):
            return value.raw if hasattr(value, "raw") else None
        if isinstance(value, (NamedBlobImage, NamedBlobFile)):
            return self._serialize_blob(value)
        if IRelationValue.providedBy(value):
            return value.to_object.UID() if value.to_object else None
        if Geolocation is not None and isinstance(value, Geolocation):
            return {"latitude": value.latitude, "longitude": value.longitude}
        if isinstance(value, Mapping):
            return {k: self._safe_serialize(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return type(value)(self._safe_serialize(v) for v in value)
        return IJsonCompatible(value, None)

    def _serialize_blob(self, value):
        """Serialize a NamedBlobImage or NamedBlobFile as base64."""
        if value is None:
            return None
        try:
            raw = value.data
        except Exception:
            raw = b""
        filename = value.filename or ""
        if isinstance(filename, bytes):
            filename = filename.decode("utf-8", errors="replace")
        return {
            "filename": filename,
            "content-type": value.contentType or "",
            "size": value.getSize(),
            "data": base64.b64encode(raw).decode("ascii"),
        }
