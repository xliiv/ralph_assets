# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.test import TestCase

from ralph.cmdb.tests.utils import (
    DeviceEnvironmentFactory,
    ServiceCatalogFactory,
)
from ralph_assets.models_parts import Part
from ralph_assets.tests.utils import ClientMixin
from ralph_assets.tests.utils.assets import AssetType, WarehouseFactory
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
