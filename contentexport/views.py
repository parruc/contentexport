# -*- coding: UTF-8 -*-
from collective.exportimport.export_other import ExportMembers
from contentexport.interfaces import IContentexportLayer
from plone import api
from plone.restapi.serializer.converters import json_compatible
from Products.CMFPlone.utils import get_installer
from Products.Five import BrowserView
from zope.interface import alsoProvides

import logging

logger = logging.getLogger(__name__)

# List of portal types to export, empty list means all types
TYPES_TO_EXPORT = [
    "Folder",
    "Document",
    "File",
    "Image",
    "Link",
    "News Item",
    "Channel",
    "Newsletter",
    "CorsiStudio",
    "AgendaEventi",
    "AgendaEvento",
    "AltaFormazione",
    "Ambito",
    "Collane",
    "Dottorati",
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
            # "export_members" skipped: with LDAP, acl.searchUsers() dumps
            # the entire directory. @@export_groups below exports only the
            # local groups (incl. their LDAP members as plain principal ids).
            "export_groups",
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


class ExportGroups(ExportMembers):
    """Export groups without members.

    @@export_members would dump the entire LDAP directory through
    acl.searchUsers(), so it cannot be used here. Only groups stored in
    the local source_groups plugin are exported (the sharing groups
    redattore.<uid>, referente.<uid>, newslettermanager.<uid> live
    there); their LDAP members are kept as plain principal ids.
    The JSON keeps the @@import_members structure, with "members" empty,
    so the standard importer can load it unchanged.
    """

    def __init__(self, context, request):
        super(ExportGroups, self).__init__(context, request)
        self.title = u"Export groups"

    def __call__(self, download_to_server=False):
        self.download_to_server = download_to_server
        if not self.request.form.get("form.submitted", False):
            return self.index()

        logger.info(u"Exporting groups...")
        data = {"groups": self.export_groups(), "members": []}
        logger.info(u"Exported {} groups".format(len(data["groups"])))
        self.download(data)

    def export_groups(self):
        # Enumerate only the local groups plugin instead of
        # api.group.get_groups(), which would also query LDAP.
        acl = api.portal.get_tool("acl_users")
        data = []
        for info in acl.source_groups.enumerateGroups():
            if info["id"] in self.AUTO_GROUPS:
                continue
            group = api.group.get(info["id"])
            if group is None:
                continue
            item = {"groupid": group.id}
            item["roles"] = [
                i
                for i in api.group.get_roles(group=group)
                if i not in self.AUTO_ROLES
            ]
            item["groups"] = [
                i.id
                for i in api.group.get_groups(user=group)
                if i.id not in self.AUTO_GROUPS
            ]
            for prop in group.getProperties():
                item[prop] = json_compatible(group.getProperty(prop))
            # export all principals (incl. ldap-users)
            item["principals"] = group.getGroup().getMemberIds()
            data.append(item)
        return data
