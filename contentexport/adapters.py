from zope.interface import implementer
from zope.component import adapter
from plone.dexterity.interfaces import IDexterityContent
from plone.formwidget.geolocation.geolocation import Geolocation
from plone.formwidget.geolocation.field import GeolocationField
from zope.interface import Interface
from plone.restapi.interfaces import IFieldSerializer

from plone.restapi.serializer.dxfields import DefaultFieldSerializer
from plone.exportimport.serializer import CollectionFieldSerializer


@implementer(IFieldSerializer)
class CollectionFieldSerializer(CollectionFieldSerializer):

    def get_value(self, default=None):
        if self.field.__name__ in ["vedi_anche"]:
            print("Field ignored:", self.field.__name__)
            return None
        return getattr(self.field.interface(self.context), self.field.__name__, default)


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


