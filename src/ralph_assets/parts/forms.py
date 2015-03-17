# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django import forms
from ralph_assets.forms import ReadOnlyFieldsMixin
from ralph_assets.models_parts import Part


class ChangeBaseForm(forms.Form):
    sn = forms.CharField()


class AttachForm(ReadOnlyFieldsMixin, forms.ModelForm):
    class Meta:
        model = Part
        fields = (
            "sn", "model", "order_no", "price", "service", "part_environment",
            "warehouse"
        )

class DetachForm(ReadOnlyFieldsMixin, forms.ModelForm):
    readonly_fields = (
        "model", "sn", "order_no", "price", "warehouse",
    )
    class Meta:
        #TODO:: validate service-env
        #TODO:: model autocomplete nice-to-have
        #TODO:: add service-env depenedency
        model = Part
        fields = (
            "sn", "model", "order_no", "price", "service", "part_environment",
            "warehouse"
        )
