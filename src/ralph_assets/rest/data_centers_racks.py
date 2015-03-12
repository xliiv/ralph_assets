# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.http import Http404

from rest_framework.response import Response
from rest_framework.views import APIView

from ralph.ui.views.common import ACLGateway
from ralph_assets.models_assets import DataCenter
from ralph_assets.rest.serializers.models_dc_assets import DCSerializer


class DCRacksAPIView(ACLGateway, APIView):
    """
    Return information of list rack in data center with their positions.
    """
    def get_object(self, pk):
        try:
            return DataCenter.objects.get(id=pk)
        except DataCenter.DoesNotExist:
            raise Http404

    def get(self, request, data_center_id, format=None):
        """
        Collecting racks information for given data_center id.

        :param data_center_id int: data_center id
        :returns list: list of informations about racks in given data center
        """
        return Response(
            DCSerializer(self.get_object(data_center_id)).data
        )
