# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime

from factory import (
    fuzzy,
    Sequence,
    SubFactory,
    lazy_attribute,
    post_generation,
)
from factory.django import DjangoModelFactory as Factory
from random import randint
from uuid import uuid1

from ralph_assets.models_assets import AssetType
from ralph_assets.models_sam import (
    Licence,
    LicenceType,
    SoftwareCategory,
)
from ralph_assets.tests.utils.assets import (
    AssetManufacturerFactory,
    AssetOwnerFactory,
    BudgetInfoFactory,
    ServiceFactory,
    UserFactory,
)


class LicenceTypeFactory(Factory):
    FACTORY_FOR = LicenceType

    name = Sequence(lambda n: 'Licence type #%s' % n)


class SoftwareCategoryFactory(Factory):
    FACTORY_FOR = SoftwareCategory

    name = Sequence(lambda n: 'Software category #%s' % n)
    asset_type = AssetType.BO


class LicenceFactory(Factory):
    FACTORY_FOR = Licence
    accounting_id = ''
    asset_type = AssetType.back_office.id
    # assets: probabbly it should be set as kwargs during creation?
    budget_info = SubFactory(BudgetInfoFactory)
    invoice_date = fuzzy.FuzzyDate(datetime.date(2008, 1, 1))
    invoice_no = Sequence(lambda n: 'INVOICE-NUMBER-%s' % n)
    licence_type = SubFactory(LicenceTypeFactory)
    license_details = Sequence(lambda n: 'Licence-details-%s' % n)
    manufacturer = SubFactory(AssetManufacturerFactory)
    number_bought = 5
    order_no = Sequence(lambda n: 'ORDER-NUMBER-%s' % n)
    parent = None
    price = 0
    property_of = SubFactory(AssetOwnerFactory)
    provider = ''
    remarks = ''
    service_name = SubFactory(ServiceFactory)
    software_category = SubFactory(SoftwareCategoryFactory)
    users = None
    valid_thru = fuzzy.FuzzyDate(datetime.date(2008, 1, 1))

    @lazy_attribute
    def niw(self):
        return str(uuid1())

    @post_generation
    def users(self, create, extracted, **kwargs):
        if not create:
            return None
        return [UserFactory() for i in range(randint(1, 8))]

    @lazy_attribute
    def sn(self):
        return str(uuid1())
