# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.http import Http404

from rest_framework.response import Response
from rest_framework.views import APIView

from ralph.ui.views.common import ACLGateway
from ralph_assets.models_assets import Asset
from ralph_assets.rest.serializers.models_parts import PartSerializer


class AssetPartsView(ACLGateway, APIView):

    def get_object(self, pk):
        try:
            return Asset.objects.get(id=pk)
        except Asset.DoesNotExist:
            raise Http404

    def get(self, request, asset_id, format=None):
        asset = self.get_object(asset_id)
        return Response(PartSerializer(asset.parts.all(), many=True).data)
