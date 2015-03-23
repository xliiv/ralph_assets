# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from factory import (
    Sequence,
    SubFactory,
    fuzzy,
    lazy_attribute,
    post_generation,
)
from factory.django import DjangoModelFactory
from ralph.cmdb.tests.utils import (
    CIRelationFactory,
    DeviceEnvironmentFactory,
    ServiceCatalogFactory,
)

from ralph_assets.models_parts import Part, PartModel, PartModelType
from ralph_assets.tests.utils.assets import (
    DCAssetFactory,
    AssetType,
    unique_str,
    WarehouseFactory,
)


class PartModelFactory(DjangoModelFactory):
    FACTORY_FOR = PartModel

    model_type = PartModelType.disk
    name = Sequence(lambda n: 'PartModel #%s' % n)


class PartFactory(DjangoModelFactory):
    FACTORY_FOR = Part

    asset = SubFactory(DCAssetFactory)
    asset_type = AssetType.data_center
    model = SubFactory(PartModelFactory)
    order_no = Sequence(lambda n: 'Order no #{}'.format(n))
    price = fuzzy.FuzzyDecimal(0, 100)
    service = SubFactory(ServiceCatalogFactory)
    part_environment = SubFactory(DeviceEnvironmentFactory)
    warehouse = SubFactory(WarehouseFactory)

    @lazy_attribute
    def sn(self):
        return unique_str()

    @post_generation
    def part_environment(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            self.device_environment = extracted
        else:
            if self.service:
                ci_relation = CIRelationFactory(parent=self.service)
                self.part_environment = ci_relation.child
