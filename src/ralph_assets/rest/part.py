# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rest_framework.response import Response
from rest_framework.views import APIView

from ralph.ui.views.common import ACLGateway
from ralph_assets.models_parts import Part
from ralph_assets.rest.serializers.models_parts import PartSerializer


class PartsView(ACLGateway, APIView):
    def get_object(self, sn):
        try:
            return Part.objects.get(sn=sn)
        except Part.DoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        sn = None
        try:
            sn = int(self.request.QUERY_PARAMS.get('sn', 0))
        except ValueError:
            return Response(status=400)
        obj = self.get_object(sn)
        return Response(PartSerializer(obj).data, status=obj and 200 or 404)
