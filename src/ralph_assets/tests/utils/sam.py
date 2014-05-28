# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from factory import (
    SubFactory,
    Sequence,
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
from ralph_assets.tests.utils import UserFactory
from ralph_assets.tests.utils.assets import ServiceFactory


class LicenceTypeFactory(Factory):
    FACTORY_FOR = LicenceType

    name = Sequence(lambda n: 'Licence type #%s' % n)


class SoftwareCategoryFactory(Factory):
    FACTORY_FOR = SoftwareCategory

    name = Sequence(lambda n: 'Software category #%s' % n)
    asset_type = AssetType.BO


class LicenceFactory(Factory):
    FACTORY_FOR = Licence

    number_bought = randint(0, 150)
    sn = str(uuid1())
    parent = None
    niw = str(uuid1())
    invoice_date = None
    invoice_no = Sequence(lambda n: 'INVOICE-NUMBER-%s' % n)
    valid_thru = None
    order_no = Sequence(lambda n: 'ORDER-NUMBER-%s' % n)
    price = 0
    accounting_id = ''
    asset_type = AssetType.BO
    provider = ''
    remarks = ''
    software_category = SubFactory(SoftwareCategoryFactory)
    licence_type = SubFactory(LicenceTypeFactory)
    service_name = SubFactory(ServiceFactory)

    @post_generation
    def users(self, create, extracted, **kwargs):
        if not create:
            return None
        return [UserFactory() for i in range(randint(1, 8))]
