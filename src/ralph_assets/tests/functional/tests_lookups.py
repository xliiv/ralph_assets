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
from ralph_assets.tests.utils.assets import (
    BOAssetFactory,
    DCAssetFactory,
)
from ralph.ui.tests.global_utils import login_as_su


class BaseLookupsTest(TestCase):

    def setUp(self):
        self.client = login_as_su()

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

    def test_unlogged_user_lookup_permission(self):
        """
        - send request
        - check for 403
        """
        url = self._generate_url('ralph_assets.models', 'DeviceLookup')
        client = Client()
        response = client.get(url + '?term=test')
        self.assertEqual(response.status_code, 403)

    def test_logged_user_lookup_permission(self):
        """
        - sign in
        - send request
        - check for 200
        """
        url = self._generate_url('ralph_assets.models', 'DeviceLookup')
        response = self.client.get(url + '?term=test')
        self.assertEqual(response.status_code, 200)


class TestAssetLookup(BaseLookupsTest):

    def test_lookups_bo_and_dc(self):
        """
        - user type 'Model' in some ajax-selects field
        - user get assets with DC and BO type
        """
        number_of_assets = 3
        for _ in xrange(number_of_assets):
            BOAssetFactory()
            DCAssetFactory()

        url = self._generate_url('ralph_assets.models', 'AssetLookup')
        response = self.client.get(url + '?term=Model')
        self.assertEqual(
            len(json.loads(response.content)), number_of_assets * 2
        )


class TestLinkedDeviceNameLookup(BaseLookupsTest):

    def test_asset_found_by_barcode(self):
        barcode = 'test-barcode'
        DCAssetFactory(barcode=barcode)
        base_url = self._generate_url(
            'ralph_assets.models', 'LinkedDeviceNameLookup',
        )
        self._check_lookup_count(
            base_url, searched_term=barcode, expected_count=1
        )

    def test_asset_found_by_sn(self):
        sn = 'test-sn'
        DCAssetFactory(sn=sn)
        base_url = self._generate_url(
            'ralph_assets.models', 'LinkedDeviceNameLookup',
        )
        self._check_lookup_count(
            base_url, searched_term=sn, expected_count=1
        )

    def test_asset_found_by_hostname(self):
        hostname = 'blade-408-1-sw1.dc4.local'
        device = DeviceFactory(name=hostname)
        DCAssetFactory(device_info__ralph_device_id=device.id)
        base_url = self._generate_url(
            'ralph_assets.models', 'LinkedDeviceNameLookup',
        )
        self._check_lookup_count(
            base_url, searched_term=hostname, expected_count=1
        )

    def test_asset_found_by_device_hostname(self):
        hostname = 'blade-408-1-sw1.dc4.local'
        device = DeviceFactory(name=hostname)
        DCAssetFactory(device_info__ralph_device_id=device.id)
        base_url = self._generate_url(
            'ralph_assets.models', 'LinkedDeviceNameLookup',
        )
        self._check_lookup_count(
            base_url, searched_term=hostname, expected_count=1
        )
