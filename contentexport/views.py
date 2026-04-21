# -*- coding: UTF-8 -*-
from contentexport.interfaces import IContentexportLayer
from plone import api
from Products.CMFPlone.utils import get_installer
from Products.Five import BrowserView
from zope.interface import alsoProvides

import logging

logger = logging.getLogger(__name__)

# List of portal types to export, empty list means all types
TYPES_TO_EXPORT = [
    "Folder",
    "Document",
    # "Event",
    "File",
    "Image",
    "Link",
    "News Item",
    "Topic",
    "Collection",
    # Custom dipartimenti types
    "HomePage",
    "Channel",
    "Newsletter",
    "CorsiStudio",
    # "Events",
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
    # "StrilloEvento",
    "StrilloNotizia",
    "Visiting",
]

PATHS_TO_EXPORT = ["/dipartimenti"]


class ExportAll(BrowserView):
    def __call__(self):
        request = self.request
        if not request.form.get("form.submitted", False):
            return self.index()

        installer = get_installer(api.portal.get())
        if not installer.is_product_installed("contentexport"):
            installer.install_product("contentexport")
        alsoProvides(request, IContentexportLayer)

        portal = api.portal.get()

        export_name = "export_content"
        logger.info("Start {}".format(export_name))
        for path in PATHS_TO_EXPORT:
            logger.info("Exporting content under path: {}".format(path))
            view = api.content.get_view(export_name, portal, request)
            request.form["form.submitted"] = True
            view(
                portal_type=TYPES_TO_EXPORT,
                path=path,
                # 0=As download urls, 1=As base-64 encoded strings, 2=As blob paths
                include_blobs=1,
                # 0=Download to local machine, 1=Download to server, 2=Save each item as a separate file on the server
                download_to_server=1,
                migration=True,
            )
            logger.info("Finished exporting content under path: {}".format(path))
        logger.info("Finished {}".format(export_name))

        other_exports = [
            "export_relations",
            "export_members",
            "export_translations",
            "export_localroles",
            "export_ordering",
            "export_defaultpages",
            "export_redirects",
        ]
        for export_name in other_exports:
            export_view = api.content.get_view(export_name, portal, request)
            request.form["form.submitted"] = True
            # store each result in var/instance/export_xxx.json
            export_view(download_to_server=True)

        logger.info("Finished export_all")
        # Important! Redirect to prevent infinite export loop :)
        return self.request.response.redirect(self.context.absolute_url())
