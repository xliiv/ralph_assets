# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime
import json
import tempfile
import uuid
from decimal import Decimal
from urllib import urlencode

from dj.choices import Country
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings

from ralph_assets import models_assets
from ralph_assets import models_support
from ralph_assets import models_sam
from ralph_assets.tests.utils import (
    AjaxClient,
    AttachmentFactory,
    ClientMixin,
    UserFactory,
)
from ralph_assets.tests.utils import assets as assets_utils
from ralph_assets.tests.utils import sam as sam_utils
from ralph_assets.tests.utils.assets import (
    BOAssetFactory,
    AssetFactory,
    AssetModelFactory,
    DCAssetFactory,
    WarehouseFactory,
)
from ralph_assets.tests.unit.tests_other import TestHostnameAssigning
from ralph_assets.tests.utils.sam import LicenceFactory
from ralph_assets.tests.utils.supports import (
    BOSupportFactory,
    DCSupportFactory,
    SupportTypeFactory,
)


def update(_dict, obj, keys):
    """
    Update *_dict* with *obj*'s values from keys.
    """
    for field_name in keys:
        _dict[field_name] = getattr(obj, field_name)
    return _dict


def get_asset_data():
    """
    Common asset data for DC & BO.

    This can't be a just module dict, becasue these data include factories
    which are not accessible during module import causing error.
    """
    return {
        'asset': '',  # required if asset (instead of *part*) is edited
        'barcode': 'barcode1',
        'budget_info': assets_utils.BudgetInfoFactory().id,
        'delivery_date': datetime.date(2013, 1, 7),
        'deprecation_end_date': datetime.date(2013, 7, 25),
        'deprecation_rate': 77,
        'invoice_date': datetime.date(2009, 2, 23),
        'invoice_no': 'Invoice no #3',
        'loan_end_date': datetime.date(2013, 12, 29),
        'location': 'location #3',
        'model': assets_utils.AssetModelFactory().id,
        'niw': 'Inventory number #3',
        'order_no': 'Order no #3',
        'owner': assets_utils.UserFactory().id,
        'price': Decimal('43.45'),
        'property_of': assets_utils.AssetOwnerFactory().id,
        'provider': 'Provider #3',
        'provider_order_date': datetime.date(2014, 3, 17),
        'remarks': 'Remarks #3',
        'request_date': datetime.date(2014, 6, 9),
        'service_name': assets_utils.ServiceFactory().id,
        'source': models_assets.AssetSource.shipment.id,
        'status': models_assets.AssetStatus.new.id,
        'task_url': 'http://www.url-3.com/',
        'user': assets_utils.UserFactory().id,
        'warehouse': assets_utils.WarehouseFactory().id,
    }


def check_fields(testcase, correct_data, object_to_check):
    """
    Checks if *object_to_check* has the same data as *correct_data*

    :param tc: testcase object
    :param correct_data: list with of tuples: (property_name, expected_value)
    :param object_to_check: dict with requried data
    """
    for prop_name, expected in correct_data:
        object_value = getattr(object_to_check, prop_name)
        try:
            object_value = object_value.id
        except AttributeError:
            pass
        object_value, expected = (
            unicode(object_value), unicode(expected)
        )
        msg = 'Object prop. "{}" is "{}" instead of "{}"'.format(
            prop_name, repr(object_value), repr(expected)
        )
        testcase.assertEqual(object_value, expected, msg)


class BaseViewsTest(ClientMixin, TestCase):
    client_class = AjaxClient

    def setUp(self):
        self.login_as_superuser()
        super(BaseViewsTest, self).setUp()

    def _assert_field_in_form(self, form_url, fields_names):
        check_strings = ('name="{}"'.format(f) for f in fields_names)
        response = self.client.get(form_url)
        for check_string in check_strings:
            self.assertContains(response, check_string)

    def get_object_form_data(self, url, form_name):
        """
        Gets data from form *form_name* inside context under *url*.
        Useful when, eg. request data for add|edit asset is needed.
        """
        response = self.client.get(url)
        form = response.context[form_name]
        return form.__dict__['initial']


class TestDataDisplay(ClientMixin, TestCase):
    """Test check if data from database are displayed on screen"""

    def setUp(self):
        self.login_as_superuser()
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


class TestDevicesView(ClientMixin, TestCase):
    """
    Parent class for common stuff for Test(DataCenter|BackOffice)DeviceView.
    """

    def setUp(self):
        self.login_as_superuser()
        self._visible_add_form_fields = [
            'asset', 'barcode', 'budget_info', 'category', 'delivery_date',
            'deprecation_end_date', 'deprecation_rate', 'invoice_date',
            'invoice_no', 'location', 'model', 'niw', 'order_no', 'owner',
            'price', 'property_of', 'provider', 'provider_order_date',
            'remarks', 'request_date', 'service_name', 'sn', 'source',
            'status', 'task_url', 'type', 'user', 'warehouse',
        ]
        self._visible_edit_form_fields = self._visible_add_form_fields[:]
        self._visible_edit_form_fields.extend([
            'supports_text', 'licences_text',
        ])

    def get_asset_form_data(self):
        from ralph_assets import urls
        asset = self.asset_factory()
        url = reverse('device_edit', kwargs={
            'mode': urls.normalize_asset_mode(asset.type.name),
            'asset_id': asset.id,
        })
        form_data = self.get_object_form_data(url, 'asset_form')
        asset.delete()
        return form_data

    def prepare_readonly_fields(self, new_asset_data, asset, readonly_fields):
        update(new_asset_data, asset, readonly_fields)

    def _update_with_supports(self, _dict):
        supports = [
            DCSupportFactory().id,
            BOSupportFactory().id,
        ]
        supports_value = '|{}|'.format('|'.join(map(str, supports)))
        _dict.update(dict(supports=supports_value))
        return supports

    def _check_asset_supports(self, asset, expected_supports):
        self.assertEqual(
            len(asset.supports.all()), len(expected_supports),
        )
        del self.new_asset_data['supports']

    def _save_asset_for_hostname_generation(self, extra_data):
        """
        Prepare (BO|DC)asset for further hostname field checks.

        - create asset a1 with hostname=None
        - get edit data from form in context
        - check if a1's hostname is None
        - send save edits request
        - return response object for futher checks
        """
        asset = self.asset_factory(**{
            'hostname': None,
            'status': TestHostnameAssigning.neutral_status,
        })
        url = reverse('device_edit', kwargs={
            'mode': self.mode,
            'asset_id': asset.id,
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        edit_data = {}
        asset_form = response.context['asset_form']
        for field_name, field_value in asset_form.fields.items():
            raw_field_value = asset_form[field_name].value()
            field_value = str(raw_field_value) if raw_field_value else ''
            edit_data[field_name] = field_value
        edit_data.update(extra_data)
        self.assertIsNone(asset.hostname)
        url = reverse('device_edit', kwargs={
            'mode': self.mode,
            'asset_id': asset.id,
        })
        response = self.client.post(url, edit_data)
        return asset, response

    @override_settings(ASSETS_AUTO_ASSIGN_HOSTNAME=True)
    def _test_hostname_is_assigned(self, extra_data):
        asset, response = self._save_asset_for_hostname_generation(extra_data)
        self.assertRedirects(
            response, response.request['PATH_INFO'], status_code=302,
            target_status_code=200,
        )
        asset = models_assets.Asset.objects.get(pk=asset.id)
        self.assertIsNotNone(asset.hostname)
        return asset

    def update_asset(self, asset_id, **kwargs):
        url = reverse('device_edit', kwargs={
            'mode': self.mode if self.mode else 'back_office',
            'asset_id': asset_id,
        })
        response = self.client.get(url)
        form = response.context['asset_form']
        update_dict = form.__dict__['initial']
        update_dict.update(**kwargs)
        response = self.client.post(url, update_dict, follow=True)
        return response, models_assets.Asset.objects.get(id=asset_id)

    def _test_mulitvalues_behaviour(self):
        '''
        - get add device request data d1
        - update d1 with duplicated values for field sn
        - send add device request with data d1
        - assert error about duplicates occured

        - update d1 with unique values for field sn
        - send add device request with data d1
        - assert asset was added
        '''
        request_data = self.get_asset_form_data()
        request_data.update(dict(
            # required, irrelevant data here
            ralph_device_id='',
            hostname='',
        ))
        url = reverse('add_device', kwargs={'mode': self.mode})

        duplicated_sns = ','.join([self.asset_factory.build().sn] * 3)
        request_data['sn'] = duplicated_sns
        response = self.client.post(url, request_data)
        self.assertFormError(
            response, 'asset_form', 'sn', 'There are duplicates in field.',
        )
        unique_sns = ','.join([
            self.asset_factory.build().sn for i in xrange(3)
        ])
        request_data.update(dict(
            sn=unique_sns,
            barcode='1,2,3',
        ))
        request_data['sn'] = unique_sns
        response = self.client.post(url, request_data)
        self.assertEqual(response.status_code, 302)


class TestDataCenterDevicesView(TestDevicesView, BaseViewsTest):

    def setUp(self):
        super(TestDataCenterDevicesView, self).setUp()
        self.asset_factory = DCAssetFactory
        self.mode = 'dc'
        self.asset_data = get_asset_data()
        self.asset_data.update({
            'type': models_assets.AssetType.data_center.id,
        })
        self.device_data = {
            'ralph_device_id': '',
            'u_height': 14,
            'u_level': 21,
        }

        self.additional_fields = ['ralph_device_id', 'u_height', 'u_level']
        self.visible_add_form_fields = self._visible_add_form_fields[:]
        self.visible_add_form_fields.extend(self.additional_fields)
        self.visible_edit_form_fields = self._visible_edit_form_fields[:]
        self.visible_edit_form_fields.extend(self.additional_fields)

    def test_add_device(self):
        """
        Add device with all fields filled.

        - send the full asset's data with post request
        - get saved asset from db
        - asserts all db asset's fields with request's data
        """
        asset_data = self.asset_data.copy()
        asset_data.update({
            'sn': str(uuid.uuid1()),
        })
        device_data = self.device_data.copy()
        request_data = {}
        request_data.update(asset_data)
        request_data.update(device_data)
        url = reverse('add_device', kwargs={'mode': self.mode})
        existing_assets = models_assets.Asset.objects.reverse()
        asset_id = existing_assets[0].id + 1 if existing_assets else 1
        response = self.client.post(url, request_data)
        self.assertRedirects(
            response,
            reverse('device_edit', kwargs={
                'mode': self.mode, 'asset_id': asset_id
            }),
            status_code=302,
            target_status_code=200,
        )
        asset = models_assets.Asset.objects.filter(pk=asset_id).get()
        del asset_data['asset']
        check_fields(self, asset_data.items(), asset)
        device_data['ralph_device_id'] = asset_id
        check_fields(self, device_data.items(), asset.device_info)

    def test_edit_device(self):
        """
        Add device with all fields filled.

        - generate asset data d1
        - create asset a1
        - send data d1 via edit request to a1
        - get a1 from db
        - assert a1's data is the same as d1 data
        """
        self.new_asset_data = self.asset_data.copy()
        supports = self._update_with_supports(self.new_asset_data)
        new_device_data = self.device_data.copy()
        asset = DCAssetFactory()
        edited_data = {}
        edited_data.update(self.new_asset_data)
        edited_data.update(new_device_data)
        url = reverse('device_edit', kwargs={
            'mode': self.mode,
            'asset_id': asset.id,
        })
        response = self.client.post(url, edited_data)
        self.assertRedirects(
            response, url, status_code=302, target_status_code=200,
        )
        asset = models_assets.Asset.objects.get(pk=asset.id)
        del self.new_asset_data['asset']
        self._check_asset_supports(asset, supports)
        check_fields(self, self.new_asset_data.items(), asset)
        new_device_data['ralph_device_id'] = None
        check_fields(self, new_device_data.items(), asset.device_info)

    def test_hostname_is_assigned(self):
        extra_data = {
            # required data for this test
            'ralph_device_id': '',
            'asset': '',  # required button
            'status': str(TestHostnameAssigning.trigger_status.id),
        }
        self._test_hostname_is_assigned(extra_data)

    def test_device_add_form_show_fields(self):
        required_fields = self.visible_add_form_fields[:]
        form_url = reverse('add_device', kwargs={'mode': 'dc'})
        self._assert_field_in_form(form_url, required_fields)

    def test_device_edit_form_show_fields(self):
        required_fields = self.visible_edit_form_fields[:]
        device = DCAssetFactory()
        form_url = reverse(
            'device_edit', kwargs={'mode': 'dc', 'asset_id': device.id},
        )
        self._assert_field_in_form(form_url, required_fields)

    def test_mulitvalues_behaviour(self):
        self._test_mulitvalues_behaviour()


class TestBackOfficeDevicesView(TestDevicesView, BaseViewsTest):

    def setUp(self):
        super(TestBackOfficeDevicesView, self).setUp()
        self.asset_factory = BOAssetFactory
        self.mode = 'back_office'
        self.asset_data = get_asset_data()
        self.asset_data.update({
            'type': models_assets.AssetType.back_office.id,
        })
        self.office_data = {
            'coa_oem_os': assets_utils.CoaOemOsFactory().id,
            'purpose': models_assets.AssetPurpose.others.id,
            'license_key': str(uuid.uuid1()),
            'imei': assets_utils.generate_imei(15),
            'coa_number': str(uuid.uuid1()),
        }
        self.additional_fields = [
            'budget_info', 'coa_number', 'coa_oem_os', 'license_key',
        ]
        self.visible_add_form_fields = self._visible_add_form_fields[:]
        self.visible_add_form_fields.extend(self.additional_fields)
        self.visible_edit_form_fields = self._visible_edit_form_fields[:]
        self.visible_edit_form_fields.extend(self.additional_fields)

    def test_add_device(self):
        """
        Add device with all fields filled.

        - send the full asset's data with post request
        - get saved asset from db
        - asserts all db asset's fields with request's data
        """
        asset_data = self.asset_data.copy()
        asset_data.update({
            'sn': str(uuid.uuid1()),
        })
        office_data = self.office_data.copy()
        request_data = {}
        request_data.update(asset_data)
        request_data.update(office_data)
        url = reverse('add_device', kwargs={'mode': self.mode})
        existing_assets = models_assets.Asset.objects.reverse()
        asset_id = existing_assets[0].id + 1 if existing_assets else 1
        response = self.client.post(url, request_data)
        self.assertRedirects(
            response,
            reverse('device_edit', kwargs={
                'mode': self.mode, 'asset_id': asset_id
            }),
            status_code=302,
            target_status_code=200,
        )
        asset = models_assets.Asset.objects.filter(pk=asset_id).get()
        del asset_data['asset']
        check_fields(self, asset_data.items(), asset)
        check_fields(self, office_data.items(), asset.office_info)

    def test_edit_device(self):
        """
        Edit device with all fields filled.

        - generate asset data d1
        - create asset a1
        - send data d1 via edit request to a1
        - get a1 from db
        - assert a1's data is the same as d1 data
        """
        self.new_asset_data = self.asset_data.copy()
        self.new_asset_data.update({
            'hostname': 'XXXYY00001'
        })
        supports = self._update_with_supports(self.new_asset_data)
        new_office_data = self.office_data.copy()
        asset = BOAssetFactory()
        edited_data = {}
        edited_data.update(self.new_asset_data)
        edited_data.update(new_office_data)
        url = reverse('device_edit', kwargs={
            'mode': self.mode,
            'asset_id': asset.id,
        })
        response = self.client.post(url, edited_data)
        self.assertRedirects(
            response, url, status_code=302, target_status_code=200,
        )
        asset = models_assets.Asset.objects.get(pk=asset.id)
        del self.new_asset_data['asset']
        self.prepare_readonly_fields(self.new_asset_data, asset, ['hostname'])
        self._check_asset_supports(asset, supports)
        check_fields(self, self.new_asset_data.items(), asset)
        self.assertIsNotNone(asset.hostname)
        check_fields(self, new_office_data.items(), asset.office_info)

    def test_hostname_is_assigned(self):
        extra_data = {
            # required data for this test
            'asset': '',  # required button
            'status': str(TestHostnameAssigning.trigger_status.id),
        }
        self._test_hostname_is_assigned(extra_data)

    def test_device_add_form_show_fields(self):
        required_fields = self.visible_add_form_fields[:]
        form_url = reverse('add_device', kwargs={'mode': 'back_office'})
        self._assert_field_in_form(form_url, required_fields)

    def test_device_edit_form_show_fields(self):
        required_fields = self.visible_edit_form_fields[:]
        device = BOAssetFactory()
        form_url = reverse(
            'device_edit', kwargs={
                'mode': 'back_office', 'asset_id': device.id,
            }
        )
        self._assert_field_in_form(form_url, required_fields)

    def test_last_hostname_change_owner(self):
        """Assets user change owner and status and expect new hostname.
        Scenario:
        - user change status and owner in asset
        - again, change status and owner in asset
        - user change status to in progress (this action will by generate
        new hostname respected latest hostname)
        """
        def set_user_country(user, country):
            user.profile.country = country
            user.profile.save()

        user_pl_1 = UserFactory()
        set_user_country(user_pl_1, Country.pl)
        user_pl_2 = UserFactory()
        set_user_country(user_pl_2, Country.pl)
        user_pl_3 = UserFactory()
        set_user_country(user_pl_3, Country.pl)
        user_cz = UserFactory()
        set_user_country(user_cz, Country.cz)
        asset = BOAssetFactory(
            model=AssetModelFactory(category__code='XX'),
            hostname='',
            user=user_pl_1,
            owner=user_pl_1,
            status=models_assets.AssetStatus.new,
        )

        response, asset = self.update_asset(
            asset.id,
            asset=True,
            owner=user_pl_2.id,
            status=models_assets.AssetStatus.in_progress.id,
        )
        self.assertEqual(asset.hostname, 'POLXX00001')

        response, asset = self.update_asset(
            asset.id,
            asset=True,
            owner=user_cz.id,
            status=models_assets.AssetStatus.new.id,
        )
        response, asset = self.update_asset(
            asset.id,
            asset=True,
            status=models_assets.AssetStatus.in_progress.id,
        )
        self.assertEqual(asset.hostname, 'CZEXX00001')

        response, asset = self.update_asset(
            asset.id,
            asset=True,
            owner=user_pl_3.id,
            status=models_assets.AssetStatus.new.id,
        )
        response, asset = self.update_asset(
            asset.id,
            asset=True,
            status=models_assets.AssetStatus.in_progress.id,
        )
        self.assertEqual(asset.hostname, 'POLXX00002')

    def test_mulitvalues_behaviour(self):
        self._test_mulitvalues_behaviour()


class TestLicencesView(BaseViewsTest):
    """This test case concern all licences views."""

    def setUp(self):
        super(TestLicencesView, self).setUp()
        self.license_data = {
            'accounting_id': '1',
            'asset_type': models_assets.AssetType.back_office.id,
            # TODO: this field is not saving 'assets':'|{}|'.format(asset.id),
            'budget_info': assets_utils.BudgetInfoFactory().id,
            'invoice_date': datetime.date(2014, 06, 11),
            'invoice_no': 'Invoice no',
            'licence_type': sam_utils.LicenceTypeFactory().id,
            'license_details': 'licence_details',
            'manufacturer': assets_utils.AssetManufacturerFactory().id,
            'niw': 'Inventory number',
            'number_bought': '99',
            'order_no': 'Order no',
            'price': Decimal('100.99'),
            'property_of': assets_utils.AssetOwnerFactory().id,
            'provider': 'Provider',
            'remarks': 'Additional remarks',
            'service_name': assets_utils.ServiceFactory().id,
            'sn': 'Licence key',
            'software_category': sam_utils.SoftwareCategoryFactory().id,
            'valid_thru': datetime.date(2014, 06, 10),
        }
        self.licence = LicenceFactory()
        self.visible_add_form_fields = [
            'accounting_id', 'asset', 'asset_type', 'assets', 'budget_info',
            'invoice_date', 'invoice_no', 'licence_type', 'license_details',
            'manufacturer', 'niw', 'number_bought', 'order_no', 'parent',
            'price', 'property_of', 'provider', 'remarks', 'service_name',
            'sn', 'software_category', 'users', 'valid_thru',
        ]
        self.visible_edit_form_fields = self.visible_add_form_fields[:]

    def test_add_license(self):
        """
        Add license with all fields filled.

        - send the full license's data with post request
        - get saved license from db
        - asserts all db license's fields with request's data
        """
        request_data = self.license_data.copy()
        response = self.client.post(reverse('add_licence'), request_data)
        self.assertRedirects(
            response, reverse('licence_list'), status_code=302,
            target_status_code=200,
        )
        license = models_sam.Licence.objects.reverse()[0]
        check_fields(self, request_data.items(), license)

    def test_edit_license(self):
        """
        Edit license with all fields filled.
        - generate license data d1
        - create license l1
        - send data d1 via edit request to l1
        - get l1 from db
        - assert l1's data is the same as d1 data
        """
        new_license_data = self.license_data.copy()
        license = LicenceFactory()
        url = reverse('edit_licence', kwargs={
            'licence_id': license.id,
        })
        response = self.client.post(url, new_license_data)
        self.assertRedirects(
            response, url, status_code=302, target_status_code=200,
        )
        license = models_sam.Licence.objects.get(pk=license.id)
        check_fields(self, new_license_data.items(), license)

    def test_license_add_form_show_fields(self):
        required_fields = self.visible_add_form_fields[:]
        form_url = reverse('add_licence')
        self._assert_field_in_form(form_url, required_fields)

    def test_license_edit_form_show_fields(self):
        required_fields = self.visible_edit_form_fields[:]
        license = LicenceFactory()
        form_url = reverse(
            'edit_licence', kwargs={'licence_id': license.id},
        )
        self._assert_field_in_form(form_url, required_fields)

    def test_bulk_edit(self):
        num_of_licences = 10
        fields = [
            'accounting_id',
            'asset_type',
            'assets',
            'invoice_date',
            'invoice_no',
            'licence_type',
            'niw',
            'number_bought',
            'order_no',
            'parent',
            'price',
            'property_of',
            'provider',
            'remarks',
            'service_name',
            'sn',
            'software_category',
            'valid_thru',
        ]
        licences = [LicenceFactory() for _ in range(num_of_licences)]
        url = reverse('licence_bulkedit')
        url += '?' + '&'.join(['select={}'.format(obj.pk) for obj in licences])
        response = self.client.get(url, follow=True)

        for key in fields:
            self.assertIn(
                key, response.context['formset'][0].fields.keys()
            )

    def get_license_form_data(self):
        license = LicenceFactory()
        url = reverse('edit_licence', kwargs={
            'licence_id': license.id,
        })
        form_data = self.get_object_form_data(url, 'form')
        license.delete()
        return form_data

    def test_mulitvalues_behaviour(self):
        """
        - get add license request data d1

        - add licence with duplicated inv. nb. in data
        - assert error occured

        - edit licence with duplicated sn in data
        - assert licence was added
        """
        request_data = self.get_license_form_data()
        request_data.update(dict(
            # required, irrelevant data here
            parent='',
            sn=','.join([LicenceFactory.build().niw] * 3),
        ))
        url = reverse('add_licence')

        request_data['niw'] = ','.join([LicenceFactory.build().niw] * 3)
        response = self.client.post(url, request_data)
        self.assertFormError(
            response, 'form', 'niw', 'There are duplicates in field.',
        )
        request_data.update(dict(
            niw=','.join([LicenceFactory.build().niw for idx in xrange(3)]),
        ))
        response = self.client.post(url, request_data)
        self.assertEqual(response.status_code, 302)

    def test_licence_count_simple(self):
        number_of_users = 5
        number_of_assets = 5
        licences = [LicenceFactory() for idx in xrange(5)]
        licences[0].assets.add(
            *[BOAssetFactory() for _ in xrange(number_of_assets)]
        )
        licences[0].users.add(
            *[UserFactory() for _ in xrange(number_of_users)]
        )
        url = reverse('count_licences')
        url += '?id={}'.format(licences[0].id)
        response = self.client.ajax_get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content),
            {
                'used_by_users': number_of_users,
                'used_by_assets': number_of_assets,
                'total': licences[0].number_bought,
            },
        )

    def test_licence_count_all(self):
        licences = [LicenceFactory() for idx in xrange(5)]
        total = sum(models_sam.Licence.objects.values_list(
            'number_bought', flat=True)
        )
        for lic in licences:
            lic.assets.add(
                *[BOAssetFactory() for _ in xrange(5)]
            )
        for lic in licences:
            lic.users.add(
                *[UserFactory() for _ in xrange(5)]
            )
        url = reverse('count_licences')
        response = self.client.ajax_get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content),
            {
                'used_by_users': 25,
                'used_by_assets': 25,
                'total': total,
            },
        )


class TestSupportsView(BaseViewsTest):
    """This test case concern all supports views."""

    def setUp(self):
        super(TestSupportsView, self).setUp()
        SupportTypeFactory().id
        self.support_data = dict(
            additional_notes="Additional notes",
            # asset='',  # button, skip it
            asset_type=101,
            contract_id='1',
            contract_terms='Contract terms',
            date_from=datetime.date(2014, 06, 17),
            date_to=datetime.date(2014, 06, 18),
            description='Description',
            escalation_path='Escalation path',
            invoice_date=datetime.date(2014, 06, 19),
            invoice_no='Invoice no',
            name='name',
            period_in_months='12',
            price=Decimal('99.99'),
            producer='Producer',
            property_of=assets_utils.AssetOwnerFactory().id,
            serial_no='Serial no',
            sla_type='Sla type',
            status=models_support.SupportStatus.new.id,
            supplier='Supplier',
            support_type=SupportTypeFactory().id,
        )
        self.visible_add_form_fields = [
            'additional_notes', 'asset', 'asset_type', 'contract_id',
            'contract_terms', 'date_from', 'date_to', 'description',
            'escalation_path', 'invoice_date', 'invoice_no', 'name',
            'period_in_months', 'price', 'producer', 'property_of',
            'serial_no', 'sla_type', 'status', 'supplier', 'support_type',
        ]
        self.visible_edit_form_fields = self.visible_add_form_fields[:]
        self.visible_edit_form_fields.extend(['assets'])

    def _check_supports_assets(self, support, expected_assets):
        self.assertEqual(
            len(support.assets.all()), len(expected_assets),
        )
        del self.new_support_data['assets']

    def _update_with_supports(self, _dict):
        assets = [
            assets_utils.DCAssetFactory().id,
            assets_utils.BOAssetFactory().id,
        ]
        assets_values = '|{}|'.format('|'.join(map(str, assets)))
        _dict.update(dict(assets=assets_values))
        return assets

    def test_add_support(self):
        """
        Add support with all fields filled.

        - send the full support's data with post request
        - get saved support from db
        - asserts all db support's fields with request's data
        """
        request_data = self.support_data.copy()
        response = self.client.post(reverse('add_support'), request_data)
        self.assertRedirects(
            response, reverse('support_list'), status_code=302,
            target_status_code=200,
        )
        support = models_support.Support.objects.reverse()[0]
        check_fields(self, request_data.items(), support)

    def test_edit_support(self):
        """
        Edit support with all fields filled.
        - generate support data
        - create support
        - send data via edit request to
        - get from db
        - assert data is the same as data
        """

        self.new_support_data = self.support_data.copy()
        assets = self._update_with_supports(self.new_support_data)
        support = BOSupportFactory()
        url = reverse('edit_support', kwargs={
            'mode': 'back_office',
            'support_id': support.id,
        })
        response = self.client.post(url, self.new_support_data)
        self.assertRedirects(
            response, url, status_code=302, target_status_code=200,
        )
        support = models_support.Support.objects.get(pk=support.id)
        self._check_supports_assets(support, assets)
        check_fields(self, self.new_support_data.items(), support)

    def test_license_add_form_show_fields(self):
        required_fields = self.visible_add_form_fields[:]
        form_url = reverse('add_support')
        self._assert_field_in_form(form_url, required_fields)

    def test_license_edit_form_show_fields(self):
        required_fields = self.visible_edit_form_fields[:]
        test_data = (
            ('dc', DCSupportFactory()),
            ('back_office', BOSupportFactory()),
        )
        for mode, support in test_data:
            form_url = reverse(
                'edit_support',
                kwargs={'mode': mode, 'support_id': support.id},
            )
            self._assert_field_in_form(form_url, required_fields)


class TestAttachments(BaseViewsTest):
    """This test case concern all attachments views."""

    def test_cant_add_empty_attachment(self):
        """
        create asset a1
        send post with blank file
        assert that message about blank error exists
        """
        parent = BOAssetFactory()
        add_attachment_url = reverse('add_attachment', kwargs={
            'mode': 'back_office',
            'parent': 'asset',
        })
        full_url = "{}?{}".format(
            add_attachment_url,
            urlencode({'select': obj.id for obj in [parent]}),
        )
        with tempfile.TemporaryFile() as test_file:
            data = {
                "form-TOTAL_FORMS": 1,
                "form-INITIAL_FORMS": 1,
                "form-MAX_NUM_FORMS": 1,
                "form-0-file": test_file,
            }
            response = self.client.post(full_url, data, follow=True)
        self.assertIn(
            'The submitted file is empty.',
            response.context['formset'][0].errors['file'],
        )

    def test_add_bo_asset_attachment(self):
        add_attachment_url = reverse('add_attachment', kwargs={
            'mode': 'back_office',
            'parent': 'asset',
        })
        self.add_attachment(BOAssetFactory(), add_attachment_url)

    def test_add_dc_asset_attachment(self):
        add_attachment_url = reverse('add_attachment', kwargs={
            'mode': 'dc',
            'parent': 'asset',
        })
        self.add_attachment(DCAssetFactory(), add_attachment_url)

    def test_add_license_attachment(self):
        add_attachment_url = reverse('add_attachment', kwargs={
            'mode': 'back_office',  # TODO: to rm if modes are cleaned
            'parent': 'license',
        })
        self.add_attachment(LicenceFactory(), add_attachment_url)

    def test_add_support_attachment(self):
        add_attachment_url = reverse('add_attachment', kwargs={
            'mode': 'back_office',  # TODO: to rm if modes are cleaned
            'parent': 'support',
        })
        self.add_attachment(
            BOSupportFactory(),
            add_attachment_url,
        )

    def add_attachment(self, parent, add_attachment_url):
        """
        Checks if attachment can be added.
        """
        file_content = 'anything'
        full_url = "{}?{}".format(
            add_attachment_url,
            urlencode({'select': obj.id for obj in [parent]}),
        )

        asset = parent.__class__.objects.get(pk=parent.id)
        self.assertEqual(asset.attachments.count(), 0)

        with tempfile.TemporaryFile() as test_file:
            saved_filename = test_file.name
            test_file.write(file_content)
            test_file.seek(0)
            data = {
                "form-TOTAL_FORMS": 1,
                "form-INITIAL_FORMS": 1,
                "form-MAX_NUM_FORMS": 1,
                "form-0-file": test_file,
            }
            response = self.client.post(full_url, data, follow=True)

        self.assertEqual(response.status_code, 200)
        asset = parent.__class__.objects.get(pk=parent.id)
        self.assertEqual(asset.attachments.count(), 1)
        attachment = asset.attachments.all()[0]
        self.assertEqual(attachment.original_filename, saved_filename)
        with attachment.file as attachment_file:
            self.assertEqual(attachment_file.read(), file_content)

    def test_delete_one_bo_asset_attachment(self):
        self.delete_attachment_check(
            mode='back_office',
            parent_name='asset',
            parents=[BOAssetFactory()],
            delete_type='from_one',
        )

    def test_delete_one_bo_licence_attachment(self):
        self.delete_attachment_check(
            mode='back_office',
            parent_name='license',
            parents=[LicenceFactory()],
            delete_type='from_one',
        )

    def test_delete_one_bo_support_attachment(self):
        self.delete_attachment_check(
            mode='back_office',
            parent_name='support',
            parents=[BOSupportFactory()],
            delete_type='from_one',
        )

    def test_delete_all_bo_asset_attachment(self):
        self.delete_attachment_check(
            mode='back_office',
            parent_name='asset',
            parents=[BOAssetFactory(), BOAssetFactory(), BOAssetFactory()],
            delete_type='from_all',
        )

    def test_delete_all_bo_licence_attachment(self):
        self.delete_attachment_check(
            mode='back_office',
            parent_name='license',
            parents=[LicenceFactory(), LicenceFactory(), LicenceFactory()],
            delete_type='from_all',
        )

    def test_delete_all_bo_support_attachment(self):
        self.delete_attachment_check(
            mode='back_office',
            parent_name='support',
            parents=[
                BOSupportFactory(), BOSupportFactory(), BOSupportFactory(),
            ],
            delete_type='from_all',
        )

    def test_delete_one_dc_asset_attachment(self):
        self.delete_attachment_check(
            mode='dc',
            parent_name='asset',
            parents=[DCAssetFactory()],
            delete_type='from_one',
        )

    def test_delete_one_dc_licence_attachment(self):
        self.delete_attachment_check(
            mode='dc',
            parent_name='license',
            parents=[LicenceFactory()],
            delete_type='from_one',
        )

    def test_delete_one_dc_support_attachment(self):
        self.delete_attachment_check(
            mode='dc',
            parent_name='support',
            parents=[DCSupportFactory()],
            delete_type='from_one',
        )

    def test_delete_all_dc_asset_attachment(self):
        self.delete_attachment_check(
            mode='dc',
            parent_name='asset',
            parents=[DCAssetFactory(), DCAssetFactory(), DCAssetFactory()],
            delete_type='from_all',
        )

    def test_delete_all_dc_licence_attachment(self):
        self.delete_attachment_check(
            mode='dc',
            parent_name='license',
            parents=[LicenceFactory(), LicenceFactory(), LicenceFactory()],
            delete_type='from_all',
        )

    def test_delete_all_dc_support_attachment(self):
        self.delete_attachment_check(
            mode='dc',
            parent_name='support',
            parents=[
                DCSupportFactory(), DCSupportFactory(), DCSupportFactory(),
            ],
            delete_type='from_all',
        )

    def delete_attachment_check(
        self, mode, parent_name, parents, delete_type
    ):
        attachment = AttachmentFactory()
        for parent in parents:
            parent.attachments.add(attachment)
            parent.save()

        parent = parents[0]  # each one is suitable, so take the first
        full_url = reverse('delete_attachment', kwargs={
            'mode': mode,
            'parent': parent_name,
        })
        data = {
            'parent_id': parent.id,
            'attachment_id': attachment.id,
            'delete_type': delete_type,
        }

        for parent in parents:
            self.assertIn(attachment, parent.attachments.all())
        response = self.client.post(full_url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        for parent in parents:
            self.assertNotIn(
                attachment,
                parent.attachments.filter(pk=attachment.id),
            )


class DeviceEditViewTest(ClientMixin, TestCase):

    def setUp(self):
        self.login_as_superuser()
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


class TestImport(ClientMixin, TestCase):
    def setUp(self):
        self.login_as_superuser()
        self.url = reverse('xls_upload')

    def _update_asset_by_csv(self, asset, field, value):
        self.client.get(self.url)
        csv_data = '"id","{}"\n"{}","{}"'.format(field, asset.id, value)

        step1_post = {
            'upload-asset_type': models_sam.AssetType.back_office.id,
            'upload-model': 'ralph_assets.asset',
            'upload-file': SimpleUploadedFile('test.csv', csv_data),
            'xls_upload_view-current_step': 'upload',
        }
        response = self.client.post(self.url, step1_post)
        self.assertContains(response, 'column_choice')
        self.assertContains(response, 'step 2/3')

        step2_post = {
            'column_choice-%s' % field: field,
            'xls_upload_view-current_step': 'column_choice',
        }
        response = self.client.post(self.url, step2_post)
        self.assertContains(response, 'step 3/3')

        step3_post = {
            'xls_upload_view-current_step': 'confirm',
        }
        response = self.client.post(self.url, step3_post)
        self.assertContains(response, 'Import done')

    def test_import_csv_asset_back_office_update(self):
        self.client.get(self.url)
        asset = BOAssetFactory()

        for field in [
            'barcode', 'invoice_no', 'order_no', 'sn', 'remarks', 'niw'
        ]:
            new_value = str(uuid.uuid1())
            self._update_asset_by_csv(asset, field, new_value)
            updated_asset = models_assets.Asset.objects.get(id=asset.id)
            self.assertEqual(
                getattr(updated_asset, field), new_value
            )


class TestColumnsInSearch(BaseViewsTest):

    def get_cols_by_mode(self, bob_cols, mode):
        mode_cols = set()
        for col in bob_cols:
            if not col.bob_tag:
                continue
            if (col.show_conditions is True) or (
                isinstance(col.show_conditions, tuple)
                and col.show_conditions[1] == mode
            ):
                mode_cols.add(col.header_name)
        return mode_cols

    def check_cols_presence(self, search_url, correct_col_names, mode):
        """
        Checks if bob table has all required columns.
        :parma search_url: url where bob table occures,
        :parma correct_col_names: sequence of expected column names,
        :parma mode: filtering mode comapared with
            bob_table.col.show_conditions, which is 'dc' or 'back_office'
        """
        response = self.client.get(search_url)
        self.assertEqual(response.status_code, 200)
        if mode:
            found_cols = self.get_cols_by_mode(
                response.context_data['columns'], mode
            )
        else:
            found_cols = [
                unicode(col.header_name)
                for col in response.context_data['columns']
            ]
        self.assertEqual(len(found_cols), len(correct_col_names))
        for correct_field in correct_col_names:
            self.assertIn(correct_field, found_cols)

    def test_bo_cols_presence(self):
        BOAssetFactory()
        correct_col_names = set([
            'Additional remarks', 'Barcode', 'Category', 'Dropdown',
            'Hostname', 'IMEI', 'Invoice date', 'Invoice no.', 'Manufacturer',
            'Model', 'Property of', 'SN', 'Service name', 'Status', 'Type',
            'User', 'Warehouse',
        ])
        mode = 'back_office'
        search_url = reverse('asset_search', kwargs={'mode': mode})
        self.check_cols_presence(search_url, correct_col_names, mode)

    def test_dc_cols_presence(self):
        DCAssetFactory()
        correct_col_names = set([
            'Barcode', 'Discovered', 'Dropdown', 'Invoice date',
            'Invoice no.', 'Model', 'Order no.', 'Price', 'SN', 'Status',
            'Type', 'Venture', 'Warehouse',
        ])
        mode = 'dc'
        search_url = reverse('asset_search', kwargs={'mode': mode})
        self.check_cols_presence(search_url, correct_col_names, mode)

    def test_license_cols_presence(self):
        LicenceFactory()
        correct_col_names = set([
            'Dropdown', 'Inventory number', 'Invoice date', 'Invoice no.',
            'Licence Type', 'Manufacturer', 'Number of purchased items',
            'Property of', 'Software Category', 'Type', 'Used', 'Valid thru',
        ])
        search_url = reverse('licence_list')
        self.check_cols_presence(search_url, correct_col_names, mode=None)

    def test_supports_cols_presence(self):
        DCSupportFactory()
        correct_col_names = set([
            'Dropdown', 'Type', 'Contract id', 'Name', 'Date from', 'Date to',
            'Price',
        ])
        search_url = reverse('support_list')
        self.check_cols_presence(search_url, correct_col_names, mode=None)
