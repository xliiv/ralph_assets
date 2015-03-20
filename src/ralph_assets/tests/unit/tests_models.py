# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime
import itertools as it
from datetime import timedelta
from unittest import skip

import factory
from django.test import TestCase

from ralph.business.models import Venture
from ralph.discovery.models_device import Device, DeviceType

from ralph.discovery.tests.util import DeviceModelFactory
from ralph_assets.api_pricing import get_assets, get_asset_parts
from ralph_assets.models_assets import AssetStatus, PartInfo, Rack
from ralph_assets.models_dc_assets import (
    DeprecatedRalphDC,
    DeprecatedRalphRack,
)
from ralph_assets.licences.models import LicenceAsset, Licence, WrongModelError
from ralph_assets.tests.utils.assets import (
    AssetSubCategoryFactory,
    AssetModelFactory,
    AssetFactory,
    DCAssetFactory,
    DeviceInfoFactory,
    RackFactory,
    ServiceFactory,
)
from ralph_assets.tests.utils.supports import DCSupportFactory
from ralph_assets.tests.utils.licences import LicenceFactory


class TestModelAsset(TestCase):
    def setUp(self):
        self.asset = AssetFactory(
            invoice_date=datetime.date(2012, 11, 28),
            support_period=1,
            deprecation_rate=100,
        )
        self.asset.device_info.ralph_device_id = 666
        self.asset.device_info.save()
        self.asset2 = AssetFactory(
            invoice_date=datetime.date(2012, 11, 28),
            support_period=120,
            deprecation_rate=50,
        )
        self.asset2.device_info.ralph_device_id = 667
        self.asset2.device_info.save()
        self.asset3 = AssetFactory(
            invoice_date=datetime.date(2012, 11, 28),
            support_period=120,
            deprecation_rate=50,
            force_deprecation=True,
        )
        self.asset_depr_date = AssetFactory(
            sn='1111-1111-1111-1114',
            invoice_date=datetime.date(2012, 11, 28),
            support_period=120,
            deprecation_rate=50,
            deprecation_end_date=datetime.date(2014, 12, 15),
        )
        self.dev1 = Device.create(
            [('1', 'sda', 0)],
            model_name='xxx',
            model_type=DeviceType.rack_server,
            allow_stub=1,
        )
        self.dev1.id = 666
        self.dev1.save()
        dev2 = Device.create(
            [('1', 'dawdwad', 0)],
            model_name='Unknown',
            model_type=DeviceType.unknown,
            allow_stub=1,
        )
        dev2.id = 667
        dev2.save()

    def test_is_discovered(self):
        self.assertEqual(self.asset.is_discovered, True)
        self.assertEqual(self.asset2.is_discovered, False)
        self.assertEqual(self.asset3.is_discovered, False)

    def test_is_deperecated(self):
        date = datetime.date(2014, 03, 29)
        self.assertEqual(self.asset.get_deprecation_months(), 12)
        self.assertEqual(self.asset2.get_deprecation_months(), 24)
        self.assertEqual(self.asset.is_deprecated(date), True)
        self.assertEqual(self.asset2.is_deprecated(date), False)
        self.assertEqual(self.asset3.is_deprecated(date), True)
        self.assertEqual(
            self.asset_depr_date.is_deprecated(datetime.date(2014, 12, 10)),
            False,
        )
        self.assertEqual(
            self.asset_depr_date.is_deprecated(datetime.date(2014, 12, 20)),
            True,
        )

    def test_asset_is_liquidated(self):
        date = datetime.date.today()
        self.assertFalse(self.asset.is_liquidated(date))

        self.asset.status = AssetStatus.liquidated
        self.asset.save()

        self.assertTrue(self.asset.is_liquidated(date + timedelta(days=1)))
        self.assertTrue(self.asset.is_liquidated(date))
        self.assertFalse(self.asset.is_liquidated(date + timedelta(days=-1)))

    def test_asset_reverted_from_liquidated_state(self):
        date = datetime.date.today()
        self.asset.status = AssetStatus.liquidated
        self.asset.save()
        self.asset.status = AssetStatus.used
        self.asset.save()
        self.assertFalse(self.asset.is_liquidated(date + timedelta(days=1)))
        self.assertFalse(self.asset.is_liquidated(date))
        self.assertFalse(self.asset.is_liquidated(date + timedelta(days=-1)))

    def test_venture(self):
        venture = Venture.objects.create(name='v1')
        self.dev1.venture = venture
        self.dev1.save()

        asset_without_device = AssetFactory(device_info=None)

        self.assertEqual(self.asset.venture, venture)
        self.assertEqual(self.asset2.venture, None)
        self.assertEqual(asset_without_device.venture, None)

    def test_in_use_status(self):
        self.assertEqual(AssetStatus.used.desc, 'in use')


class TestModelLicences(TestCase):
    def setUp(self):
        self.licence = LicenceFactory()

    def test_remarks(self):
        """Remarks field is in model?"""
        self.licence.remarks = 'a' * 512
        self.licence.save()

        self.assertEqual(self.licence.remarks, 'a' * 512)

    def test_service_name(self):
        old_service = self.licence.service_name
        self.licence.service_name = ServiceFactory()
        self.licence.save()

        self.assertNotEqual(old_service, self.licence.service_name)

    def test_assign_asset_to_licence(self):
        """Simple assign asset to licence."""
        asset = AssetFactory()
        self.licence.assign(obj=asset)
        self.assertEqual(LicenceAsset.objects.all().count(), 1)
        self.assertEqual(LicenceAsset.objects.all()[0].quantity, 1)
        self.assertEqual(self.licence.used, 1)

    def test_assign_asset_to_support(self):
        """Assign not supported object to licence."""
        asset = DCSupportFactory()
        with self.assertRaises(WrongModelError):
            self.licence.assign(obj=asset)

    def test_assign_asset_to_licence_zero_quantity(self):
        """Simple assign asset to licence with zero quantity."""
        asset = AssetFactory()
        with self.assertRaises(ValueError):
            self.licence.assign(obj=asset, quantity=0)

    def test_update_assign_asset_to_licence(self):
        """Simple update assign asset to licence."""
        asset = AssetFactory()
        self.licence.assign(obj=asset)
        self.assertEqual(LicenceAsset.objects.all().count(), 1)
        self.assertEqual(LicenceAsset.objects.all()[0].quantity, 1)
        self.assertEqual(self.licence.used, 1)

        self.licence = Licence.objects.get(pk=self.licence.pk)
        self.licence.assign(obj=asset, quantity=10)
        self.assertEqual(LicenceAsset.objects.all().count(), 1)
        self.assertEqual(LicenceAsset.objects.all()[0].quantity, 10)
        self.assertEqual(self.licence.used, 10)

    def test_assign_asset_to_licence_custom_number_of_used(self):
        """Simple assign asset to licence with custom number of used."""
        asset = AssetFactory()
        consume_by_asset = 5
        self.licence.assign(obj=asset, quantity=consume_by_asset)
        self.assertEqual(LicenceAsset.objects.all().count(), 1)
        self.assertEqual(
            LicenceAsset.objects.all()[0].quantity, consume_by_asset
        )
        self.assertEqual(self.licence.used, consume_by_asset)

    def test_detach(self):
        """Detach asset from licence."""
        asset = AssetFactory()
        self.licence.assign(obj=asset)
        self.licence.detach(obj=asset)
        self.assertEqual(LicenceAsset.objects.all().count(), 0)
        self.assertEqual(self.licence.used, 0)

    def test_detach_does_not_exist(self):
        """Detach asset from licence but licence doesn't assgin to asset."""
        asset = AssetFactory()
        self.licence.detach(obj=asset)
        self.assertEqual(LicenceAsset.objects.all().count(), 0)
        self.assertEqual(self.licence.used, 0)

    @skip('TODO: implementation limit of licences')
    def test_reached_free_limit(self):
        """All licences is assigned."""
        asset = AssetFactory()
        asset2 = AssetFactory()
        self.licence.number_bought = 25
        self.licence.save()
        self.licence.assign(obj=asset, quantity=self.licence.number_bought)
        self.assertEqual(self.licence.used, self.licence.number_bought)
        self.assertEqual(self.licence.free, 0)

        with self.assertRaises(Exception):
            self.licence.assign(obj=asset2, quantity=1)


class TestApiAssets(TestCase):
    def setUp(self):
        self.category = AssetSubCategoryFactory(is_blade=True)
        self.model = AssetModelFactory(category=self.category)
        self.asset = AssetFactory(
            invoice_date=datetime.date(2012, 11, 28),
            support_period=1,
            slots=12.0,
            price=100,
            deprecation_rate=100,
            model=self.model,
        )
        part_info = PartInfo(device=self.asset)
        part_info.save()
        self.asset2 = AssetFactory(
            invoice_date=datetime.date(2012, 11, 28),
            support_period=1,
            slots=12.0,
            price=100,
            part_info=part_info,
            deprecation_rate=50,
            model=self.model,
        )
        self.stock_venture = Venture.objects.get(name='Stock')

    def tests_api_asset(self):
        date = datetime.date(2014, 03, 29)
        for item in get_assets(date):
            self.assertEqual(item['asset_id'], self.asset.id)
            self.assertEqual(
                item['ralph_id'], self.asset.device_info.ralph_device_id,
            )
            self.assertEqual(item['slots'], self.asset.slots)
            self.assertEqual(item['price'], self.asset.price)
            self.assertEqual(
                item['is_deprecated'],
                self.asset.is_deprecated(date)
            )
            self.assertEqual(item['sn'], self.asset.sn)
            self.assertEqual(item['barcode'], self.asset.barcode)
            self.assertEqual(item['venture_id'], self.stock_venture.id)
            self.assertEqual(item['is_blade'], self.category.is_blade)
            self.assertEqual(item['cores_count'], self.asset.cores_count)

    def tests_api_asset_part(self):
        for item in get_asset_parts():
            self.assertEqual(item['price'], 100)
            # self.assertEqual(item['is_deprecated'], False)
            model = self.model
            self.assertEqual(item['model'], model.name)
            self.assertEqual(item['asset_id'], self.asset2.id)
            self.assertEqual(item['sn'], self.asset.sn)
            self.assertEqual(item['barcode'], self.asset.barcode)


class TestModelHistory(TestCase):

    def test_asset(self):
        asset = AssetFactory(pk=123)
        history = asset.get_history()
        self.assertEqual(0, history.count())

        asset.sn = '123'
        asset.save()
        self.assertEqual(1, history.count())

        asset.sn = '1233'
        asset.save()
        self.assertEqual(2, history.count())

        licence = LicenceFactory()
        history = licence.get_history()
        # dry saves
        licence.save()
        licence.save()
        self.assertEqual(0, history.count())
        history = asset.get_history()

        for i in xrange(5):
            self.assertEqual(i + 2, history.count())
            licence.assign(asset, i + 1)
            self.assertEqual(i + 3, history.count())


class BladeDeviceInfoFactory(DeviceInfoFactory):
    """Creates DeviceInfo for elements in a blade system"""
    slot_no = factory.Iterator(it.count(1))


class BladeAssetFactory(DCAssetFactory):
    """Creates Assets in a blade system"""
    device_info = factory.SubFactory(BladeDeviceInfoFactory)


def ab_iterator():
    for i in it.count(1):
        yield str(i) + 'A'
        yield str(i) + 'B'


class BladeDeviceInfoABFactory(DeviceInfoFactory):
    """Creates DeviceInfo for elements in a blade system (AB mode)"""
    slot_no = factory.Iterator(ab_iterator())


class BladeAssetABFactory(DCAssetFactory):
    """Creates Assets in a blade system (AB mode)"""
    device_info = factory.SubFactory(BladeDeviceInfoABFactory)


class TestModelRack(TestCase):
    def test_free_u(self):
        rack = RackFactory()
        rack = Rack.objects.with_free_u()[0]
        rack_height = 48
        self.assertEqual(rack.free_u, rack_height)

        # mount 2U device to rack
        asset_count = 10
        model_height = 2
        model = AssetModelFactory(height_of_device=model_height)
        [
            DCAssetFactory(
                device_info__rack=rack, model=model, device_info__slot_no=''
            )
            for _ in range(asset_count)
        ]
        rack = Rack.objects.with_free_u()[0]
        self.assertEqual(
            rack.free_u, rack_height - (asset_count * model_height)
        )

    def test_chassis_returns_childre_with_gaps(self):
        position = 3
        rack = RackFactory()
        chassis = DCAssetFactory(
            device_info__rack=rack,
            device_info__position=position,
            model__height_of_device=10,
        )
        blades = BladeAssetFactory.create_batch(
            5,
            device_info__rack=rack,
            device_info__position=position,
            model__category__is_blade=True,
        )
        # Create a gap
        blades[2].delete()
        BladeAssetFactory.create_batch(
            4,
            device_info__position=position,
            model__category__is_blade=True,
        )
        children = chassis.get_related_assets()
        self.assertEqual(len(children), 5)
        self.assertIn(
            ('3', '-'),
            {
                (asset.device_info.slot_no, asset.model.name)
                for asset in children
            }
        )

    def test_chassis_returns_childre_with_gaps_ab(self):
        position = 3
        rack = RackFactory()
        chassis = DCAssetFactory(
            device_info__rack=rack,
            device_info__position=position,
            model__height_of_device=10,
        )
        blades = BladeAssetABFactory.create_batch(
            5,
            device_info__rack=rack,
            device_info__position=position,
            model__category__is_blade=True,
        )
        # Create a gap
        blades[2].delete()
        BladeAssetABFactory.create_batch(
            4,
            device_info__position=position,
            model__category__is_blade=True,
        )
        children = chassis.get_related_assets()
        self.assertEqual(len(children), 6)
        self.assertIn(
            ('2A', '-'),
            {
                (asset.device_info.slot_no, asset.model.name)
                for asset in children
            }
        )


class TestModelDeprecatedDataCenter(TestCase):

    def test_create(self):
        model = DeviceModelFactory(type=DeviceType.data_center)
        self.assertTrue(DeprecatedRalphDC.create(name='DC', model=model))

    def test_create_without_model(self):
        with self.assertRaises(ValueError):
            DeprecatedRalphDC.create(name='DC')

    def test_create_with_incorrect_model(self):
        model = DeviceModelFactory()
        with self.assertRaises(ValueError):
            DeprecatedRalphDC.create(name='DC', model=model)


class TestModelDeprecatedRack(TestCase):

    def test_create(self):
        model = DeviceModelFactory(type=DeviceType.rack)
        self.assertTrue(DeprecatedRalphRack.create(name='Rack', model=model))

    def test_create_without_model(self):
        with self.assertRaises(ValueError):
            DeprecatedRalphRack.create(name='Rack')

    def test_create_with_incorrect_model(self):
        model = DeviceModelFactory()
        with self.assertRaises(ValueError):
            DeprecatedRalphRack.create(name='Rack', model=model)
