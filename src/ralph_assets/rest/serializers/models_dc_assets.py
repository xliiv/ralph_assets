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
TYPE_PDU = 'pdu'


class RackAccessorySerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='accessory.name')
    _type = serializers.SerializerMethodField('get_type')

    def get_type(self, obj):
        return TYPE_ACCESSORY

    class Meta:
        model = RackAccessory
        fields = ('position', 'remarks', 'type', '_type')


class PDUSerializer(serializers.ModelSerializer):
    model = serializers.CharField(source='model.name')
    orientation = serializers.IntegerField(source='get_orientation_desc')
    url = serializers.CharField(source='url')

    def get_type(self, obj):
        return TYPE_PDU

    class Meta:
        model = Asset
        fields = ('model', 'sn', 'orientation', 'url')


class RackSerializer(serializers.ModelSerializer):
    free_u = serializers.IntegerField(source='get_free_u', read_only=True)
    orientation = serializers.CharField(source='get_orientation_desc')
    rack_admin_url = serializers.SerializerMethodField('get_rack_admin_url')

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

    def get_rack_admin_url(self, obj):
        return reverse(
            'admin:ralph_assets_rack_change', args=(obj.id,),
        )


class DCSerializer(serializers.ModelSerializer):
    rack_set = RackSerializer()

    class Meta:
        model = DataCenter
        fields = ('id', 'name', 'visualization_cols_num',
                  'visualization_rows_num', 'rack_set')
        depth = 1
