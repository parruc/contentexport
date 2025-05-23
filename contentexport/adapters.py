from zope.interface import implementer
from zope.component import adapter
from plone.restapi.interfaces import ISerializeToJson
from plone.restapi.serializer.dx import SerializeToJson
from plone.app.contenttypes.interfaces import IEvent
from plone.formwidget.geolocation.geolocation import Geolocation

@implementer(ISerializeToJson)
@adapter(IEvent, Interface)
class CustomEventJSONSerializer(SerializeToJson):
    def __call__(self, include_items=True, exclude_fields=None, include_fields=None):
        data = super().__call__(
            include_items=include_items,
            exclude_fields=exclude_fields,
            include_fields=include_fields,
        )

        geo = getattr(self.context, "geolocation", None)
        if isinstance(geo, Geolocation):
            data["geolocation"] = {
                "latitude": geo.latitude,
                "longitude": geo.longitude,
            }

        return data