from zope.interface import implementer
from zope.component import adapter
from plone.dexterity.interfaces import IDexterityContent
from plone.formwidget.geolocation.geolocation import Geolocation
from plone.formwidget.geolocation.field import GeolocationField
from zope.interface import Interface
from plone.restapi.interfaces import IFieldSerializer
from z3c.relationfield.interfaces import IRelation

from plone.restapi.serializer.dxfields import DefaultFieldSerializer
from collective.exportimport.serializer import CollectionFieldSerializer


@implementer(IFieldSerializer)
class CollectionFieldSerializer(CollectionFieldSerializer):

    def get_value(self, default=None):
        if self.field.__name__ == "inrete":
            if not self.context.inrete:
                return []
            return [{"title": l.title, "link": l.link} for l in self.context.inrete]
        return getattr(self.field.interface(self.context), self.field.__name__, default)
