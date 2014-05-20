# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.test import TestCase

from ralph_assets import models_assets
from ralph_assets.models_assets import AssetStatus
from ralph_assets.tests import util as utils
from ralph_assets.tests.util import (
    create_asset,
    create_model,
    create_category,
    get_bulk_edit_post_data,
)
from ralph.ui.tests.global_utils import login_as_su


class TestBulkEdit(TestCase):
    """Test bulkedit for generic actions

    Scenario:
    1. Add two assets
    2. Check if data was saved
    """

    def setUp(self):
        self.client = login_as_su()
        self.category = create_category()
        self.asset = create_asset(
            sn='1111-1111-1111-1111',
        )
        self.asset1 = create_asset(
            sn='2222-2222-2222-2222',
        )
        self.user = utils.create_user()
        self.owner = self.user
        self.model = create_model(category=self.category)  # u'Model1'
        self.model1 = create_model(name='Model2', category=self.category)
        self.warehouse = utils.create_warehouse()
        self.assetOwner = utils.create_asset_owner()
        self.asset_service = utils.create_service()

        self.common_asset_data = {  # DC & BO common data
            'status': models_assets.AssetStatus.in_progress,
            'barcode': 'barcode',
            'model': self.model,
            'user': self.user,
            'owner': self.user,
            'warehouse': self.warehouse,
            'property_of': self.assetOwner,
            'service_name': self.asset_service,
            'invoice_no': 'invoice_no',
            'invoice_date': '2011-11-14',
            'price': '100',
            'task_url': 'www.test.com',
            'deprecation_rate': '25',
            'order_no': 'order_no',
            'source': models_assets.AssetSource.shipment,
        }

    def test_edit_via_bulkedit_form(self):
        url = '/assets/dc/bulkedit/?select=%s&select=%s' % (
            self.asset.id, self.asset1.id)
        content = self.client.get(url)
        self.assertEqual(content.status_code, 200)

        post_data = get_bulk_edit_post_data(
            {
                'model': self.model.id,
                'invoice_no': 'Invoice No1',
                'order_no': 'Order No1',
                'invoice_date': '2012-02-02',
                'status': AssetStatus.in_progress.id,
                'sn': '3333-3333-3333-3333',
                'barcode': 'bc-3333-3333-3333-3333',
            },
            {
                'model': self.model1.id,
                'invoice_no': 'Invoice No2',
                'order_no': 'Order No2',
                'invoice_date': '2011-02-03',
                'status': AssetStatus.waiting_for_release.id,
                'sn': '4444-4444-4444-4444',
                'barcode': 'bc-4444-4444-4444-4444',
            },
        )

        response = self.client.post(url, post_data, follow=True)

        # Find success message
        self.assertTrue('Changes saved.' in response.content)

        # if everything is ok, server return response code = 302, and
        # redirect us to /assets/dc/search given response code 200
        self.assertRedirects(
            response,
            url,
            status_code=302,
            target_status_code=200,
        )

        # Simulate reopening bulkedit form to check if data were written
        new_view = self.client.get(url)
        fields = new_view.context['formset'].queryset

        correct_data = [
            dict(
                model=unicode(self.model),
                invoice_no='Invoice No1',
                order_no='Order No1',
                invoice_date='2012-02-02',
                status=AssetStatus.in_progress.id,
                sn='3333-3333-3333-3333',
                barcode='bc-3333-3333-3333-3333',
            ),
            dict(
                model=unicode(self.model1),
                invoice_no='Invoice No2',
                order_no='Order No2',
                invoice_date='2011-02-03',
                status=AssetStatus.waiting_for_release.id,
                sn='4444-4444-4444-4444',
                barcode='bc-4444-4444-4444-4444',
            )
        ]
        counter = 0
        for data in correct_data:
            for key in data.keys():
                self.assertEqual(
                    unicode(getattr(fields[counter], key)), unicode(data[key])
                )
            counter += 1

    def _test_showing_form_data(self, mode, asset_id, asset_data):
        """
        Common code for tests:
        - test_showing_dc_form_data
        - test_showing_bo_form_data
        """
        url = ''.join([
            reverse('bulkedit', kwargs={'mode': mode}),
            '?select={}'.format(asset_id),
        ])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        for field_name, value in asset_data.items():
            form_val = unicode(
                response.context['formset'].forms[0][field_name].value(),
            )
            try:
                expected = value.id
            except AttributeError:
                expected = value
            msg = 'Bulkedit field "{}" got "{}" instead of "{}"'.format(
                field_name, form_val, expected,
            )
            self.assertEqual(form_val, unicode(expected), msg)

    def test_showing_dc_form_data(self):
        """
        1. add DC asset,
        2. open asset in bulk mode,
        3. check if all fields are set like the added asset.
        """
        dc_asset_data = self.common_asset_data.copy()
        dc_asset_data.update({'sn': 'dc-sn-number'})
        dc_asset = create_asset(**dc_asset_data)
        self._test_showing_form_data(
            'dc', dc_asset.id, dc_asset_data
        )

    def test_showing_bo_form_data(self):
        """
        1. add BO asset,
        2. open asset in bulk mode,
        3. check if all fields are set like the added asset.
        """
        bo_asset_data = self.common_asset_data.copy()
        bo_asset_data.update({
            'sn': 'bo-sn-number',
            'type': models_assets.AssetType.back_office,
            'purpose': models_assets.AssetPurpose.others,
            'provider': 'provider',
        })
        bo_asset = utils.create_bo_asset(**bo_asset_data)
        self._test_showing_form_data(
            'back_office', bo_asset.id, bo_asset_data
        )
