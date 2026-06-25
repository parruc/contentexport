# -*- coding: UTF-8 -*-
import re
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

    EXPORT_DOMAIN = "http://cms01:4081"

    QUERY = {
    }

    DROP_PATHS = [
        "/dipartimenti/resources",
    ]

    DROP_PATHS_RE = [
        rf"^{EXPORT_DOMAIN}/dipartimenti/.*?/it/biblioteca($|/.*)",
        rf"^{EXPORT_DOMAIN}/dipartimenti/.*?/en/library($|/.*)",
    ]

    DROP_UIDS = [
    ]

    RENAME_PATHS = {
        rf"^{EXPORT_DOMAIN}/dipartimenti/.*?/it/didattica($|/.*)": {"title": "Studiare", "id": "studiare"},
        rf"^{EXPORT_DOMAIN}/dipartimenti/.*?/en/teaching($|/.*)": {"title": "Study", "id": "study"},
        rf"^{EXPORT_DOMAIN}/dipartimenti/.*?/it/notizie($|/.*)": {"title": "News", "id": "news"},
        rf"^{EXPORT_DOMAIN}/dipartimenti/.*?/en/agenda-events($|/.*)": {"title": "Events", "id": "events"},
        rf"^{EXPORT_DOMAIN}/dipartimenti/.*?/it/agenda-eventi($|/.*)": {"title": "Eventi", "id": "eventi"},
    }

    DROP_TILES = [
        "eod.tiles.slides",
        "eod.tiles.links_attachments",
        "eod.tiles.richtext",
        "eod.tiles.video",
        "eod.tiles.map",
        "eod.tiles.album",
        "unibo.tiles.contatti",
        "unibo.tiles.summary_link",
        "unibo.tiles.rss_eventi",
        "unibo.tiles.banners",
        "unibo.tiles.eventiricerca",
        "unibo.tiles.multi.banners",
        "unibo.tiles.multi.galleria",
        "unibo.tiles.multi.hp_head",
        "unibo.tiles.multi.avvisi",
        "unibo.tiles.notizie",
        "unibo.tiles.tessera",
        "unibo.tiles.dipartimenti.tessera",
    ]

    REPLACE_TILES = {
        "unibo.tiles.lancio_ambiti": "unibo.tiles.lancio_ricerca",
        "unibo.tiles.notiziehp": "unibo.tiles.notizie",
        "unibo.tiles.eventihp": "unibo.tiles.eventi",
        "unibo.tiles.multi.avvisi": "unibo.tiles.ultimora",
        "unibo.tiles.multi.links_attachments": "unibo.tiles.links_attachments",
        "unibo.tiles.multi.summary_link": "unibo.tiles.summary_link",
        "unibo.tiles.multi.links": "unibo.tiles.links",
        "unibo.tiles.multi.map_multipoint": "unibo.tiles.map_multipoint",
        "unibo.tiles.multi.album": "unibo.tiles.album",
        "unibo.tiles.multi.contacts": "unibo.tiles.contacts",
        "unibo.tiles.multi.infografica": "unibo.tiles.infografica",
        "unibo.tiles.multi.lanci": "unibo.tiles.lanci",
        "unibo.tiles.multi.focus": "unibo.tiles.focus",
        "unibo.tiles.multi.media_gallery_video": "unibo.tiles.media_gallery_video",
        "unibo.tiles.multi.linkedimageattachment": "unibo.tiles.linkedimageattachment",
    }

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

        for drop_path_re in self.DROP_PATHS_RE:
            if re.match(drop_path_re, item.get("@id", "")):
                return None
        
        for rename_path_re, replacement in self.RENAME_PATHS_RE.items():
            if re.match(rename_path_re, item.get("@id", "")):
                item.update(replacement)
                break

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
                new_tile_refs =[]
                tile_refs = getattr(obj, fieldname, None) or []
                for tile_ref in tile_refs:
                    # tile_ref format: @@{tile_type}/{tile_id}
                    try:
                        stripped = tile_ref.lstrip("@")
                        tile_type, tile_id = stripped.split("/", 1)
                        tile_id = tile_id.split("?")[0]
                    except (ValueError, AttributeError) as exception:
                        logger.error("Error parsing tile reference '%s': %s", tile_ref, exception)
                        continue

                    if tile_type in self.DROP_TILES:
                        continue

                    if tile_type in self.REPLACE_TILES:
                        tile_type = self.REPLACE_TILES[tile_type]

                    new_tile_refs.append("@@{}/{}".format(tile_type, tile_id))

                    annotation_key = "{}.{}".format(ANNOTATIONS_KEY_PREFIX, tile_id)
                    annotation = annotations.get(annotation_key)
                    if annotation is None:
                        tiles_data[tile_id] = {"__tile_type__": tile_type}
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
                item[fieldname] = new_tile_refs

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
