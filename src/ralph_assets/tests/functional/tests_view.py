# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime
import uuid

from django.test import TestCase
from django.core.urlresolvers import reverse

from ralph_assets.tests.utils.assets import (
    AssetFactory,
    AssetModelFactory,
    WarehouseFactory,
)
from ralph_assets.tests.utils.sam import LicenceFactory
from ralph.ui.tests.global_utils import login_as_su


class TestDataDisplay(TestCase):
    """Test check if data from database are displayed on screen"""

    def setUp(self):
        self.client = login_as_su()
        asset_fields = dict(
            barcode='123456789',
            invoice_no='Invoice #1',
            order_no='Order #1',
            invoice_date=datetime.date(2001, 1, 1),
            sn='0000-0000-0000-0000',
        )
        self.asset = AssetFactory(**asset_fields)

    def test_display_data_in_table(self):
        get_search_page = self.client.get('/assets/dc/search')
        self.assertEqual(get_search_page.status_code, 200)

        # Test if data from database are displayed in correct row.
        first_table_row = get_search_page.context_data['bob_page'][0]
        self.assertEqual(self.asset, first_table_row)


class TestLicencesView(TestCase):
    """This test case concern all licences views."""
    def setUp(self):
        self.client = login_as_su()
        self.licence = LicenceFactory()
        self.modes = ['dc', 'back_office']

    def _field_in_edit_form(self, field, modes=None):
        if not modes:
            modes = self.modes

        for mode in modes:
            url = reverse('edit_licence', args=(mode, self.licence.pk))
            response = self.client.get(url)
            self.assertContains(
                response, 'id_{}'.format(field),
                msg_prefix="Error in {} mode".format(mode),
            )

    def test_edit_form_contains_remarks_field(self):
        self._field_in_edit_form('remarks')

    def test_edit_form_contains_service_name_field(self):
        self._field_in_edit_form('service_name')


class DeviceEditViewTest(TestCase):

    def setUp(self):
        self.client = login_as_su()
        self.asset_src = AssetFactory(sn='123-456-789')
        self.asset_dest = AssetFactory(sn='987-832-668')

        self.model = AssetModelFactory()
        self.warehouse = WarehouseFactory()

    def _create_part(self, asset, model, warehouse):
        url_kwargs = {'mode': 'dc'}
        url = reverse('add_part', kwargs=url_kwargs)
        url += '?device={}'.format(asset.id)

        post_data = {
            'asset': '1',  # submit button
            'model': model.id,
            'warehouse': warehouse.id,
            'device': asset.id,
            'type': '1',
            'sn': str(uuid.uuid1()),
            'deprecation_rate': '25',
        }
        return self.client.post(url, post_data, follow=True)

    def _move_part(self, asset_src, post_data):
        url_kwargs = {'mode': 'back_office', 'asset_id': asset_src.id}
        url = reverse('device_edit', kwargs=url_kwargs)
        return self.client.post(url, post_data, follow=True)

    def test_create_part(self):
        """Create part in add part view."""
        response = self._create_part(
            self.asset_src, self.model, self.warehouse,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['asset'].pk)

    def test_move_part(self):
        """Move part in edit device view.
        Scenario:
         - add part to specified device,
         - go to edit device view,
         - move part from actual device to another device.
        """
        part = self._create_part(
            self.asset_src, self.model, self.warehouse,
        ).context['asset']

        url_kwargs = {'mode': 'back_office', 'asset_id': self.asset_src.id}
        url = reverse('device_edit', kwargs=url_kwargs)
        response = self.client.get(url)
        self.assertContains(response, part)

        post_data = {
            'move_parts': '1',  # submit form
            'new_asset': self.asset_dest.id,
            'part_ids': [part.id],
        }
        response = self._move_part(self.asset_src, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, part)

        url_kwargs = {'mode': 'back_office', 'asset_id': self.asset_dest.id}
        url = reverse('device_edit', kwargs=url_kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, part)

    def test_move_few_part(self):
        """Move part in edit device view.
        Scenario:
         - add part to specified device,
         - go to edit device view,
         - move few parts from actual device to another.
        """
        parts = []
        for i in range(5):
            part = self._create_part(
                self.asset_src, self.model, self.warehouse,
            ).context['asset']
            parts.append(part)

        url_kwargs = {'mode': 'back_office', 'asset_id': self.asset_src.id}
        url = reverse('device_edit', kwargs=url_kwargs)
        response = self.client.get(url)
        for part in parts:
            self.assertContains(response, part)

        post_data = {
            'move_parts': '1',  # submit form
            'new_asset': self.asset_dest.id,
            'part_ids': [part.id for part in parts],
        }
        response = self._move_part(self.asset_src, post_data)
        self.assertEqual(response.status_code, 200)
        for part in parts:
            self.assertNotContains(response, part)

        url_kwargs = {'mode': 'back_office', 'asset_id': self.asset_dest.id}
        url = reverse('device_edit', kwargs=url_kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, part)

    def test_move_part_error_new_asset(self):
        """Move part in edit device view.
        Scenario:
         - add part to specified device,
         - go to edit device view,
         - user fill all required field except new_asset,
         - user see a message: 'Source device asset does not exist'
        """
        msg_error = 'Source device asset does not exist'
        part = self._create_part(
            self.asset_src, self.model, self.warehouse,
        ).context['asset']

        post_data = {
            'move_parts': '1',
            'part_ids': [part.id],
        }
        response = self._move_part(self.asset_src, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, msg_error)
        self.assertContains(response, part)

    def test_move_part_error_part_ids(self):
        """Move part in edit device view.
        Scenario:
         - add part to specified device,
         - go to edit device view,
         - user fill all required field but doesn't select any part,
         - user see a message: 'Please select one or more parts'
        """
        msg_error = 'Please select one or more parts'
        part = self._create_part(
            self.asset_src, self.model, self.warehouse,
        ).context['asset']

        post_data = {
            'move_parts': '1',
            'new_asset': self.asset_dest.id,
        }
        response = self._move_part(self.asset_src, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, msg_error)
        self.assertContains(response, part)
