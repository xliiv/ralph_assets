# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rest_framework.generics import ListAPIView

from ralph.ui.views.common import ACLGateway
from ralph_assets.models_parts import Part
from ralph_assets.rest.serializers.models_parts import PartSerializer


class PartsView(ACLGateway, ListAPIView):
    serializer_class = PartSerializer

    def get_queryset(self):
        sns = self.request.QUERY_PARAMS.get('sns', None)
        filters = {}
        if sns:
            filters['sn__in'] = sns.split(',')
        return Part.objects.filter(**filters)
