#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from lck.django.choices import Choices
from lck.django.common.models import (
    Named,
    SoftDeletable,
    TimeTrackable,
)

from django.db import models
from django.db.models.signals import post_save, post_delete
from django.db.utils import DatabaseError
from django.dispatch import receiver

from ralph.discovery.models_device import (
    Device,
    DeviceType,
)
from ralph.discovery.models_util import SavingUser


logger = logging.getLogger(__name__)

INVALID_DATA_CENTER = 1
INVALID_SERVER_ROOM = 2
INVALID_ORIENTATION = 3
INVALID_POSITION = 4
REQUIRED_SLOT_NUMBER = 5


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


class DeprecatedRalphDCManager(models.Manager):
    def get_query_set(self):
        query_set = super(DeprecatedRalphDCManager, self).get_query_set()
        data_centers = query_set.filter(model__type=DeviceType.data_center)
        return data_centers


class DeprecatedRalphDC(Device):
    objects = DeprecatedRalphDCManager()

    class Meta:
        proxy = True


class DeprecatedRalphRackManager(models.Manager):
    def get_query_set(self):
        query_set = super(DeprecatedRalphRackManager, self).get_query_set()
        racks = query_set.filter(model__type=DeviceType.rack)
        return racks


class DeprecatedRalphRack(Device):
    objects = DeprecatedRalphRackManager()

    class Meta:
        proxy = True


class DataCenter(Named):
    deprecated_ralph_dc = models.ForeignKey(
        DeprecatedRalphDC, null=True, blank=True,
    )


class ServerRoom(Named.NonUnique):
    data_center = models.ForeignKey(DataCenter, verbose_name=_("data center"))


class Rack(Named.NonUnique):
    class Meta:
        unique_together = ('name', 'data_center')

    data_center = models.ForeignKey(DataCenter, null=False, blank=False)
    server_room = models.ForeignKey(
        ServerRoom, verbose_name=_("server room"),
        null=True,
        blank=True,
    )
    max_u_height = models.IntegerField(default=48)
    deprecated_ralph_rack = models.ForeignKey(
        DeprecatedRalphRack, null=True, related_name='deprecated_asset_rack',
        blank=True,
    )



class AccessoryType(Choices):
    _ = Choices.Choice
    brush = _("brush")
    patch_pabel = _("patch pabel")


class Accessory(Named.NonUnique):
    type = models.PositiveIntegerField(choices=AccessoryType())
    data_center = models.ForeignKey(DataCenter, null=True, blank=False)
    server_room = models.ForeignKey(ServerRoom, null=True, blank=False)
    rack = models.ForeignKey(Rack, null=True, blank=True)
    position = models.IntegerField(null=True)
    remarks = models.CharField(
        verbose_name='Additional remarks',
        max_length=1024,
        blank=True,
    )



class DeviceInfo(TimeTrackable, SavingUser, SoftDeletable):
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
    slot_no = models.IntegerField(
        verbose_name=_("slot number"), null=True, blank=True,
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
                msg = 'Valid server room for this rack is: "{}"'.format(
                    self.rack.server_room.name,
                )
                raise ValidationError(
                    {'server_room': msg}, code=INVALID_SERVER_ROOM,
                )
        if self.server_room and self.data_center:
            if self.server_room.data_center != self.data_center:
                msg = 'Valid data center for this server room is: "{}"'.format(
                    self.server_room.data_center.name,
                )
                raise ValidationError(
                    {'data_center': msg}, code=INVALID_DATA_CENTER,
                )
        if self.position == 0 and not Orientation.is_width(self.orientation):
            msg = 'Valid orientations for picked position are: {}'.format(
                ', '.join(
                    choice.desc for choice in Orientation.WIDTH.choices
                )
            )
            raise ValidationError(
                {'orientation': msg}, code=INVALID_ORIENTATION
            )
        if self.position > 0 and not Orientation.is_depth(self.orientation):
            msg = 'Valid orientations for picked position are: {}'.format(
                ', '.join(
                    choice.desc for choice in Orientation.DEPTH.choices
                )
            )
            raise ValidationError(
                {'orientation': msg}, code=INVALID_ORIENTATION,
            )
        if self.rack and self.position > self.rack.max_u_height:
            msg = 'Position is higher than "max u height" = {}'.format(
                self.rack.max_u_height,
            )
            raise ValidationError({'position': msg}, code=INVALID_POSITION)

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
