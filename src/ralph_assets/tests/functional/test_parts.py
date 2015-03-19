# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import mock
from urllib import urlencode

from django.core.urlresolvers import reverse
from django.test import TestCase

from ralph.cmdb.tests.utils import (
    DeviceEnvironmentFactory,
    ServiceCatalogFactory,
)
from ralph_assets.models_parts import Part
from ralph_assets.parts.views import (
    COMMON_SNS_BETWEEN_FORMSETS_MSG, BULK_CREATE_ERROR_MSG, LIST_SEPARATOR,
)
from ralph_assets.tests.functional.tests_view import BaseViewsTest
from ralph_assets.tests.utils import ClientMixin, AdminFactory
from ralph_assets.tests.utils.assets import (
    AssetFactory,
    AssetType,
    DCAssetFactory,
    WarehouseFactory,
    generate_sn,
)
from ralph_assets.tests.utils.parts import (
    PartFactory,
    PartModelFactory,
)


FORM_FIELDS = (
    'asset_type', 'model', 'service', 'part_environment', 'warehouse',
    'order_no', 'price', 'sn',
)


class PartManageViewsTestBase(ClientMixin, TestCase):

    def setUp(self):  # noqa
        self.sample_warehouse = WarehouseFactory()
        self.sample_service = ServiceCatalogFactory()
        self.sample_environment = DeviceEnvironmentFactory()
        self.sample_part_model = PartModelFactory()
        self.sample_part_1 = PartFactory()
        self.sample_part_2 = PartFactory()

        self.login_as_superuser()

    def _check_part(self, sample_data, expected_sn, part):
        for field, value in sample_data.iteritems():
            if field == 'sn':
                continue
            self.assertEqual(
                getattr(
                    part,
                    '{}_id'.format(field),
                    getattr(part, field),
                ),
                value,
            )
        self.assertEqual(part.sn, expected_sn)


class TestAddPartView(PartManageViewsTestBase):

    def _get_sample_form_data(self, serial_numbers):
        return {
            'asset_type': AssetType.data_center.id,
            'model': self.sample_part_model.id,
            'service': self.sample_service.id,
            'part_environment': self.sample_environment.id,
            'warehouse': self.sample_warehouse.id,
            'order_no': '#123',
            'price': 1000.5,
            'sn': '\n'.join(serial_numbers),
        }

    def _make_request(self, data):
        url = reverse('add_part', kwargs={'mode': 'dc'})
        return self.client.post(url, data)

    def test_should_add_parts_when_all_is_ok(self):
        """
        Scenario:
        - all required data were sent

        Expectations:
        - new parts exist in DB
        - redirect (302)
        """

        serial_numbers = ['sn_qwe_1', 'sn_qwe_2']
        sample_data = self._get_sample_form_data(serial_numbers)
        response = self._make_request(sample_data)
        self.assertEqual(response.status_code, 302)
        for sn in serial_numbers:
            part = Part.objects.get(sn=sn)
            self._check_part(sample_data, sn, part)

    def test_should_return_validation_error_when_required_fields_were_empty(
        self
    ):
        """
        Scenario:
        - all required data were not sent

        Expectations:
        - all required field should have `This field is required...` or
          similar error
        - not redirect (200)
        """

        response = self._make_request({})
        self.assertEqual(response.status_code, 200)
        for field in FORM_FIELDS:
            if field == 'sn':
                error_msg = (
                    "Field can't be empty. Please put the item OR "
                    "items separated by new line or comma."
                )
            else:
                error_msg = 'This field is required.'
            self.assertFormError(
                response,
                'form',
                field,
                error_msg
            )

    def test_should_return_validation_error_when_existing_sn_was_sent(self):
        """
        Scenario:
        - send all required data with existing SN

        Expectations:
        - number of errors should be equal 1 - only `sn` field
        - not redirect (200)
        """

        serial_numbers = [self.sample_part_1.sn]
        sample_data = self._get_sample_form_data(serial_numbers)
        response = self._make_request(sample_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['form'].errors), 1)
        self.assertFormError(
            response,
            'form',
            'sn',
            'Following items already exist: '
            '<a href="/assets/dc/edit/part/{0}/">{0}</a>'.format(
                self.sample_part_1.id,
            )
        )


class TestEditPartView(PartManageViewsTestBase):

    def _make_request(self, part_id, data):
        url = reverse('part_edit', kwargs={'mode': 'dc', 'part_id': part_id})
        return self.client.post(url, data)

    def _check_part(self, sample_data, expected_sn, part):
        for field, value in sample_data.iteritems():
            if field == 'sn':
                continue
            self.assertEqual(
                getattr(
                    part,
                    '{}_id'.format(field),
                    getattr(part, field),
                ),
                value,
            )
        self.assertEqual(part.sn, expected_sn)

    def _get_form_data_by_part(self, part):
        data = {
            'id': part.id,
        }
        for field in FORM_FIELDS:
            if field == 'asset_type':
                data[field] = part.asset_type.id
            else:
                data[field] = getattr(
                    part,
                    '{}_id'.format(field),
                    getattr(part, field)
                )
        return data

    def test_should_save_changes_when_all_is_ok(self):
        """
        Scenario:
        - change some simple values (price and order_no)

        Expectations:
        - specified values were changed
        - other without changes
        - redirect (302)
        """

        data = self._get_form_data_by_part(self.sample_part_2)
        data.update({
            'price': 10.0,
            'order_no': '#321321',
        })
        response = self._make_request(self.sample_part_2.id, data)
        self.assertEqual(response.status_code, 302)
        part = Part.objects.get(pk=self.sample_part_2.id)
        self._check_part(data, self.sample_part_2.sn, part)

    def test_shound_return_404_when_part_does_not_exist(self):
        """
        Scenario:
        - change not existing part

        Expectations:
        - 404
        """

        response = self._make_request(666, {})
        self.assertEqual(response.status_code, 404)


class TestChangePartsView(ClientMixin, TestCase):

    def setUp(self):
        self.login_as_user(self.user)

    @classmethod
    def setUpClass(cls):
        cls.asset = AssetFactory()
        cls.user = AdminFactory()

    @classmethod
    def tearDownClass(cls):
        cls.asset.delete()
        cls.user.delete()

    def test_redirect(self):
        url = reverse(
            'change_parts', kwargs={'mode': 'dc', 'asset_id': self.asset.id}
        )
        post_data = {
            'in-0-sn': '21',
            'in-1-sn': '31',
            'out-0-sn': '22',
            'out-1-sn': '32',
            'out-INITIAL_FORMS': 0,
            'out-TOTAL_FORMS': 2,
            'out-MAX_NUM_FORMS': 1000,
            'in-INITIAL_FORMS': 0,
            'in-TOTAL_FORMS': 2,
            'in-MAX_NUM_FORMS': 1000,
        }
        response = self.client.post(url, post_data)
        expected_url = url + '?in_sn=21%2C31&out_sn=22%2C32'
        self.assertRedirects(response, expected_url)


class TestMovingParts(BaseViewsTest):

    def test_part_is_attached(self):
        "Part can be attached to asset"
        asset = DCAssetFactory()
        part = PartFactory()
        self.assertEqual(len(asset.parts.all()), 0)
        save_url = reverse('assign_to_asset', args=('dc', asset.id))
        post_data = {
            'asset': u'',
            'attach-INITIAL_FORMS': 1,
            'attach-MAX_NUM_FORMS': '1000',
            'attach-TOTAL_FORMS': 1,
            'attach-0-id': part.id,
        }
        response = self.client.post(save_url, post_data, follow=True)
        self.assertEqual(len(response.context['messages']), 2)
        self.assertIn(
            'detached 0',
            unicode(response.context['messages']._loaded_messages[0])
        )
        self.assertIn(
            'attached 1',
            unicode(response.context['messages']._loaded_messages[1])
        )

    def test_part_is_detached(self):
        "Part can be deatached from asset"
        part = PartFactory()
        self.assertEqual(len(part.asset.parts.all()), 1)
        save_url = reverse('assign_to_asset', args=('dc', part.asset.id))
        post_data = {
            'asset': u'',
            'detach-INITIAL_FORMS': 1,
            'detach-MAX_NUM_FORMS': '1000',
            'detach-TOTAL_FORMS': 1,
            'detach-0-id': part.id,
            'detach-0-sn': part.sn,
            'detach-0-model': part.model.id,
            'detach-0-price': part.price,
            'detach-0-service': part.service.id,
            'detach-0-part_environment': part.part_environment.id,
            'detach-0-warehouse': part.warehouse.id
        }
        response = self.client.post(save_url, post_data, follow=True)
        self.assertEqual(len(response.context['messages']), 2)
        self.assertIn(
            'detached 1',
            unicode(response.context['messages']._loaded_messages[0])
        )
        self.assertIn(
            'attached 0',
            unicode(response.context['messages']._loaded_messages[1])
        )

    def test_detached_part_can_be_edited(self):
        "Deatached part data was edited excluding order-no field"
        new_data = PartFactory()
        part = PartFactory()
        free_sn = 'non-existing-new-sn'
        self.assertNotEqual(part.sn, free_sn)
        save_url = reverse('assign_to_asset', args=('dc', part.asset.id))
        post_data = {
            'asset': u'',
            'detach-INITIAL_FORMS': 1,
            'detach-MAX_NUM_FORMS': '1000',
            'detach-TOTAL_FORMS': 1,
            'detach-0-id': part.id,
            'detach-0-sn': free_sn,
            'detach-0-model': new_data.model.id,
            'detach-0-order_no': new_data.order_no,
            'detach-0-price': new_data.price,
            'detach-0-service': new_data.service.id,
            'detach-0-part_environment': new_data.part_environment.id,
            'detach-0-warehouse': new_data.warehouse.id
        }
        self.client.post(save_url, post_data, follow=True)
        changed_part = Part.objects.get(pk=part.id)
        for field in [
            'model', 'price', 'service', 'part_environment', 'warehouse'
        ]:
            self.assertNotEqual(
                getattr(part, field), getattr(new_data, field),
            )
            self.assertEqual(
                getattr(changed_part, field), getattr(new_data, field),
            )
        self.assertEqual(changed_part.sn, free_sn)
        # order_no should stay unchanged
        self.assertEqual(changed_part.order_no, part.order_no)

    def test_cant_attach_and_detach_same_sn(self):
        part = PartFactory()
        save_url = reverse('assign_to_asset', args=('dc', part.asset.id))
        post_data = {
            'asset': u'',
            'attach-INITIAL_FORMS': 1,
            'attach-MAX_NUM_FORMS': '1000',
            'attach-TOTAL_FORMS': 1,
            'attach-0-id': part.id,
            'attach-0-sn': part.sn,
            'detach-INITIAL_FORMS': 1,
            'detach-MAX_NUM_FORMS': '1000',
            'detach-TOTAL_FORMS': 1,
            'detach-0-id': part.id,
            'detach-0-sn': part.sn,
            'detach-0-model': part.model.id,
            'detach-0-price': part.price,
            'detach-0-service': part.service.id,
            'detach-0-part_environment': part.part_environment.id,
            'detach-0-warehouse': part.warehouse.id
        }
        response = self.client.post(save_url, post_data, follow=True)
        self.assertEqual(len(response.context['messages']), 1)
        self.assertEqual(
            unicode(response.context['messages']._loaded_messages[0]),
            COMMON_SNS_BETWEEN_FORMSETS_MSG,
        )

    def test_exchanging_missing_parts_adds_them(self):
        asset = DCAssetFactory()
        in_sn = generate_sn()
        out_sn = generate_sn()
        self.assertEqual(len(Part.objects.all()), 0)
        form_url = reverse('assign_to_asset', args=('dc', asset.id))
        request_query = urlencode({
            'in_sn': LIST_SEPARATOR.join([in_sn]),
            'out_sn': LIST_SEPARATOR.join([out_sn]),
        })
        full_form_url = '{}?{}'.format(form_url, request_query)
        self.client.get(full_form_url)
        self.assertEqual(len(Part.objects.all()), 2)

    def test_exchanging_existing_parts_uses_them(self):
        part_in = PartFactory()
        part_out = PartFactory()
        self.assertEqual(len(Part.objects.all()), 2)
        form_url = reverse('assign_to_asset', args=('dc', part_out.asset.id))
        request_query = urlencode({
            'in_sn': LIST_SEPARATOR.join([part_in.sn]),
            'out_sn': LIST_SEPARATOR.join([part_out.sn]),
        })
        full_form_url = '{}?{}'.format(form_url, request_query)
        response = self.client.get(full_form_url, follow=True)
        self.assertEqual(len(Part.objects.all()), 2)
        context = response.context
        self.assertEqual(
            context['params']['detach_formset'].forms[0]['id'].value(),
            part_out.id,
        )
        self.assertEqual(
            context['params']['attach_formset'].forms[0]['id'].value(),
            part_in.id,
        )

    @mock.patch(
        'ralph_assets.parts.views.AssignToAssetView._find_non_existing',
    )
    def test_show_message_on_failed_adding(self, mocked_method):
        asset = DCAssetFactory()
        part_in = PartFactory()
        mocked_method.return_value = {part_in.sn}

        form_url = reverse('assign_to_asset', args=('dc', asset.id))
        request_query = urlencode({'in_sn': LIST_SEPARATOR.join([part_in.sn])})
        full_form_url = '{}?{}'.format(form_url, request_query)
        response = self.client.get(full_form_url, follow=True)
        self.assertEqual(len(response.context['messages']), 1)
        self.assertEqual(
            unicode(response.context['messages']._loaded_messages[0]),
            BULK_CREATE_ERROR_MSG,
        )
