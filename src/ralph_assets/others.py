# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from ralph_assets.models import Asset, Licence
from ralph_assets.models_assets import MODE2ASSET_TYPE


ASSETS_COLUMNS = [
    'id',
    'niw',
    'barcode',
    'sn',
    'model__category__name',
    'model__manufacturer__name',
    'model__name',
    'user__username',
    'user__first_name',
    'user__last_name',
    'owner__username',
    'owner__first_name',
    'owner__last_name',
    'status',
    'service_name',
    'property_of',
]
LICENCES_COLUMNS = [
    'niw',
    'software_category',
    'number_bought',
    'price',
    'invoice_date',
    'invoice_no',
]
LICENCES_ASSETS_COLUMNS = [
    'id',
    'barcode',
    'niw',
    'user__username',
    'user__first_name',
    'user__last_name',
    'owner__username',
    'owner__first_name',
    'owner__last_name',
]
LICENCES_USERS_COLUMNS = [
    'username',
    'first_name',
    'last_name',
]


def get_licences_rows(filter_type='all'):
    if filter_type == 'all':
        queryset = Licence.objects.all()
    else:
        queryset = Licence.objects.filter(
            asset_type=MODE2ASSET_TYPE[filter_type]
        )
    yield "{}, {}, {},single_cost, \n".format(
        ", ".join(LICENCES_COLUMNS),
        ", ".join(LICENCES_ASSETS_COLUMNS),
        ", ".join(LICENCES_USERS_COLUMNS),
    )
    fill_empty_assets = ", " * len(LICENCES_ASSETS_COLUMNS)
    fill_empty_licences = ", " * len(LICENCES_USERS_COLUMNS)
    for licence in queryset:
        row = ""
        for column in LICENCES_COLUMNS:
            row += "{}, ".format(getattr(licence, column))
        base_row = row
        row = "{}{}{}\n".format(row, fill_empty_assets, fill_empty_licences)
        yield row
        if licence.number_bought > 0 and licence.price:
            single_licence_cost = licence.price / licence.number_bought
        else:
            single_licence_cost = ''
        for asset in licence.assets.all().values(*LICENCES_ASSETS_COLUMNS):
            row = ""
            for column in LICENCES_ASSETS_COLUMNS:
                row += "{}, ".format(asset.get(column))
            yield "{}{}{}{}, \n".format(
                base_row, row, fill_empty_licences, single_licence_cost,
            )
        for user in licence.users.all().values(*LICENCES_USERS_COLUMNS):
            row = ""
            for column in LICENCES_USERS_COLUMNS:
                row += "{}, ".format(user.get(column))
            yield "{}{}{}{}, \n".format(
                base_row, fill_empty_assets, row, single_licence_cost,
            )


def get_assets_rows(filter_type='all'):
    if filter_type == 'all':
        queryset = Asset.objects.all().values(*ASSETS_COLUMNS)
    else:
        queryset = Asset.objects.filter(
            type=MODE2ASSET_TYPE[filter_type]
        ).values(*ASSETS_COLUMNS)
    yield "{},\n".format(", ".join(ASSETS_COLUMNS))
    for asset in queryset:
        row = ""
        for column in ASSETS_COLUMNS:
            row += "{}, ".format(asset.get(column))
        row = "{}\n".format(row)
        yield row
