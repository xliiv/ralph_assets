# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django import forms


class ChangeBaseForm(forms.Form):
    sn = forms.CharField()


# TODO:: clean it
from django.forms import (
    ModelForm,
)
from ralph_assets.models_parts import Part
class DetachForm(ModelForm):
    class Meta:
        model = Part
        fields = (
            "asset_type", "model", "sn", "order_no", "price", "service",
            "part_environment", "warehouse"
        )
#TODO:: override clean so that it raise error when field in defined-list
