# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import random
from factory import Sequence, SubFactory, lazy_attribute
from factory.django import DjangoModelFactory as Factory
from uuid import uuid1

from django.template.defaultfilters import slugify

from ralph_assets.models_assets import (
    Asset,
    AssetCategory,
    AssetCategoryType,
    AssetManufacturer,
    AssetModel,
    AssetOwner,
    AssetPurpose,
    AssetStatus,
    AssetSource,
    AssetType,
    DeviceInfo,
    OfficeInfo,
    Service,
    Warehouse,
)


def generate_imei(n):
    """Random IMEI generator. This function return random but not unique
    IMEI number. Based on code from http://stackoverflow.com/a/20733310
    """
    def luhn_residue(digits):
        """Luhn algorithm"""
        return sum(sum(divmod(int(d) * (1 + i % 2), 10))
                   for i, d in enumerate(digits[::-1])) % 10

    part = ''.join(str(random.randrange(0, 9)) for _ in range(n - 1))
    res = luhn_residue('{}{}'.format(part, 0))
    return '{}{}'.format(part, -res % 10)


class OfficeInfoFactory(Factory):
    FACTORY_FOR = OfficeInfo

    imei = generate_imei(15)
    purpose = AssetPurpose.others

    @lazy_attribute
    def license_key(self):
        return str(uuid1())

    @lazy_attribute
    def coa_number(self):
        return str(uuid1())


class ServiceFactory(Factory):
    FACTORY_FOR = Service

    name = Sequence(lambda n: 'Service #%s' % n)


class AssetOwnerFactory(Factory):
    FACTORY_FOR = AssetOwner

    name = Sequence(lambda n: 'Asset owner #%s' % n)


class AssetCategoryFactory(Factory):
    FACTORY_FOR = AssetCategory

    name = Sequence(lambda n: 'Asset category #%s' % n)
    type = AssetCategoryType.back_office

    @lazy_attribute
    def slug(self):
        return slugify(str(self.type) + self.name)


class AssetSubCategoryFactory(AssetCategoryFactory):
    parent = SubFactory(AssetCategoryFactory)

    @lazy_attribute
    def slug(self):
        return slugify(str(self.type) + self.name + self.parent.name)


class AssetManufacturerFactory(Factory):
    FACTORY_FOR = AssetManufacturer

    name = Sequence(lambda n: 'Manufacturer #%s' % n)


class AssetModelFactory(Factory):
    FACTORY_FOR = AssetModel

    name = Sequence(lambda n: 'Model #%s' % n)
    type = AssetCategoryType.back_office
    manufacturer = SubFactory(AssetManufacturerFactory)


class WarehouseFactory(Factory):
    FACTORY_FOR = Warehouse

    name = Sequence(lambda n: 'Warehouse #%s' % n)


class DeviceInfoFactory(Factory):
    FACTORY_FOR = DeviceInfo

    u_level = random.randint(0, 100)
    u_height = random.randint(0, 100)
    rack = Sequence(lambda n: 'Rack #%s' % n)


class AssetFactory(Factory):
    FACTORY_FOR = Asset

    type = AssetType.data_center
    model = SubFactory(AssetModelFactory)
    status = AssetStatus.new
    source = AssetSource.shipment
    model = SubFactory(AssetModelFactory)
    warehouse = SubFactory(WarehouseFactory)
    device_info = SubFactory(DeviceInfoFactory)
    provider = Sequence(lambda n: 'Provider #%s' % n)
    support_period = 24
    support_type = 'standard'

    @lazy_attribute
    def sn(self):
        return str(uuid1())


class AssetBOFactory(AssetFactory):
    type = AssetType.back_office
    office_info = SubFactory(OfficeInfoFactory)
