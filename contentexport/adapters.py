from collective.exportimport.interfaces import IFieldConverter
from zope.component import adapter
from zope.interface import implementer
from plone.formwidget.geolocation.geolocation import Geolocation

@implementer(IFieldConverter)
@adapter(Geolocation)
class GeolocationConverter(object):
    def __init__(self, value):
        self.value = value

    def __call__(self):
        if self.value is None:
            return None
        return {
            'latitude': self.value.latitude,
            'longitude': self.value.longitude,
        }