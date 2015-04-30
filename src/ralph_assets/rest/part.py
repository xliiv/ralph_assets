# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from ralph.ui.views.common import ACLGateway
from ralph_assets.models_parts import Part
from ralph_assets.rest.serializers.models_parts import PartSerializer


class PartsView(ACLGateway, APIView):
    def get_object(self, sn):
        return get_object_or_404(Part, sn=sn)

    def get(self, request, *args, **kwargs):
        sn = self.request.QUERY_PARAMS.get('sn', '')
        if sn == '':
            return Response(status=400)
        return Response(PartSerializer(self.get_object(sn)).data)
