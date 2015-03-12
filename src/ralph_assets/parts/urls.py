# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from ralph_assets.parts.views import AssignToAssetView, ChangePartsView

urlpatterns = patterns(
    '',
    url(
        (r'^(?P<asset_id>[\d]+)/$'),
        ChangePartsView.as_view(),
        name='change_parts',
    ),
    url(
        (r'^assign-to-asset/(?P<asset_id>[\d]+)/$'),
        AssignToAssetView.as_view(),
        name='assign_to_asset',
    ),
)
