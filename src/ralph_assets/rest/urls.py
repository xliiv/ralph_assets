# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from ralph_assets.rest import (
    AssetInfoPerRackAPIView,
)


urlpatterns = patterns(
    '',
    url(
        r'^rack/(?P<rack_id>\d+)/devices/$',
        AssetInfoPerRackAPIView.as_view(),
    ),
)
