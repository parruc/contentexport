# -*- coding: UTF-8 -*-
from collective.exportimport.export_other import ExportMembers
from contentexport.interfaces import IContentexportLayer
from plone import api
from plone.restapi.serializer.converters import json_compatible
from Products.CMFPlone.utils import get_installer
from Products.Five import BrowserView
from uuid import uuid4
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
            # both of these are local-only variants: the stock @@export_members
            # enumerates acl.searchUsers(), which dumps the whole AD directory
            "export_groups",
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


class ExportLocalMembers(ExportMembers):
    """Materialise the principals the local groups reference.

    Registered as @@export_members on the contentexport layer, so it shadows
    the stock view (which enumerates acl.searchUsers() and would walk all of
    AD) while still writing the export_members.json the importer looks for.

    The editors only ever existed as member ids inside the local groups,
    resolved through LDAP; nothing about them is in source_users. The new site
    has no LDAP, so @@oauth2-login cannot find them unless they are migrated as
    real Plone users. Their id is the userPrincipalName, i.e. the email, so no
    directory lookup is needed to build the member records.
    """

    def __init__(self, context, request):
        super(ExportLocalMembers, self).__init__(context, request)
        self.title = u"Export local members"

    def __call__(self, download_to_server=False):
        self.download_to_server = download_to_server
        if not self.request.form.get("form.submitted", False):
            return self.index()

        logger.info(u"Exporting local members...")
        # groups come from @@export_groups, which is imported before the content
        data = {"groups": [], "members": self.export_members()}
        logger.info(u"Exported {} local members".format(len(data["members"])))
        self.download(data)

    def export_members(self):
        acl = api.portal.get_tool("acl_users")
        local_group_ids = {i["id"] for i in acl.source_groups.enumerateGroups()}

        groups_by_member = {}
        for groupid in local_group_ids:
            if groupid in self.AUTO_GROUPS:
                continue
            for principal in acl.source_groups.getGroupMembers(groupid):
                groups_by_member.setdefault(principal, []).append(groupid)

        data = []
        for principal, groups in sorted(groups_by_member.items()):
            if principal in local_group_ids:
                # nested group, not a person
                continue
            data.append(
                {
                    "username": principal,
                    # the principal id is the userPrincipalName; @@import_members
                    # silently skips members without an email
                    "email": principal,
                    # nobody authenticates with a password, entraid does that,
                    # but addMember runs testPasswordValidity on it
                    "password": uuid4().hex,
                    # roles come with the groups
                    "roles": [],
                    "groups": sorted(groups),
                    "fullname": self._fullname(principal),
                    "listed": True,
                }
            )
        return data

    def _fullname(self, principal):
        """Best effort: the only per-principal LDAP lookup in this export."""
        try:
            member = self.pms.getMemberById(principal)
        except Exception:
            logger.exception("Could not look up %s", principal)
            return u""
        if member is None:
            return u""
        fullname = member.getProperty("fullname", "") or u""
        if isinstance(fullname, bytes):
            fullname = fullname.decode("utf-8", "replace")
        return fullname
