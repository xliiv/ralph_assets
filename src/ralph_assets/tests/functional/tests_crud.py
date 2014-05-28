# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.test import TestCase

from ralph_assets.models_assets import (
    AssetType,
    AssetSource,
    AssetStatus,
)
from ralph_assets.tests.utils.assets import (
    AssetFactory,
    AssetCategoryFactory,
    AssetModelFactory,
    WarehouseFactory,
)
from ralph.ui.tests.global_utils import login_as_su
import unittest


class TestAdding(TestCase):
    """Test adding single asset"""

    def setUp(self):
        self.client = login_as_su()
        self.category = AssetCategoryFactory()
        self.model = AssetModelFactory(category=self.category)
        self.model2 = AssetModelFactory(category=self.category)
        self.warehouse = WarehouseFactory()
        self.warehouse2 = WarehouseFactory()
        self.asset = AssetFactory()

    def get_common_add_form_data(self):
        return dict(
            type=AssetType.data_center.id,  # 1
            model=self.model.id,  # u'Model1'
            source=AssetSource.shipment.id,  # 1
            invoice_no='Invoice No1',
            order_no='Order no1',
            invoice_date='2001-01-01',
            provider='Provider2',
            status=AssetStatus.new.id,  # 1
            price=11,
            request_date='2001-01-02',
            delivery_date='2001-01-03',
            sn='2222-2222-2222-2222',
            barcode='bc-1111-1111-1111',
            warehouse=self.warehouse.id,  # 1
            deprecation_rate=0,
        )

    def get_common_edit_form_data(self):
        return dict(
            type=AssetType.data_center.id,  # 1
            model=self.model2.id,  # u'Model1'
            source=AssetSource.shipment.id,  # 1
            invoice_no='Invoice No2',
            order_no='Order No2',
            provider='Provider2',
            status=AssetStatus.in_progress.id,  # 1
            invoice_date='2001-02-02',
            request_date='2001-01-02',
            delivery_date='2001-01-03',
            provider_order_date='2001-01-05',
            sn='3333-3333-3333-333',
            barcode='bc-3333-3333-333',
            warehouse=self.warehouse.id,  # 1
            price=2.00,
            remarks='any remarks',
            asset=True,  # Button name
        )

    def send_data_via_add_form(self):
        url = '/assets/dc/add/device/'
        data_in_add_form = self.get_common_add_form_data()
        dc_spec_data = dict(
            ralph_device_id='',
        )
        data_in_add_form.update(dc_spec_data)
        send_post = self.client.post(url, data_in_add_form)
        # If everything is ok, redirect us to /assets/dc/search
        self.assertRedirects(
            send_post,
            # TODO: can't assert that id will be '2'
            # maybe propose to django new assertRedirects with url as regex
            '/assets/dc/edit/device/2/',
            status_code=302,
            target_status_code=200,
        )
        view = self.client.get('/assets/dc/search')
        row_from_table = view.context_data['bob_page'].object_list[1]

        # Overwriting variables to use the object to test the output.
        data_in_add_form.update(
            model=self.model,
            warehouse=self.warehouse,
        )
        # Test comparison input data and output data
        for field in data_in_add_form:
            input = data_in_add_form[field]
            if field == 'ralph_device_id':
                output = ''  # test Hook
            else:
                output = getattr(row_from_table, field)
            msg = 'Field: %s Input: %s Output: %s' % (field, input, output)
            self.assertEqual(unicode(input), unicode(output), msg)

    def send_data_via_edit_form(self):
        # Fetch data
        url = '/assets/dc/edit/device/1/'
        view = self.client.get(url)
        self.assertEqual(view.status_code, 200)
        old_fields = view.context['asset_form'].initial
        data_in_edit_form = self.get_common_edit_form_data()
        dc_spec_data = dict(
            slots=5.0,
            ralph_device_id='',
            deprecation_rate=0,
        )
        data_in_edit_form.update(dc_spec_data)
        self.client.post(url, data_in_edit_form)
        new_view = self.client.get(url)
        new_fields = new_view.context['asset_form'].initial
        correct_data = [
            dict(
                model=self.model2.id,
                invoice_no='Invoice No2',
                order_no='Order No2',
                invoice_date='2001-02-02',
                request_date='2001-01-02',
                delivery_date='2001-01-03',
                provider_order_date='2001-01-05',
                provider='Provider2',
                status=AssetStatus.in_progress.id,
                remarks='any remarks',
            )
        ]
        for data in correct_data:
            for key in data.keys():
                self.assertNotEqual(
                    unicode(old_fields[key]), unicode(new_fields[key])
                )
                self.assertEqual(
                    unicode(new_fields[key]), unicode(data[key])
                )

    def test_send_data_via_add_and_edit_form(self):
        self.send_data_via_add_form()
        self.send_data_via_edit_form()

    @unittest.skip("to be implement")
    def test_delete_asset(self):
        """todo"""
        pass
