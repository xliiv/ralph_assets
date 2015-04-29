# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from rest_framework import serializers

from ralph_assets.models_dc_assets import (
    DataCenter,
    Rack,
    RackAccessory,
    RackOrientation,
)
from ralph_assets.models import Asset


TYPE_EMPTY = 'empty'
TYPE_ACCESSORY = 'accessory'
TYPE_ASSET = 'asset'
TYPE_PDU = 'pdu'


class AdminMixin(serializers.ModelSerializer):
    """
    A field that returns object's admin url
    """

    def admin_link(self, obj):
        return reverse('admin:{app_label}_{module_name}_change'.format(
            app_label=obj._meta.app_label,
            module_name=obj._meta.module_name,
        ), args=(obj.id,))


class AssetSerializerBase(serializers.ModelSerializer):
    model = serializers.CharField(source='model.name')
    url = serializers.SerializerMethodField('get_absolute_url')
    core_url = serializers.SerializerMethodField('get_core_url')
    hostname = serializers.SerializerMethodField('get_hostname')
    service = serializers.CharField(source='service.name')
    orientation = serializers.SerializerMethodField('get_orientation')

    def get_orientation(self, obj):
        if not hasattr(obj.device_info, 'get_orientation_desc'):
            return 'front'
        return obj.device_info.get_orientation_desc()

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    def get_core_url(self, obj):
        """
        Return the URL to device in core.
        """
        url = None
        device_core_id = obj.device_info.ralph_device.id
        if device_core_id:
            url = reverse('search', kwargs={
                'details': 'info', 'device': device_core_id
            })
        return url

    def get_hostname(self, obj):
        device = obj.linked_device
        return device.name if device else ''


class RelatedAssetSerializer(AssetSerializerBase):
    slot_no = serializers.CharField(source='device_info.slot_no')

    class Meta:
        model = Asset
        fields = (
            'id', 'model', 'barcode', 'sn', 'slot_no', 'url', 'core_url',
            'hostname', 'service', 'orientation'
        )


class AssetSerializer(AssetSerializerBase):
    category = serializers.CharField(source='model.category.name')
    height = serializers.FloatField(source='model.height_of_device')
    front_layout = serializers.CharField(source='model.get_front_layout_class')
    back_layout = serializers.CharField(source='model.get_back_layout_class')
    position = serializers.IntegerField(source='device_info.position')
    children = RelatedAssetSerializer(
        source='get_related_assets',
        many=True,
    )
    _type = serializers.SerializerMethodField('get_type')
    management_ip = serializers.SerializerMethodField('get_management')
    url = serializers.SerializerMethodField('get_absolute_url')

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
            'id', 'model', 'category', 'height', 'front_layout', 'back_layout',
            'barcode', 'sn', 'url', 'core_url', 'position', 'children',
            '_type', 'hostname', 'management_ip', 'service', 'orientation'
        )


class RackAccessorySerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='accessory.name')
    _type = serializers.SerializerMethodField('get_type')
    orientation = serializers.SerializerMethodField('get_orientation')

    def get_type(self, obj):
        return TYPE_ACCESSORY

    def get_orientation(self, obj):
        return obj.get_orientation_desc()

    class Meta:
        model = RackAccessory
        fields = ('position', 'orientation', 'remarks', 'type', '_type')


class PDUSerializer(serializers.ModelSerializer):
    model = serializers.CharField(source='model.name')
    orientation = serializers.IntegerField(source='get_orientation_desc')
    url = serializers.CharField(source='get_absolute_url')

    def get_type(self, obj):
        return TYPE_PDU

    class Meta:
        model = Asset
        fields = ('model', 'sn', 'orientation', 'url')


class RackSerializer(AdminMixin, serializers.ModelSerializer):
    free_u = serializers.IntegerField(source='get_free_u', read_only=True)
    orientation = serializers.CharField(source='get_orientation_desc')
    rack_admin_url = serializers.SerializerMethodField('admin_link')

    class Meta:
        model = Rack
        fields = (
            'id', 'name', 'data_center', 'server_room', 'max_u_height',
            'visualization_col', 'visualization_row', 'free_u', 'description',
            'orientation', 'rack_admin_url',
        )

    def update(self):
        orientation = self.data['orientation']
        self.object.orientation = RackOrientation.id_from_name(orientation)
        return self.save(**self.data)


class DCSerializer(AdminMixin, serializers.ModelSerializer):
    rack_set = RackSerializer()
    admin_link = serializers.SerializerMethodField('admin_link')

    class Meta:
        model = DataCenter
        fields = ('id', 'name', 'visualization_cols_num',
                  'visualization_rows_num', 'rack_set', 'admin_link')
        depth = 1
