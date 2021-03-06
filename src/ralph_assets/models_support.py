# -*- coding: utf-8 -*-
"""Support module models."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime

from django.contrib.humanize.templatetags.humanize import naturaltime
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _
from lck.django.choices import Choices
from lck.django.common.models import (
    EditorTrackable,
    Named,
    SoftDeletable,
    TimeTrackable,
    WithConcurrentGetOrCreate,
)
from ralph.discovery.models_util import SavingUser

from ralph_assets import models_assets
from ralph_assets.history.models import HistoryMixin
from ralph_assets.models_assets import (
    AssetType,
    Asset,
    AssetOwner,
)
from ralph_assets.models_util import (
    Regionalized,
    RegionalizedDBManager,
)


class SupportType(Named):
    """The type of a support"""


class SupportStatus(Choices):
    _ = Choices.Choice

    SUPPORT = Choices.Group(0)
    new = _("new")


class SupportManger(RegionalizedDBManager):
    pass


class Support(
    Regionalized,
    HistoryMixin,
    EditorTrackable,
    Named.NonUnique,
    models_assets.AttachmentMixin,
    SoftDeletable,
    SavingUser,
    TimeTrackable,
    WithConcurrentGetOrCreate,
):
    objects = SupportManger()
    contract_id = models.CharField(max_length=50, blank=False)
    description = models.CharField(max_length=100, blank=True)
    attachments = models.ManyToManyField(
        models_assets.Attachment, null=True, blank=True
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, null=True, blank=True,
    )
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=False, blank=False)
    escalation_path = models.CharField(max_length=200, blank=True)
    contract_terms = models.CharField(max_length=200, blank=True)
    additional_notes = models.CharField(max_length=200, blank=True)
    sla_type = models.CharField(max_length=200, blank=True)
    asset_type = models.PositiveSmallIntegerField(
        choices=AssetType()
    )
    status = models.PositiveSmallIntegerField(
        default=SupportStatus.new.id,
        verbose_name=_("status"),
        choices=SupportStatus(),
        null=False,
        blank=False,
    )
    producer = models.CharField(max_length=100, blank=True)
    supplier = models.CharField(max_length=100, blank=True)
    serial_no = models.CharField(max_length=100, blank=True)
    invoice_no = models.CharField(max_length=100, blank=True, db_index=True)
    invoice_date = models.DateField(
        null=True, blank=True, verbose_name=_('Invoice date'),
    )
    period_in_months = models.IntegerField(null=True, blank=True)
    property_of = models.ForeignKey(
        AssetOwner,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    support_type = models.ForeignKey(
        SupportType,
        on_delete=models.PROTECT,
        blank=True,
        default=None,
        null=True,
    )
    assets = models.ManyToManyField(Asset, related_name='supports')

    def __init__(self, *args, **kwargs):
        self.saving_user = None
        super(Support, self).__init__(*args, **kwargs)

    @property
    def url(self):
        return reverse('edit_support', kwargs={
            'support_id': self.id,
        })

    def get_natural_end_support(self):
        return naturaltime(datetime(*(self.date_to.timetuple()[:6])))
