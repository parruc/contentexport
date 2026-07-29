# -*- coding: UTF-8 -*-
"""Unit tests for ExportLocalMembers.

No Plone site is needed: acl_users and portal_membership are stubbed, which
is also the point -- the export must not reach out to LDAP for anything but
the fullname.

Run:  bin/zopepy -m unittest discover -s src/contentexport -t src/contentexport
"""

import unittest

from contentexport import views


class FakeGroupsPlugin(object):
    """Stand-in for acl_users.source_groups (the local groups plugin)."""

    def __init__(self, groups):
        self._groups = groups

    def enumerateGroups(self):
        return [{"id": gid} for gid in self._groups]

    def getGroupMembers(self, groupid):
        return tuple(self._groups[groupid])


class FakeMember(object):
    def __init__(self, fullname):
        self._fullname = fullname

    def getProperty(self, name, default=None):
        if name == "fullname":
            return self._fullname
        return default


class FakeMembership(object):
    def __init__(self, fullnames=None, raises=False):
        self._fullnames = fullnames or {}
        self._raises = raises

    def getMemberById(self, principal):
        if self._raises:
            raise RuntimeError("LDAP is down")
        if principal not in self._fullnames:
            return None
        return FakeMember(self._fullnames[principal])


class ExportLocalMembersTests(unittest.TestCase):

    def _view(self, groups, fullnames=None, raises=False):
        acl = type("FakeACL", (object,), {})()
        acl.source_groups = FakeGroupsPlugin(groups)
        tools = {
            "acl_users": acl,
            "portal_membership": FakeMembership(fullnames, raises),
        }
        self._orig_get_tool = views.api.portal.get_tool
        views.api.portal.get_tool = lambda name: tools[name]
        self.addCleanup(setattr, views.api.portal, "get_tool", self._orig_get_tool)
        return views.ExportLocalMembers(None, None)

    def test_every_group_member_becomes_a_member_record(self):
        view = self._view({"redattore.abc": ["mario@unibo.it", "anna@unibo.it"]})
        members = view.export_members()
        self.assertEqual(
            [i["username"] for i in members], ["anna@unibo.it", "mario@unibo.it"]
        )

    def test_email_is_the_principal_id(self):
        # import_members silently skips members with an empty email
        view = self._view({"referente.abc": ["mario@unibo.it"]})
        member = view.export_members()[0]
        self.assertEqual(member["email"], "mario@unibo.it")

    def test_password_is_set(self):
        # addMember runs testPasswordValidity, an empty password is rejected
        view = self._view({"referente.abc": ["mario@unibo.it"]})
        member = view.export_members()[0]
        self.assertTrue(member["password"])

    def test_passwords_are_not_shared_between_members(self):
        view = self._view({"referente.abc": ["a@unibo.it", "b@unibo.it"]})
        passwords = {i["password"] for i in view.export_members()}
        self.assertEqual(len(passwords), 2)

    def test_all_groups_of_a_member_are_collected(self):
        view = self._view(
            {
                "redattore.abc": ["mario@unibo.it"],
                "referente.abc": ["mario@unibo.it"],
                "newslettermanager.xyz": ["mario@unibo.it"],
            }
        )
        member = view.export_members()[0]
        self.assertEqual(
            member["groups"],
            ["newslettermanager.xyz", "redattore.abc", "referente.abc"],
        )

    def test_roles_are_left_to_the_groups(self):
        view = self._view({"redattore.abc": ["mario@unibo.it"]})
        self.assertEqual(view.export_members()[0]["roles"], [])

    def test_automatic_groups_are_ignored(self):
        view = self._view(
            {
                "AuthenticatedUsers": ["everybody@unibo.it"],
                "redattore.abc": ["mario@unibo.it"],
            }
        )
        self.assertEqual(
            [i["username"] for i in view.export_members()], ["mario@unibo.it"]
        )

    def test_nested_groups_are_not_exported_as_people(self):
        view = self._view(
            {
                "redattore.abc": ["mario@unibo.it", "some.group"],
                "some.group": ["anna@unibo.it"],
            }
        )
        self.assertEqual(
            sorted(i["username"] for i in view.export_members()),
            ["anna@unibo.it", "mario@unibo.it"],
        )

    def test_fullname_comes_from_the_member_properties(self):
        view = self._view(
            {"redattore.abc": ["mario@unibo.it"]},
            fullnames={"mario@unibo.it": u"Mario Rossi"},
        )
        self.assertEqual(view.export_members()[0]["fullname"], u"Mario Rossi")

    def test_unknown_member_gets_an_empty_fullname(self):
        view = self._view({"redattore.abc": ["ghost@unibo.it"]})
        self.assertEqual(view.export_members()[0]["fullname"], u"")

    def test_bytes_fullname_is_decoded(self):
        # LDAP hands back bytes for some attributes
        view = self._view(
            {"redattore.abc": ["mario@unibo.it"]},
            fullnames={"mario@unibo.it": b"Mario Rossi"},
        )
        self.assertEqual(view.export_members()[0]["fullname"], u"Mario Rossi")

    def test_a_failing_lookup_does_not_abort_the_export(self):
        view = self._view({"redattore.abc": ["mario@unibo.it"]}, raises=True)
        members = view.export_members()
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0]["fullname"], u"")


if __name__ == "__main__":
    unittest.main()

