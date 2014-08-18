# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from django.test import TestCase

from ralph.business.models import Venture
from ralph.discovery.models_device import Device, DeviceType
from ralph.ui.tests.global_utils import login_as_su
from ralph_assets.models_assets import AssetCategory
from ralph_assets.tests.utils.assets import (
    AssetModelFactory,
    BOAssetFactory,
    DCAssetFactory,
)
from ralph_assets.views.report import (
    CategoryModelReport,
    CategoryModelStatusReport,
    LinkedDevicesReport,
)


SAVE_PRIORITY = 255


class TestReportCategoryTreeView(TestCase):
    """
    sdas"""
    def setUp(self):
        self.client = login_as_su()
        self._create_models()
        self._create_assets()

    def _create_models(self):
        self.keyboard_model = AssetModelFactory(
            category=AssetCategory.objects.get(name="Keyboard")
        )
        self.mouse_model = AssetModelFactory(
            category=AssetCategory.objects.get(name="Mouse")
        )
        self.pendrive_model = AssetModelFactory(
            category=AssetCategory.objects.get(name="Pendrive")
        )

        self.model_monitor = AssetModelFactory(
            category=AssetCategory.objects.get(name="Monitor")
        )
        self.navigation_model = AssetModelFactory(
            category=AssetCategory.objects.get(name="Navigation")
        )
        self.scanner_model = AssetModelFactory(
            category=AssetCategory.objects.get(name="Scanner")
        )
        self.shredder_model = AssetModelFactory(
            category=AssetCategory.objects.get(name="Shredder")
        )

    def _create_assets(self):
        [BOAssetFactory(**{'model': self.keyboard_model}) for _ in xrange(6)]
        [BOAssetFactory(**{'model': self.mouse_model}) for _ in xrange(2)]
        [BOAssetFactory(**{'model': self.pendrive_model}) for _ in xrange(2)]

        [BOAssetFactory(**{'model': self.model_monitor}) for _ in xrange(2)]
        [BOAssetFactory(**{'model': self.navigation_model}) for _ in xrange(2)]
        [BOAssetFactory(**{'model': self.scanner_model}) for _ in xrange(3)]
        [BOAssetFactory(**{'model': self.shredder_model}) for _ in xrange(3)]

    def _get_item(self, data, name):
        for item in data:
            if item['name'] == name:
                return item
        return None

    def _get_report(self, report_class, mode=None):
        report = report_class()
        report.execute(None)
        return report.report.to_dict()

    def test_category_model_tree(self):
        report = self._get_report(CategoryModelReport)

        self.assertEqual(self._get_item(report, 'Keyboard')['count'], 6)
        self.assertEqual(self._get_item(report, 'Mouse')['count'], 2)
        self.assertEqual(self._get_item(report, 'Pendrive')['count'], 2)

        self.assertEqual(self._get_item(report, 'Monitor')['count'], 2)
        self.assertEqual(self._get_item(report, 'Navigation')['count'], 2)
        self.assertEqual(self._get_item(report, 'Scanner')['count'], 3)
        self.assertEqual(self._get_item(report, 'Shredder')['count'], 3)

    def test_category_model_status_tree(self):
        report = self._get_report(CategoryModelStatusReport)

        item = self._get_item(report, 'Keyboard')['children'][0]['children']
        self.assertEqual(item[0]['count'], 6)
        item = self._get_item(report, 'Mouse')['children'][0]['children']
        self.assertEqual(item[0]['count'], 2)
        item = self._get_item(report, 'Pendrive')['children'][0]['children']
        self.assertEqual(item[0]['count'], 2)

        item = self._get_item(report, 'Monitor')['children'][0]['children']
        self.assertEqual(item[0]['count'], 2)
        item = self._get_item(report, 'Navigation')['children'][0]['children']
        self.assertEqual(item[0]['count'], 2)
        item = self._get_item(report, 'Scanner')['children'][0]['children']
        self.assertEqual(item[0]['count'], 3)
        item = self._get_item(report, 'Shredder')['children'][0]['children']
        self.assertEqual(item[0]['count'], 3)


class TestReportLinked(TestCase):

    def create_device(self, sn, barcode):
        venture, _ = Venture.objects.get_or_create(
            name='TestVenture',
            symbol='testventure'
        )
        return Device.create(
            sn=sn,
            barcode=barcode,
            model_name='test_model',
            model_type=DeviceType.unknown,
            priority=SAVE_PRIORITY,
            venture=venture,
            name='test_device',
        )

    def test_report_linked_empty_report(self):
        assets = [DCAssetFactory() for _ in xrange(3)]
        for asset in assets:
            device = self.create_device(
                sn=asset.sn,
                barcode=asset.barcode
            )
            asset.device_info.ralph_device_id = device.id
            asset.device_info.save()

        report = LinkedDevicesReport()
        result = report.execute(None)
        self.assertEqual(len(result), 1)

    def test_report_linked_report(self):
        assets = [DCAssetFactory() for _ in xrange(6)]
        for asset in assets:
            self.create_device(
                sn=asset.sn,
                barcode=asset.barcode
            )
            asset.device_info.ralph_device_id = None
            asset.device_info.save()

        report = LinkedDevicesReport()
        results = report.execute(None)
        self.assertEqual(len(results), 3)
