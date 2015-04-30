# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rest_framework import serializers

from ralph_assets.models_parts import Part


class PartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Part
        fields = (
            'sn', 'order_no', 'price', 'service', 'part_environment',
            'warehouse'
        )
