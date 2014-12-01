# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.utils.translation import ugettext as _

from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND
from rest_framework.views import APIView

from ralph_assets.models_assets import Rack, DeviceInfo
from ralph_assets.views.base import ACLGateway


class AssetInfoPerRackAPIView(ACLGateway, APIView):
    """
    Collect and return information for visualization of racks.
    """
    def get(self, request, rack_id, format=None):
        """
        Collecting asset and device_info information for given rack id.

        :param rack_id int: rack id
        :returns list: list of informations about assets
        """
        try:
            rack = Rack.objects.get(id=rack_id)
        except Rack.DoesNotExist:
            return Response({
                'status': False,
                'message': _('Rack with id `{0}` does not exist'.format(
                    rack_id
                )),
            }, status=HTTP_404_NOT_FOUND)

        results = []
        for device_info in DeviceInfo.objects.filter(
            rack=rack,
        ).select_related(
            'asset__model',
        ):
            results.append({
                'asset_id': device_info.asset.id,
                'model': device_info.asset.model.name,
                'barcode': device_info.asset.barcode,
                'sn': device_info.asset.sn,
                'url': device_info.asset.url,
                'position': device_info.position,
                'height_of_device': device_info.asset.model.height_of_device,
            })

        return Response({'status': True, 'data': results})
