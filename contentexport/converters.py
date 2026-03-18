# -*- coding: UTF-8 -*-
from plone.restapi.interfaces import IJsonCompatible
from unibo.z3cform.fields.summary.field import AutomaticSummary
from zope.component import adapter
from zope.interface import implementer

import json


@adapter(AutomaticSummary)
@implementer(IJsonCompatible)
def automaticsummary_converter(value):
    """Convert an AutomaticSummary object to a JSON-compatible dict."""
    if value is None:
        return None
    items = value.items
    if items is None:
        return {"items": None}
    # items is a JSON string or legacy format; parse it to ensure clean output
    try:
        parsed = json.loads(items)
    except (json.JSONDecodeError, TypeError):
        parsed = items
    return {"items": parsed}
