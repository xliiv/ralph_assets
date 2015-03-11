# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.db import models
from lck.django.choices import Choices
from lck.django.common.models import TimeTrackable

from ralph.discovery.models_device import (
    DeviceEnvironment,
    ServiceCatalog,
)
from ralph_assets.history.models import HistoryMixin
from ralph_assets.models_assets import Asset, AssetType, Warehouse


class PartModelType(Choices):

    _ = Choices.Choice

    COMPONENTS = Choices.Group(0)
    disk = _('disk')
    fc_card = _('FC card')
    eth_card = _('Eth card')
    controller = _('controller')

    OTHER = Choices.Group(100)
    other = _('other')


class PartModel(models.Model):

    model_type = models.PositiveSmallIntegerField(choices=PartModelType())
    name = models.CharField(
        max_length=150, unique=True,
    )

    def __unicode__(self):
        return '{} ({})'.format(
            self.name,
            PartModelType.from_id(self.model_type),
        )


class Part(HistoryMixin, TimeTrackable):

    asset = models.ForeignKey(
        Asset,
        null=True,
        blank=True,
        related_name='parts',
        on_delete=models.CASCADE,
    )
    asset_type = models.PositiveSmallIntegerField(choices=AssetType())
    model = models.ForeignKey(
        PartModel,
        on_delete=models.PROTECT,
    )
    sn = models.CharField(max_length=200, unique=True)
    order_no = models.CharField(max_length=100)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
    )
    service = models.ForeignKey(
        ServiceCatalog,
        default=None,
        null=True,
        on_delete=models.PROTECT,
    )
    part_environment = models.ForeignKey(
        DeviceEnvironment,
        default=None,
        null=True,
        on_delete=models.PROTECT,
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)

    def __unicode__(self):
        return '{} ({})'.format(self.sn, self.model)
