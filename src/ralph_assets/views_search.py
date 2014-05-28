# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re

from django.db.models import Q

from ralph_assets.models import Asset


QUOTATION_MARKS = re.compile(r"^\".+\"$")
SEARCH_DELIMITERS = re.compile(r";|\|")


class AssetsSearchQueryableMixin(object):

    def handle_search_data(self, *args, **kwargs):
        search_fields = [
            'id',
            'niw',
            'category',
            'invoice_no',
            'model',
            'order_no',
            'part_info',
            'provider',
            'sn',
            'status',
            'deleted',
            'manufacturer',
            'barcode',
            'device_info',
            'source',
            'deprecation_rate',
            'unlinked',
            'ralph_device_id',
            'task_url',
            'imei',
            'guardian',
            'owner',
            'location',
            'company',
            'employee_id',
            'cost_center',
            'profit_center',
            'department',
            'user',
            'purpose',
            'service_name',
            'warehouse',
            'remarks',
        ]
        # handle simple 'equals' search fields at once.
        all_q = Q()
        for field in search_fields:
            field_value = self.request.GET.get(field)
            if field_value:
                exact = False
                multi = False
                # if search term is enclosed in "", we want exact matches
                if isinstance(field_value, basestring) and \
                        QUOTATION_MARKS.search(field_value):
                    exact = True
                    field_value = field_value[1:-1]
                elif re.search(SEARCH_DELIMITERS, field_value):
                    multi = True
                if field == 'part_info':
                    if field_value == 'device':
                        all_q &= Q(part_info__isnull=True)
                    elif field_value == 'part':
                        all_q &= Q(part_info__gte=0)
                elif field == 'model':
                    if exact:
                        all_q &= Q(model__name=field_value)
                    else:
                        all_q &= Q(model__name__icontains=field_value)
                elif field == 'category':
                    part = self.get_search_category_part(field_value)
                    if part:
                        all_q &= part
                elif field == 'deleted':
                    if field_value.lower() == 'on':
                        all_q &= Q(deleted__in=(True, False))
                elif field == 'manufacturer':
                    if exact:
                        all_q &= Q(model__manufacturer__name=field_value)
                    else:
                        all_q &= Q(
                            model__manufacturer__name__icontains=field_value
                        )
                elif field == 'barcode':
                    if exact:
                        all_q &= Q(barcode=field_value)
                    elif multi:
                        all_q &= self._search_fields_or(
                            ['barcode'],
                            re.split(SEARCH_DELIMITERS, field_value),
                        )
                    else:
                        all_q &= Q(barcode__contains=field_value)
                elif field == 'sn':
                    if exact:
                        all_q &= Q(sn=field_value)
                    elif multi:
                        all_q &= self._search_fields_or(
                            ['sn'],
                            re.split(SEARCH_DELIMITERS, field_value),
                        )
                    else:
                        all_q &= Q(sn__icontains=field_value)
                elif field == 'niw':
                    if exact:
                        all_q &= Q(niw=field_value)
                    elif multi:
                        all_q &= self._search_fields_or(
                            ['niw'],
                            re.split(SEARCH_DELIMITERS, field_value),
                        )
                    else:
                        all_q &= Q(niw__icontains=field_value)
                elif field == 'provider':
                    if exact:
                        all_q &= Q(provider=field_value)
                    else:
                        all_q &= Q(provider__icontains=field_value)
                elif field == 'order_no':
                    if exact:
                        all_q &= Q(order_no=field_value)
                    else:
                        all_q &= Q(order_no__icontains=field_value)
                elif field == 'invoice_no':
                    if exact:
                        all_q &= Q(invoice_no=field_value)
                    else:
                        all_q &= Q(invoice_no__icontains=field_value)
                elif field == 'warehouse':
                    all_q &= Q(warehouse__id=field_value)
                elif field == 'owner':
                    all_q &= Q(owner__id=field_value)
                elif field == 'location':
                    all_q &= Q(location__icontains=field_value)
                elif field == 'employee_id':
                    all_q &= Q(owner__profile__employee_id=field_value)
                elif field == 'company':
                    all_q &= Q(owner__profile__company__icontains=field_value)
                elif field == 'profit_center':
                    all_q &= Q(owner__profile__profit_center=field_value)
                elif field == 'cost_center':
                    all_q &= Q(owner__profile__cost_center=field_value)
                elif field == 'department':
                    all_q &= Q(
                        owner__profile__department__icontains=field_value
                    )
                elif field == 'remarks':
                    all_q &= Q(remarks__icontains=field_value)
                elif field == 'user':
                    all_q &= Q(user__id=field_value)
                elif field == 'guardian':
                    all_q &= Q(guardian__id=field_value)
                elif field == 'deprecation_rate':
                    deprecation_rate_query_map = {
                        'null': Q(deprecation_rate__isnull=True),
                        'deprecated': Q(deprecation_rate=0),
                        '6': Q(deprecation_rate__gt=0,
                               deprecation_rate__lte=6),
                        '12': Q(deprecation_rate__gt=6,
                                deprecation_rate__lte=12),
                        '24': Q(deprecation_rate__gt=12,
                                deprecation_rate__lte=24),
                        '48': Q(deprecation_rate__gt=24,
                                deprecation_rate__lte=48),
                        '48<': Q(deprecation_rate__gt=48),
                    }
                    all_q &= deprecation_rate_query_map[field_value]
                elif field == 'unlinked' and field_value.lower() == 'on':
                        all_q &= ~Q(device_info=None)
                        all_q &= Q(device_info__ralph_device_id=None)
                elif field == 'ralph_device_id':
                    if exact:
                        all_q &= Q(device_info__ralph_device_id=field_value)
                    else:
                        all_q &= Q(
                            device_info__ralph_device_id__icontains=field_value
                        )
                elif field == 'task_url':
                    if exact:
                        all_q &= Q(task_url=field_value)
                    else:
                        all_q &= Q(task_url__icontains=field_value)
                elif field == 'id':
                        all_q &= Q(
                            id__in=[int(id) for id in field_value.split(",")],
                        )
                elif field == 'imei':
                    if exact:
                        all_q &= Q(office_info__imei=field_value)
                    else:
                        all_q &= Q(office_info__imei__icontains=field_value)
                elif field == 'service_name':
                    all_q &= Q(service_name=field_value)
                elif field == 'purpose':
                    all_q &= Q(office_info__purpose=field_value)
                else:
                    q = Q(**{field: field_value})
                    all_q = all_q & q

        # now fields within ranges.
        search_date_fields = [
            'invoice_date', 'request_date', 'delivery_date',
            'production_use_date', 'provider_order_date', 'loan_end_date',
        ]
        for date in search_date_fields:
            start = self.request.GET.get(date + '_from')
            end = self.request.GET.get(date + '_to')
            if start:
                all_q &= Q(**{date + '__gte': start})
            if end:
                all_q &= Q(**{date + '__lte': end})
        self.items_count = Asset.objects.filter(all_q).count()
        return all_q
