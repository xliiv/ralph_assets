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
    readonly_fields = (
        "sn", "model", "order_no", "price", "service", "part_environment",
        "warehouse"
    )
    class Meta:
        model = Part
        fields = (
            "sn", "model", "order_no", "price", "service", "part_environment",
            "warehouse"
        )

from django.forms import (
    ModelChoiceField,
)
from ajax_select.fields import (
    AutoCompleteSelectField,
)
from ralph_assets.forms import LOOKUPS
from ralph.discovery import models_device
from django.utils.translation import ugettext_lazy as _
from ralph.ui.forms.devices import ServiceCatalogMixin
from ajax_select.fields import (
    AutoCompleteSelectField,
    CascadeModelChoiceField,
)
from ralph.discovery.models import (
    ASSET_NOT_REQUIRED,
    Device,
    DeviceEnvironment,
    DeviceType,
)
class DetachForm(ReadOnlyFieldsMixin, forms.ModelForm):
    readonly_fields = ("order_no",)
    class Meta:
        model = Part
        fields = (
            "sn", "model", "order_no", "price", "service", "part_environment",
            "warehouse"
        )

    service = AutoCompleteSelectField(
        ('ralph.ui.channels', 'ServiceCatalogLookup'),
        required=True,
        label=_('Service catalog'),
    )
    part_environment = CascadeModelChoiceField(
        ('ralph.ui.channels', 'DeviceEnvironmentLookup'),
        label=_('Device environment'),
        queryset=DeviceEnvironment.objects.all(),
        parent_field=service,
    )
    def __init__(self, *args, **kwargs):
        super(DetachForm, self).__init__(*args, **kwargs)
        self['part_environment'].field.widget.attrs['data-parent-id'] = self['service'].auto_id
