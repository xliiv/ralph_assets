# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.core.urlresolvers import reverse

from rest_framework import serializers

from ralph_assets.models_assets import Asset


TYPE_ASSET = 'asset'


class CoreDeviceMixin(object):
    def get_core_url(self, obj):
        """
        Return the URL to device in core.
        """
        url = None
        device_core_id = obj.device_info.ralph_device_id
        if device_core_id:
            url = reverse('search', kwargs={
                'details': 'info', 'device': device_core_id
            })
        return url

    def get_hostname(self, obj):
        device = obj.linked_device
        return device.name if device else ''


class RelatedAssetSerializer(CoreDeviceMixin, serializers.ModelSerializer):
    model = serializers.CharField(source='model.name')
    slot_no = serializers.CharField(source='device_info.slot_no')
    url = serializers.CharField(source='url')
    core_url = serializers.SerializerMethodField('get_core_url')
    hostname = serializers.SerializerMethodField('get_hostname')
    service = serializers.CharField(source='service.name')

    class Meta:
        model = Asset
        fields = (
            'id', 'model', 'barcode', 'sn', 'slot_no', 'url', 'core_url',
            'hostname', 'service',
        )


class AssetSerializer(CoreDeviceMixin, serializers.ModelSerializer):
    model = serializers.CharField(source='model.name')
    category = serializers.CharField(source='model.category.name')
    height = serializers.FloatField(source='model.height_of_device')
    layout = serializers.CharField(source='model.get_layout_class')
    url = serializers.CharField(source='url')
    core_url = serializers.SerializerMethodField('get_core_url')
    position = serializers.IntegerField(source='device_info.position')
    children = RelatedAssetSerializer(source='get_related_assets')
    _type = serializers.SerializerMethodField('get_type')
    hostname = serializers.SerializerMethodField('get_hostname')
    management_ip = serializers.SerializerMethodField('get_management')
    service = serializers.CharField(source='service.name')

    def get_type(self, obj):
        return TYPE_ASSET

    def get_management(self, obj):
        device = obj.linked_device
        if not device:
            return ''
        management_ip = device.management_ip
        return management_ip.address if management_ip else ''

    class Meta:
        model = Asset
        fields = (
            'id', 'model', 'category', 'height', 'layout', 'barcode', 'sn',
            'url', 'core_url', 'position', 'children', '_type', 'hostname',
            'management_ip', 'service',
        )
