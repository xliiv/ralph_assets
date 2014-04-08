# -*- coding: utf-8 -*-
"""Forms for SAM module."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from ajax_select.fields import (
    AutoCompleteField,
    AutoCompleteWidget,
    AutoCompleteSelectMultipleField,
)
from django import forms
from django.utils.translation import ugettext_lazy as _

from ralph.ui.widgets import DateWidget
from ralph_assets import models_sam
from ralph_assets.forms import LOOKUPS
from ralph_assets.models_assets import MODE2ASSET_TYPE


class SoftwareCategoryWidget(AutoCompleteWidget):
    """A widget for SoftwareCategoryField."""

    def render(self, name, value, attrs=None):
        if isinstance(value, basestring):
            sc_name = value
        else:
            try:
                sc_name = models_sam.SoftwareCategory.objects.get(
                    pk=value
                ).name
            except models_sam.SoftwareCategory.DoesNotExist:
                sc_name = ''
        return super(
            SoftwareCategoryWidget, self
        ).render(name, sc_name, attrs)


class SoftwareCategoryField(AutoCompleteField):
    """A field that either finds or creates a SoftwareCategory. NOTE:
    these values are *not* saved. The view should save it after validating
    the whole form"""

    def clean(self, value):
        value = super(SoftwareCategoryField, self).clean(value)
        try:
            return models_sam.SoftwareCategory.objects.get(
                name=value
            )
        except models_sam.SoftwareCategory.DoesNotExist:
            return models_sam.SoftwareCategory(
                name=value
            )


class LicenceForm(forms.ModelForm):
    """Licence add/edit form for licences."""

    def __init__(self, mode, *args, **kwargs):
        self.mode = mode
        super(LicenceForm, self).__init__(*args, **kwargs)

    software_category = SoftwareCategoryField(
        ('ralph_assets.models_sam', 'SoftwareCategoryLookup'),
        widget=SoftwareCategoryWidget,
    )

    assets = AutoCompleteSelectMultipleField(LOOKUPS['asset'], required=False)

    def clean(self, *args, **kwargs):
        result = super(LicenceForm, self).clean(*args, **kwargs)
        if len(result.get('assets', [])) > result.get('number_bought'):
            raise forms.ValidationError(_(
                "You don't have sufficient licences!"
            ))
        if 'software_category' not in result:
            return result
        if result['software_category'].asset_type is None:
            result['software_category'].asset_type = MODE2ASSET_TYPE[self.mode]
        if result['software_category'].pk is None:
            result['software_category'].save()
        return result

    class Meta:
        model = models_sam.Licence
        fields = (
            'manufacturer',
            'licence_type',
            'property_of',
            'software_category',
            'number_bought',
            'sn',
            'parent',
            'niw',
            'bought_date',
            'valid_thru',
            'order_no',
            'price',
            'accounting_id',
            'assets',
        )
        widgets = {
            'bought_date': DateWidget,
            'valid_thru': DateWidget,
        }
