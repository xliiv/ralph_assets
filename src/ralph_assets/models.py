#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import difflib

from ajax_select import LookupChannel
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils.html import escape
from django.db.models import Q

from ralph_assets.models_assets import (
    Asset,
    AssetCategory,
    AssetCategoryType,
    AssetManufacturer,
    AssetModel,
    AssetOwner,
    AssetSource,
    AssetStatus,
    AssetType,
    CoaOemOs,
    DeviceInfo,
    OfficeInfo,
    PartInfo,
    ReportOdtSource,
    Service,
    Warehouse,
)
from ralph_assets.models_sam import (  # noqa
    Licence,
    LicenceType,
    SoftwareCategory,
)
from ralph_assets.models_history import AssetHistoryChange
from ralph_assets.models_transition import (
    Action,
    Transition,
    TransitionsHistory,
)
from ralph_assets.models_util import WithForm
from ralph.discovery.models import Device, DeviceType


class DeviceLookup(LookupChannel):
    model = Asset

    def get_query(self, q, request):
        query = Q(
            Q(device_info__gt=0) & Q(
                Q(barcode__istartswith=q) |
                Q(sn__istartswith=q) |
                Q(model__name__icontains=q)
            )
        )
        return self.get_base_objects().filter(query).order_by('sn')[:10]

    def get_result(self, obj):
        return obj.id

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        return """
        <li class='asset-container'>
            <span class='asset-model'>%s</span>
            <span class='asset-barcode'>%s</span>
            <span class='asset-sn'>%s</span>
        </li>
        """ % (escape(obj.model), escape(obj.barcode or ''), escape(obj.sn))

    def get_base_objects(self):
        return self.model.objects


class FreeLicenceLookup(LookupChannel):
    """Lookup the licences that have any specimen left."""

    model = Licence

    def get_query(self, q, _):
        return self.model.objects.raw(
            """SELECT
                ralph_assets_licence.*,
                ralph_assets_softwarecategory.name,
                (
                    COUNT(ralph_assets_licence_assets.asset_id)  +
                    COUNT(ralph_assets_licence_users.user_id)
                ) AS used
            FROM
                ralph_assets_licence
            INNER JOIN ralph_assets_softwarecategory ON (
                ralph_assets_licence.software_category_id =
                ralph_assets_softwarecategory.id
            )
            LEFT JOIN ralph_assets_licence_assets ON (
                ralph_assets_licence.id =
                ralph_assets_licence_assets.licence_id
            )
            LEFT JOIN ralph_assets_licence_users ON (
                ralph_assets_licence.id =
                ralph_assets_licence_users.licence_id
            )
            WHERE ralph_assets_softwarecategory.name LIKE %s
            GROUP BY ralph_assets_licence.id
            HAVING used < ralph_assets_licence.number_bought
            LIMIT 10;
            """,
            ('%{}%'.format(q),)
        )

    def get_result(self, obj):
        return obj.id

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        return """
        <li class='asset-container'>
            <span>{}</span>
            <span>({} free)</span>
        </li>
        """.format(
            escape(str(obj)),
            str(obj.number_bought - obj.assets.count() - obj.users.count())
        )


class RalphDeviceLookup(LookupChannel):
    model = Device

    def get_query(self, q, request):
        query = Q(
            Q(
                Q(barcode__istartswith=q) |
                Q(id__istartswith=q) |
                Q(sn__istartswith=q) |
                Q(model__name__icontains=q)
            )
        )
        return Device.objects.filter(query).order_by('sn')[:10]

    def get_result(self, obj):
        return obj.id

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        return """
        <li class='asset-container'>
            <span class='asset-model'>%s</span>
            <span class='asset-barcode'>%s</span>
            <span class='asset-sn'>%s</span>
        </li>
        """ % (escape(obj.model), escape(obj.barcode or ''), escape(obj.sn))


class AssetLookup(LookupChannel):
    model = Asset

    def get_query(self, q, request):
        return Asset.objects.filter(
            Q(barcode__icontains=q) |
            Q(sn__icontains=q)
        ).order_by('sn', 'barcode')[:10]

    def get_result(self, obj):
        return obj.id

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        return '{}'.format(escape(unicode(obj)))


class AssetModelLookup(LookupChannel):
    model = AssetModel

    def get_query(self, q, request):
        return self.model.objects.filter(
            Q(name__icontains=q) & Q(type=getattr(self, 'type', None))
        ).order_by('name')[:10]

    def get_result(self, obj):
        return obj.name

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        manufacturer = getattr(obj, 'manufacturer', None) or '-'
        return '''
        <li>
            <span>{model}</span>
            <span class='auto-complete-blue'>({manufacturer})</span>
        </li>
        '''.format(model=escape(obj.name), manufacturer=escape(manufacturer))


class DCAssetModelLookup(AssetModelLookup):
    type = AssetType.data_center


class BOAssetModelLookup(AssetModelLookup):
    type = AssetType.back_office


class AssetManufacturerLookup(LookupChannel):
    model = AssetModel

    def get_query(self, q, request):
        return AssetModel.objects.filter(
            Q(manufacturer__name__icontains=q)
        ).order_by('manufacturer__name')[:10]

    def get_result(self, obj):
        return obj.manufacturer.name

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        return '{}'.format(escape(obj.manufacturer.name))


class WarehouseLookup(LookupChannel):
    model = Warehouse

    def get_query(self, q, request):
        return Warehouse.objects.filter(
            Q(name__icontains=q)
        ).order_by('name')[:10]

    def get_result(self, obj):
        return obj.id

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        return escape(obj.name)


class DCDeviceLookup(DeviceLookup):
    def get_base_objects(self):
        return Asset.objects_dc


class BODeviceLookup(DeviceLookup):
    def get_base_objects(self):
        return Asset.objects_bo


class AssetLookupFuzzy(AssetLookup):
    def get_query(self, query, request):
        dev_ids = Device.objects.filter(
            model__type=DeviceType.unknown,
        ).values_list('id', flat=True)
        assets = Asset.objects.select_related(
            'model__name',
        ).filter(
            Q(device_info__ralph_device_id=None) |
            Q(device_info__ralph_device_id__in=dev_ids),
        ).filter(part_info=None)

        def comparator(asset):
            seq = "".join(
                [part or '' for part in
                    [
                        asset.sn,
                        asset.barcode,
                        asset.model.name,
                    ]]
            ).replace(" ", "").lower()
            ratio = difflib.SequenceMatcher(
                None,
                seq,
                query.replace(" ", "").lower(),
            ).ratio()
            if ratio:
                return 1 / ratio
            return 999

        assets = sorted(assets, key=comparator)
        return assets[:10]

    def format_match(self, obj):
        ret = obj.__unicode__()
        ret += " - {}".format(obj.invoice_no)
        return ret


class UserLookup(LookupChannel):
    model = User

    def get_query(self, q, request):
        try:
            q1, q2 = q.split()
        except ValueError:
            result = User.objects.filter(
                Q(username__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q)
            ).order_by('username')[:10]
        else:
            result = User.objects.filter(
                Q(first_name__icontains=q1, last_name__icontains=q2) |
                Q(first_name__icontains=q2, last_name__icontains=q1)
            )[:10]
        return result

    def get_result(self, obj):
        return obj.id

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        return """
        <li class='asset-container'>
            <span class=''>{first_name} {last_name}</span>
            <span class='asset-user-department'>{department}</span>
        </li>
         """.format(
            first_name=obj.first_name,
            last_name=obj.last_name,
            department=obj.profile.department,
        )


def get_edit_url(object_):
    if isinstance(object_, User):
        return reverse(
            'edit_user_relations', kwargs={'username': object_.username},
        )
    elif isinstance(object_, WithForm):
        return object_.url


__all__ = [
    'Action',
    'Asset',
    'AssetCategory',
    'AssetCategoryType',
    'AssetManufacturer',
    'AssetModel',
    'AssetOwner',
    'AssetSource',
    'AssetStatus',
    'AssetType',
    'CoaOemOs',
    'DeviceInfo',
    'OfficeInfo',
    'PartInfo',
    'ReportOdtSource',
    'Service',
    'Transition',
    'TransitionsHistory',
    'Warehouse',
    'DeviceLookup',
    'DCDeviceLookup',
    'BODeviceLookup',
    'DCAssetModelLookup',
    'BOAssetModelLookup',
    'AssetHistoryChange',
]
