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
    DataCenterFactory,
    ServerRoomFactory,
    RackFactory,
)
from ralph_assets.tests.utils.licences import (
    LicenceAssetFactory,
    LicenceUserFactory,
    LicenceFactory,
)


class BaseLookupsTest(TestCase):
    lookup = (None, None)

    def setUp(self):
        self.client = login_as_su()
        self.base_url = self._generate_url(*self.lookup)

    def _generate_url(self, *lookup):
        channel = base64.b64encode(cPickle.dumps(lookup))
        return reverse('ajax_lookup', kwargs={'channel': channel})

    def _get_lookup_url(self, base_url, searched_term):
        return "{}?{}".format(base_url, urlencode({
            'term': searched_term,
        }))

    def _get_lookup_results(self, lookup_url):
        response = self.client.get(lookup_url)
        return json.loads(response.content)

    def _check_lookup_count(self, base_url, searched_term, expected_count):
        lookup_url = self._get_lookup_url(base_url, searched_term)
        jsoned = self._get_lookup_results(lookup_url)
        self.assertEqual(len(jsoned), expected_count)


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

    def test_licence_found_by_niw(self):
        licence = LicenceFactory()
        self._check_lookup_count(
            self.base_url, searched_term=licence.niw, expected_count=1,
        )

    def test_licence_not_found_when_all_assigned(self):
        BOUGHT = 5
        licence = LicenceFactory(number_bought=BOUGHT)
        licence_asset = LicenceAssetFactory(licence=licence, quantity=BOUGHT)
        self._check_lookup_count(
            self.base_url, searched_term=licence_asset.licence.niw,
            expected_count=0,
        )

    def test_licence_found_when_assigned_to_user(self):
        BOUGHT = 5
        licence = LicenceFactory(number_bought=BOUGHT)
        licence_asset = LicenceAssetFactory(
            licence=licence, quantity=2,
        )
        LicenceUserFactory(licence=licence, quantity=2)
        self._check_lookup_count(
            self.base_url, searched_term=licence_asset.licence.niw,
            expected_count=1,
        )

    def test_licence_found_when_no_assiging_to_user(self):
        BOUGHT = 5
        licence = LicenceFactory(number_bought=BOUGHT)
        licence_asset = LicenceAssetFactory(
            licence=licence, quantity=BOUGHT - 1,
        )
        self._check_lookup_count(
            self.base_url, searched_term=licence_asset.licence.niw,
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
        DCAssetFactory(device_info__ralph_device=device)
        self._check_lookup_count(
            self.base_url, searched_term=hostname, expected_count=1
        )

    def test_asset_found_by_device_hostname(self):
        hostname = 'blade-408-1-sw1.dc4.local'
        device = DeviceFactory(name=hostname)
        DCAssetFactory(device_info__ralph_device=device)
        self._check_lookup_count(
            self.base_url, searched_term=hostname, expected_count=1
        )


class TestServerRoomLookup(BaseLookupsTest):
    lookup = ('ralph_assets.models', 'ServerRoomLookup')

    def test_gets_from_data_center(self):
        server_room1 = ServerRoomFactory(data_center=DataCenterFactory())
        server_room2 = ServerRoomFactory(data_center=DataCenterFactory())
        self.assertNotEqual(server_room1.data_center, server_room2.data_center)
        self._check_lookup_count(
            self.base_url,
            searched_term=server_room1.data_center.id,
            expected_count=1,
        )

    def test_gets_ascending_order(self):
        data_center = DataCenterFactory()
        z_server_room = ServerRoomFactory(name='z-server-room',
                                          data_center=data_center)
        a_server_room = ServerRoomFactory(name='a-server-room',
                                          data_center=data_center)
        self.assertEqual(z_server_room.data_center, a_server_room.data_center)
        jsoned = self._get_lookup_results(
            self._get_lookup_url(self.base_url, data_center.id),
        )
        self.assertEqual(jsoned[0]['value'], a_server_room.name)
        self.assertEqual(jsoned[1]['value'], z_server_room.name)


class TestRackLookup(BaseLookupsTest):
    lookup = ('ralph_assets.models', 'RackLookup')

    def test_gets_from_server_room(self):
        rack1 = RackFactory(server_room=ServerRoomFactory())
        rack2 = RackFactory(server_room=ServerRoomFactory())
        self.assertNotEqual(rack1.server_room, rack2.server_room)
        self._check_lookup_count(
            self.base_url,
            searched_term=rack1.server_room.id,
            expected_count=1,
        )

    def test_gets_ascending_order(self):
        server_room = ServerRoomFactory()
        z_rack = RackFactory(name='z-rack', server_room=server_room)
        a_rack = RackFactory(name='a-rack', server_room=server_room)
        self.assertEqual(z_rack.server_room, a_rack.server_room)
        jsoned = self._get_lookup_results(
            self._get_lookup_url(self.base_url, server_room.id),
        )
        self.assertEqual(jsoned[0]['value'], a_rack.name)
        self.assertEqual(jsoned[1]['value'], z_rack.name)
