# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from ralph_assets.rest.asset_info_per_rack import AssetsView
from ralph_assets.rest.asset import AssetPartsView
from ralph_assets.rest.part import PartsView
from ralph_assets.rest import DCRacksAPIView


urlpatterns = patterns(
    '',
    url(
        r'^rack/(?P<rack_id>\d+)/?$',
        AssetsView.as_view(),
    ),
    url(
        r'^data_center/(?P<data_center_id>\d+)/?$',
        DCRacksAPIView.as_view(),
    ),
    url(
        r'^assets/(?P<asset_id>\d+)/parts/?$',
        AssetPartsView.as_view(),
    ),
    url(
        r'^parts/?$',
        PartsView.as_view(),
        name='api_parts',
    ),
)
