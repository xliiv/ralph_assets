# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.test import TestCase

from ralph.account.models import BoundPerm, Perm
from ralph.ui.tests.global_utils import (
    login_as_su,
)
from ralph_assets.tests.utils import (
    UserFactory,
    login_as_user,
)


class ACLInheritanceTest(TestCase):

    def test_all_views_inherits_acls(self):
        """
        - get all views from url.py except these urls:
            - api (until it clarifies)
            - redirections
        - assert if each view has ACLClass in mro
        """
        from ralph_assets import urls
        from ralph_assets.views.base import ACLGateway
        excluded_urls_by_regexp = [
            '^api/'  # skip it until api authen./author. is resolved
        ]
        for urlpattern in urls.urlpatterns:
            if urlpattern._regex in excluded_urls_by_regexp:
                continue
            elif urlpattern.callback.func_name == 'RedirectView':
                continue
            module_name = urlpattern._callback.__module__
            class_name = urlpattern._callback.__name__
            imported_module = __import__(module_name, fromlist=[class_name])
            found_class = getattr(imported_module, class_name)
            msg = "View '{}' doesn't inherit from acl class".format(
                '.'.join([module_name, class_name])
            )
            self.assertIn(ACLGateway, found_class.__mro__, msg)


class TestAssetModulePerms(TestCase):
    def setUp(self):
        self.mode = 'dc'
        self.assets_module_url = reverse(
            'asset_search',  kwargs={'mode': self.mode}
        )

    def test_superuser_has_access(self):
        su_client = login_as_su()
        response = su_client.get(self.assets_module_url)
        self.assertEqual(response.status_code, 200)

    def test_user_has_no_access(self):
        no_access_user = UserFactory(
            is_staff=False,
            is_superuser=False,
        )
        no_access_user.get_profile().boundperm_set.all().delete()
        client = login_as_user(no_access_user)
        response = client.get(self.assets_module_url, follow=True)
        self.assertEqual(response.status_code, 403)

    def test_user_with_bound_perms_has_access(self):
        user_with_access = UserFactory(
            is_staff=False,
            is_superuser=False,
        )
        BoundPerm(
            profile=user_with_access.get_profile(),
            perm=Perm.has_assets_access,
        ).save()

        client = login_as_user(user_with_access)
        response = client.get(self.assets_module_url, follow=True)
        self.assertEqual(response.status_code, 200)
