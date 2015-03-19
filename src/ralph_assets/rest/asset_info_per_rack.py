# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.http import Http404

from rest_framework.response import Response
from rest_framework.views import APIView

from ralph_assets.models_assets import Orientation, Rack
from ralph_assets.models_dc_assets import RackAccessory
from ralph.ui.views.common import ACLGateway
from ralph_assets.rest.serializers.models_assets import AssetSerializer
from ralph_assets.rest.serializers.models_dc_assets import (
    RackAccessorySerializer,
    RackSerializer,
    PDUSerializer,
)


class AssetsView(ACLGateway, APIView):

    def get_object(self, pk):
        try:
            return Rack.objects.get(id=pk)
        except Rack.DoesNotExist:
            raise Http404

    def _get_assets(self, rack, side):
        return AssetSerializer(rack.get_root_assets(side), many=True).data

    def _get_accessories(self, rack, side):
        accessories = RackAccessory.objects.select_related('accessory').filter(
            rack=rack,
            orientation=side,
        )
        return RackAccessorySerializer(accessories, many=True).data

    def _get_pdus(self, rack):
        return PDUSerializer(rack.get_pdus(), many=True).data

    def get(self, request, rack_id, format=None):
        rack = self.get_object(rack_id)
        devices = {}
        for side in [Orientation.front, Orientation.back]:
            devices[side.desc] = (
                self._get_assets(rack, side) +
                self._get_accessories(rack, side)
            )
        devices['pdus'] = self._get_pdus(rack)
        devices['info'] = RackSerializer(rack).data
        return Response(devices)

    def put(self, request, rack_id, format=None):
        serializer = RackSerializer(
            self.get_object(rack_id), data=request.DATA)
        if serializer.is_valid():
            serializer.update()
            return Response(serializer.data)
        return Response(serializer.errors)
