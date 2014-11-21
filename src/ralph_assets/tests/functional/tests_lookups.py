# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import base64
import cPickle
import json
from urllib import urlencode

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client
from ralph.discovery.tests.util import DeviceFactory
from ralph.ui.tests.global_utils import login_as_su

from ralph_assets.tests.utils.assets import (
    BOAssetFactory,
    DCAssetFactory,
)
from ralph_assets.tests.utils.licences import LicenceFactory


class BaseLookupsTest(TestCase):
    lookup = (None, None)

    def setUp(self):
        self.client = login_as_su()
        self.base_url = self._generate_url(*self.lookup)

    def _generate_url(self, *lookup):
        channel = base64.b64encode(cPickle.dumps(lookup))
        return reverse('ajax_lookup', kwargs={'channel': channel})

    def _check_lookup_count(self, base_url, searched_term, expected_count):
        full_url = "{}?{}".format(base_url, urlencode({
            'term': searched_term,
        }))
        response = self.client.get(full_url)
        self.assertEqual(
            len(json.loads(response.content)), expected_count,
        )


class TestPerms(BaseLookupsTest):
    lookup = ('ralph_assets.models', 'DeviceLookup')

    def test_unlogged_user_lookup_permission(self):
        """
        - send request
        - check for 403
        """
        client = Client()
        response = client.get(self.base_url + '?term=test')
        self.assertEqual(response.status_code, 403)

    def test_logged_user_lookup_permission(self):
        """
        - sign in
        - send request
        - check for 200
        """
        response = self.client.get(self.base_url + '?term=test')
        self.assertEqual(response.status_code, 200)


class TestFreeLicenceLookup(BaseLookupsTest):
    lookup = ('ralph_assets.models', 'FreeLicenceLookup')

    def test_licence_found_by_category_name(self):
        licence = LicenceFactory()
        self._check_lookup_count(
            self.base_url,
            searched_term=licence.software_category.name,
            expected_count=1,
        )


class TestAssetLookup(BaseLookupsTest):
    lookup = ('ralph_assets.models', 'AssetLookup')

    def test_lookups_bo_and_dc(self):
        """
        - user type 'Model' in some ajax-selects field
        - user get assets with DC and BO type
        """
        number_of_assets = 3
        for _ in xrange(number_of_assets):
            BOAssetFactory()
            DCAssetFactory()
        self._check_lookup_count(
            self.base_url,
            searched_term='Model',
            expected_count=2 * number_of_assets,
        )


class TestLinkedDeviceNameLookup(BaseLookupsTest):
    lookup = ('ralph_assets.models', 'LinkedDeviceNameLookup')

    def test_asset_found_by_barcode(self):
        barcode = 'test-barcode'
        DCAssetFactory(barcode=barcode)
        self._check_lookup_count(
            self.base_url, searched_term=barcode, expected_count=1
        )

    def test_asset_found_by_sn(self):
        sn = 'test-sn'
        DCAssetFactory(sn=sn)
        self._check_lookup_count(
            self.base_url, searched_term=sn, expected_count=1
        )

    def test_asset_found_by_hostname(self):
        hostname = 'blade-408-1-sw1.dc4.local'
        device = DeviceFactory(name=hostname)
        DCAssetFactory(device_info__ralph_device_id=device.id)
        self._check_lookup_count(
            self.base_url, searched_term=hostname, expected_count=1
        )

    def test_asset_found_by_device_hostname(self):
        hostname = 'blade-408-1-sw1.dc4.local'
        device = DeviceFactory(name=hostname)
        DCAssetFactory(device_info__ralph_device_id=device.id)
        self._check_lookup_count(
            self.base_url, searched_term=hostname, expected_count=1
        )
