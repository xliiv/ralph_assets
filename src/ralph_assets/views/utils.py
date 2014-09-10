# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.db import transaction

from ralph_assets.models import Asset, DeviceInfo, OfficeInfo, PartInfo


def _move_data(src, dst, fields):
    for field in fields:
        if field in src:
            value = src.pop(field)
            dst[field] = value
    return src, dst


@transaction.commit_on_success
def _create_device(creator_profile, asset_data, cleaned_additional_info, mode):
    if mode == 'dc':
        asset = Asset(created_by=creator_profile, **asset_data)
        device_info = DeviceInfo()
        for field in ['ralph_device_id', 'u_level', 'u_height']:
            setattr(device_info, field, cleaned_additional_info[field])
        device_info.save(user=creator_profile.user)
        asset.device_info = device_info
    elif mode == 'back_office':
        _move_data(asset_data, cleaned_additional_info, ['purpose'])
        asset = Asset(created_by=creator_profile, **asset_data)
        office_info = OfficeInfo()
        office_info.__dict__.update(**cleaned_additional_info)
        office_info.coa_oem_os = cleaned_additional_info['coa_oem_os']
        office_info.save(user=creator_profile.user)
        asset.office_info = office_info
    asset.save(user=creator_profile.user)
    return asset


@transaction.commit_on_success
def _create_part(creator_profile, asset_data, part_info_data, sn):
    part_info = PartInfo(**part_info_data)
    part_info.save(user=creator_profile.user)
    asset = Asset(
        part_info=part_info,
        sn=sn.strip(),
        created_by=creator_profile,
        **asset_data
    )
    asset.save(user=creator_profile.user)
    return asset.id


@transaction.commit_on_success
def _update_office_info(user, asset, office_info_data):
    if not asset.office_info:
        office_info = OfficeInfo()
    else:
        office_info = asset.office_info
    if 'attachment' in office_info_data:
        if office_info_data['attachment'] is None:
            del office_info_data['attachment']
        elif office_info_data['attachment'] is False:
            office_info_data['attachment'] = None
    office_info.__dict__.update(**office_info_data)
    office_info.save(user=user)
    asset.office_info = office_info
    asset.save(user=user)
    return asset


@transaction.commit_on_success
def _update_device_info(user, asset, device_info_data):
    if not asset.device_info:
        asset.device_info = DeviceInfo()
    asset.device_info.__dict__.update(
        **device_info_data
    )
    asset.device_info.save(user=user)
    return asset


@transaction.commit_on_success
def _update_asset(modifier_profile, asset, asset_updated_data):
    if (
        'barcode' not in asset_updated_data or
        not asset_updated_data['barcode']
    ):
        asset_updated_data['barcode'] = None
    asset_updated_data.update({'modified_by': modifier_profile})
    asset.__dict__.update(**asset_updated_data)
    return asset


@transaction.commit_on_success
def _update_part_info(user, asset, part_info_data):
    if not asset.part_info:
        part_info = PartInfo()
    else:
        part_info = asset.part_info
    part_info.device = part_info_data.get('device')
    part_info.source_device = part_info_data.get('source_device')
    part_info.barcode_salvaged = part_info_data.get('barcode_salvaged')
    part_info.save(user=user)
    asset.part_info = part_info
    asset.part_info.save(user=user)
    return asset
