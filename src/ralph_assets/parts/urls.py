# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from ralph_assets.parts.views import AssignToAssetView, ChangePartsView
from ralph_assets.views.part import (
    AddPart,
    EditPart,
    PartList,
)

urlpatterns = patterns(
    '',
    url(r'^$',
        login_required(PartList.as_view()),
        name='part_search'),
    url(r'^add/part/',
        login_required(AddPart.as_view()),
        name='add_part'),
    url(r'^edit/part/(?P<part_id>[0-9]+)/$',
        login_required(EditPart.as_view()),
        name='part_edit'),
    url(
        (r'^exchange/(?P<asset_id>[\d]+)/$'),
        ChangePartsView.as_view(),
        name='change_parts',),
    url(
        (r'^apply/(?P<asset_id>[\d]+)/$'),
        AssignToAssetView.as_view(),
        name='assign_to_asset',),
)
