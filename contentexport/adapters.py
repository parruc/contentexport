from zope.interface import implementer
from zope.component import adapter
from plone.restapi.interfaces import IFieldSerializer
from plone.dexterity.interfaces import IDexterityContent
from plone.formwidget.geolocation.geolocation import Geolocation
from plone.formwidget.geolocation.field import GeolocationField
from zope.interface import Interface

from plone.restapi.serializer.dxfields import DefaultFieldSerializer

@implementer(IFieldSerializer)
@adapter(GeolocationField, IDexterityContent, Interface)
class GeolocationFieldSerializer(DefaultFieldSerializer):
    def __call__(self):
        value = self.get_value()

        if isinstance(value, Geolocation):
            return {
                "latitude": value.latitude,
                "longitude": value.longitude
            }

        return None  # or return json_compatible(value) if fallback is needed