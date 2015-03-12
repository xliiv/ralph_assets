# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import re

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from lck.django.choices import Choices
from lck.django.common.models import (
    Named,
    SoftDeletable,
    TimeTrackable,
)

from django.db import models
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete
from django.db.utils import DatabaseError
from django.dispatch import receiver

from ralph.discovery.models_device import (
    Device,
    DeviceType,
)
from ralph.discovery.models_util import SavingUser
from ralph_assets.history.models import HistoryMixin


logger = logging.getLogger(__name__)

# i.e. number in range 1-16 and optional postfix 'A' or 'B'
VALID_SLOT_NUMBER_FORMAT = re.compile('^([1-9][A,B]?|1[0-6][A,B]?)$')


class Orientation(Choices):
    _ = Choices.Choice

    DEPTH = Choices.Group(0)
    front = _("front")
    back = _("back")
    middle = _("middle")

    WIDTH = Choices.Group(100)
    left = _("left")
    right = _("right")

    @classmethod
    def is_width(cls, orientation):
        is_width = orientation in set(
            [choice.id for choice in cls.WIDTH.choices]
        )
        return is_width

    @classmethod
    def is_depth(cls, orientation):
        is_depth = orientation in set(
            [choice.id for choice in cls.DEPTH.choices]
        )
        return is_depth


class RackOrientation(Choices):
    _ = Choices.Choice

    top = _("top")
    bottom = _("bottom")
    left = _("left")
    right = _("right")


class RequiredModelWithTypeMixin(object):
    """
    Mixin forces a model type in deprecated object (rack, dc).
    """
    _model_type = None

    def __init__(self, *args, **kwargs):
        if not self._model_type:
            raise ValueError('Please provide _model_type')
        super(RequiredModelWithTypeMixin, self).__init__(*args, **kwargs)

    @classmethod
    def create(cls, **kwargs):
        if 'model' not in kwargs.iterkeys():
            raise ValueError('Please provide model.')
        elif kwargs['model'].type != cls._model_type:
            raise ValueError(
                'Model must be a {} type.'.format(cls._model_type.desc)
            )
        return cls(**kwargs)


class DeprecatedRalphDCManager(models.Manager):
    def get_query_set(self):
        query_set = super(DeprecatedRalphDCManager, self).get_query_set()
        data_centers = query_set.filter(model__type=DeviceType.data_center)
        return data_centers


class DeprecatedRalphDC(RequiredModelWithTypeMixin, Device):
    _model_type = DeviceType.data_center
    objects = DeprecatedRalphDCManager()

    class Meta:
        proxy = True


class DeprecatedRalphRackManager(models.Manager):
    def get_query_set(self):
        query_set = super(DeprecatedRalphRackManager, self).get_query_set()
        racks = query_set.filter(model__type=DeviceType.rack)
        return racks


class DeprecatedRalphRack(RequiredModelWithTypeMixin, Device):
    _model_type = DeviceType.rack
    objects = DeprecatedRalphRackManager()

    class Meta:
        proxy = True


class DataCenter(Named):
    deprecated_ralph_dc = models.ForeignKey(
        DeprecatedRalphDC, null=True, blank=True, unique=True
    )
    visualization_cols_num = models.PositiveIntegerField(
        verbose_name=_('visualization grid columns number'),
        default=20,
    )
    visualization_rows_num = models.PositiveIntegerField(
        verbose_name=_('visualization grid rows number'),
        default=20,
    )

    def __unicode__(self):
        return self.name


class ServerRoom(Named.NonUnique):
    data_center = models.ForeignKey(DataCenter, verbose_name=_("data center"))

    def __unicode__(self):
        return '{} ({})'.format(self.name, self.data_center.name)


class Accessory(Named):

    class Meta:
        verbose_name = _('accessory')
        verbose_name_plural = _('accessories')


class RackManager(models.Manager):
    def with_free_u(self):
        racks = self.get_query_set()
        for rack in racks:
            rack.free_u = rack.get_free_u()
        return racks


class Rack(Named.NonUnique):
    class Meta:
        unique_together = ('name', 'data_center')

    data_center = models.ForeignKey(DataCenter, null=False, blank=False)
    server_room = models.ForeignKey(
        ServerRoom, verbose_name=_("server room"),
        null=True,
        blank=True,
    )
    description = models.CharField(
        _('description'), max_length=250, blank=True
    )
    orientation = models.PositiveIntegerField(
        choices=RackOrientation(),
        default=RackOrientation.top.id,
    )
    max_u_height = models.IntegerField(default=48)
    deprecated_ralph_rack = models.ForeignKey(
        DeprecatedRalphRack, null=True, related_name='deprecated_asset_rack',
        blank=True,
    )
    visualization_col = models.PositiveIntegerField(
        verbose_name=_('column number on visualization grid'),
        default=0,
    )
    visualization_row = models.PositiveIntegerField(
        verbose_name=_('row number on visualization grid'),
        default=0,
    )
    accessories = models.ManyToManyField(Accessory, through='RackAccessory')
    objects = RackManager()

    def get_free_u(self):
        assets = self.get_root_assets()
        assets_height = assets.aggregate(
            sum=Sum('model__height_of_device'))['sum'] or 0
        # accesory always has 1U of height
        accessories = RackAccessory.objects.values_list(
            'position', flat=True).filter(rack=self)
        return self.max_u_height - assets_height - len(set(accessories))

    def get_orientation_desc(self):
        return RackOrientation.name_from_id(self.orientation)

    def get_pdus(self):
        from ralph_assets.models_assets import Asset
        return Asset.objects.select_related('model', 'device_info').filter(
            device_info__rack=self,
            device_info__orientation__in=(Orientation.left, Orientation.right),
            device_info__position=0,
        )

    def get_root_assets(self, side=None):
        from ralph_assets.models_assets import Asset
        filter_kwargs = {
            'device_info__rack': self,
            'device_info__slot_no': '',
        }
        if side:
            filter_kwargs['device_info__orientation'] = side
        return Asset.objects.select_related(
            'model', 'device_info', 'model__category'
        ).filter(**filter_kwargs).exclude(model__category__is_blade=True)

    def __unicode__(self):
        name = self.name
        if self.server_room:
            name = '{} - {}'.format(name, self.server_room)
        elif self.data_center:
            name = '{} - {}'.format(name, self.data_center)
        return name


class RackAccessory(models.Model):
    accessory = models.ForeignKey(Accessory)
    rack = models.ForeignKey(Rack)
    data_center = models.ForeignKey(DataCenter, null=True, blank=False)
    server_room = models.ForeignKey(ServerRoom, null=True, blank=False)
    orientation = models.PositiveIntegerField(
        choices=Orientation(),
        default=Orientation.front.id,
    )
    position = models.IntegerField(null=True, blank=False)
    remarks = models.CharField(
        verbose_name='Additional remarks',
        max_length=1024,
        blank=True,
    )

    def get_orientation_desc(self):
        return Orientation.name_from_id(self.orientation)

    def __unicode__(self):
        rack_name = self.rack.name if self.rack else ''
        accessory_name = self.accessory.name if self.accessory else ''
        return 'RackAccessory: {rack_name} - {accessory_name}'.format(
            rack_name=rack_name, accessory_name=accessory_name,
        )


class DeviceInfo(HistoryMixin, TimeTrackable, SavingUser, SoftDeletable):
    ralph_device_id = models.IntegerField(
        verbose_name=_("Ralph device id"),
        null=True,
        blank=True,
        unique=True,
        default=None,
    )
    u_level = models.CharField(max_length=10, null=True, blank=True)
    u_height = models.CharField(max_length=10, null=True, blank=True)
    data_center = models.ForeignKey(DataCenter, null=True, blank=False)
    server_room = models.ForeignKey(ServerRoom, null=True, blank=False)
    rack = models.ForeignKey(Rack, null=True, blank=True)
    # deperecated field, use rack instead
    rack_old = models.CharField(max_length=10, null=True, blank=True)
    slot_no = models.CharField(
        verbose_name=_("slot number"), max_length=3, null=True, blank=True,
    )
    position = models.IntegerField(null=True)
    orientation = models.PositiveIntegerField(
        choices=Orientation(),
        default=Orientation.front.id,
    )

    def clean_fields(self, exclude=None):
        """
        Constraints:
        - picked rack is from picked server-room
        - picked server-room is from picked data-center
        - postion = 0: orientation(left, right)
        - postion > 0: orientation(front, middle, back)
        - position <= rack.max_u_height
        - slot_no: asset is_blade=True
        """
        if self.rack and self.server_room:
            if self.rack.server_room != self.server_room:
                msg = 'This rack is not from picked server room'
                raise ValidationError({'rack': [msg]})
        if self.server_room and self.data_center:
            if self.server_room.data_center != self.data_center:
                msg = 'This server room is not from picked data center'
                raise ValidationError({'server_room': [msg]})
        if self.position == 0 and not Orientation.is_width(self.orientation):
            msg = 'Valid orientations for picked position are: {}'.format(
                ', '.join(
                    choice.desc for choice in Orientation.WIDTH.choices
                )
            )
            raise ValidationError({'orientation': [msg]})
        if self.position > 0 and not Orientation.is_depth(self.orientation):
            msg = 'Valid orientations for picked position are: {}'.format(
                ', '.join(
                    choice.desc for choice in Orientation.DEPTH.choices
                )
            )
            raise ValidationError({'orientation': [msg]})
        if self.rack and self.position > self.rack.max_u_height:
            msg = 'Position is higher than "max u height" = {}'.format(
                self.rack.max_u_height,
            )
            raise ValidationError({'position': [msg]})
        if self.slot_no and not VALID_SLOT_NUMBER_FORMAT.search(self.slot_no):
            msg = ("Slot number should be a number from range 1-16 with "
                   "an optional postfix 'A' or 'B' (e.g. '16A')")
            raise ValidationError({'slot_no': [msg]})

    @property
    def size(self):
        """Deprecated. Kept for backwards compatibility."""
        return 0

    def __unicode__(self):
        return "{} - {}".format(
            self.ralph_device_id,
            self.size,
        )

    def get_ralph_device(self):
        if not self.ralph_device_id:
            return None
        try:
            dev = Device.objects.get(id=self.ralph_device_id)
            return dev
        except Device.DoesNotExist:
            return None

    def get_orientation_desc(self):
        return Orientation.name_from_id(self.orientation)

    def __init__(self, *args, **kwargs):
        self.save_comment = None
        self.saving_user = None
        super(DeviceInfo, self).__init__(*args, **kwargs)


@receiver(
    post_delete,
    sender=Device,
    dispatch_uid='discovery.device.post_delete',
)
def device_post_delete(sender, instance, **kwargs):
    for deviceinfo in DeviceInfo.objects.filter(ralph_device_id=instance.id):
        deviceinfo.ralph_device_id = None
        deviceinfo.save()


@receiver(post_save, sender=Device, dispatch_uid='ralph_assets.device_delete')
def device_post_save(sender, instance, **kwargs):
    """
    A hook for cleaning ``ralph_device_id`` in ``DeviceInfo`` when device
    linked to it gets soft-deleted (hence post-save signal instead of
    pre-delete or post-delete).
    """
    if instance.deleted:
        try:
            di = DeviceInfo.objects.get(ralph_device_id=instance.id)
            di.ralph_device_id = None
            di.save()
        except (DeviceInfo.DoesNotExist, DatabaseError):
            pass
