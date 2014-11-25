# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from django.db.models.signals import post_save
from django.dispatch import receiver

from ralph_assets.models import Asset, DeviceInfo, Orientation


SAVE_PRIORITY = 215


def _can_not_edit_localization(asset_dev_info):
    return not Asset.objects.filter(device_info=asset_dev_info).exists() or (
        asset_dev_info.asset.model.category and
        asset_dev_info.asset.model.category.is_blade
    )


def _update_localization(device, asset_dev_info):
    if _can_not_edit_localization(asset_dev_info):
        return
    # Rack not defined in asset device_info
    if (
        not asset_dev_info.rack or
        not asset_dev_info.rack.deprecated_ralph_rack
    ):
        return
    # update rack (parent)
    rack = asset_dev_info.rack.deprecated_ralph_rack
    device.parent = rack
    device.save(priority=SAVE_PRIORITY)
    # update dc for rack (rack parent)
    if not asset_dev_info.rack.data_center.deprecated_ralph_dc:
        return
    data_center = asset_dev_info.rack.data_center.deprecated_ralph_dc
    rack.parent = data_center
    rack.save(priority=SAVE_PRIORITY)


def _update_cached_localization(device, asset_dev_info):
    if (
        asset_dev_info.data_center and
        asset_dev_info.data_center.deprecated_ralph_dc
    ):
        device.dc = asset_dev_info.data_center.deprecated_ralph_dc.sn
    if (
        asset_dev_info.rack and
        asset_dev_info.rack.deprecated_ralph_rack
    ):
        device.rack = asset_dev_info.rack.deprecated_ralph_rack.sn
    device.save(priority=SAVE_PRIORITY)


def _update_level_and_orientation(device, asset_dev_info):
    if _can_not_edit_localization(asset_dev_info):
        return
    if asset_dev_info.position:
        device.chassis_position = asset_dev_info.position
    if asset_dev_info.orientation:
        device.position = Orientation.name_from_id(
            asset_dev_info.orientation,
        )
    device.save(priority=SAVE_PRIORITY)


def update_core_localization(asset_dev_info):
    """
    DEPRECATED

    Synchronize Asset localization with Ralph Core localization - for backward
    compatibility. In future, localization will be stored only for Asset.
    """

    device = asset_dev_info.get_ralph_device()
    if not device:
        return
    _update_localization(device=device, asset_dev_info=asset_dev_info)
    _update_cached_localization(device=device, asset_dev_info=asset_dev_info)
    _update_level_and_orientation(device=device, asset_dev_info=asset_dev_info)


@receiver(
    post_save, sender=DeviceInfo, dispatch_uid='assets.deviceinfo.post_save',
)
def asset_device_info_post_save(sender, instance, **kwargs):
    update_core_localization(asset_dev_info=instance)
