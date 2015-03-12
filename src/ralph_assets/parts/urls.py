# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from ralph_assets.parts.views import ChangePartsView


urlpatterns = patterns(
    '',
    url(
        (r'^(?P<asset_id>[\d]+)/$'),
        ChangePartsView.as_view(),
        name='change_parts',
    ),
)
