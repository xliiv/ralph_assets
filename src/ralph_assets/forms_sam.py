# -*- coding: utf-8 -*-
"""Forms for SAM module."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from ajax_select.fields import (
    AutoCompleteSelectField,
    AutoCompleteSelectMultipleField,
    AutoCompleteWidget,
)
from collections import OrderedDict
from django import forms
from django.utils.translation import ugettext_lazy as _
from django_search_forms.form import SearchForm
from django_search_forms.fields import (
    DateRangeSearchField,
    ExactSearchField,
    MultiSearchField,
    RelatedSearchField,
    TextSearchField,
)
from django_search_forms.fields_ajax import RelatedAjaxSearchField

from ralph.ui.widgets import DateWidget
from ralph_assets import models_sam
from ralph_assets.forms import LOOKUPS, MultilineField, MultivalFieldForm
from ralph_assets.models_assets import MODE2ASSET_TYPE
from ralph_assets.models_sam import AssetOwner, LicenceType


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


class SoftwareCategoryField(AutoCompleteSelectField):
    """A field that either finds or creates a SoftwareCategory. NOTE:
    these values are *not* saved. The view should save it after validating
    the whole form"""

    def clean(self, value):
        value = super(SoftwareCategoryField, self).clean(value)
        try:
            return models_sam.SoftwareCategory.objects.get(
                name=value)
        except models_sam.SoftwareCategory.DoesNotExist:
            return models_sam.SoftwareCategory(
                name=value
            )


class LicenceForm(forms.ModelForm):
    """Base form for licences."""

    class Meta:
        fieldset = OrderedDict([
            ('Basic info', [
                'asset_type', 'manufacturer', 'licence_type',
                'software_category', 'parent', 'niw', 'sn', 'property_of',
                'valid_thru', 'assets', 'remarks', 'service_name',
            ]),
            ('Financial info', [
                'order_no', 'invoice_date', 'invoice_no', 'price', 'provider',
                'number_bought', 'accounting_id'
            ]),
        ])
        widgets = {
            'invoice_date': DateWidget,
            'valid_thru': DateWidget,
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }

    parent = AutoCompleteSelectField(
        ('ralph_assets.models', 'LicenceLookup'),
        required=False,
        label=_('Parent licence'),
    )

    def __init__(self, mode, *args, **kwargs):
        self.mode = mode
        super(LicenceForm, self).__init__(*args, **kwargs)

    software_category = SoftwareCategoryField(
        ('ralph_assets.models_sam', 'SoftwareCategoryLookup'),
        widget=SoftwareCategoryWidget,
        plugin_options=dict(
            add_link='/admin/ralph_assets/softwarecategory/add/?name=',
        )
    )

    manufacturer = AutoCompleteSelectField(
        ('ralph_assets.models', 'ManufacturerLookup'),
        widget=AutoCompleteWidget,
        plugin_options=dict(
            add_link='/admin/ralph_assets/assetmanufacturer/add/',
        ),
        required=False,
    )

    assets = AutoCompleteSelectMultipleField(
        LOOKUPS['asset'], required=False, label=_('Assigned Assets')
    )

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


class AddLicenceForm(LicenceForm, MultivalFieldForm):
    """Class for adding a licence or multiple licences."""

    def __init__(self, *args, **kwargs):
        super(AddLicenceForm, self).__init__(*args, **kwargs)
        self.multival_fields = ['sn', 'niw']

    class Meta(LicenceForm.Meta):
        model = models_sam.Licence
        fields = (
            'asset_type',
            'manufacturer',
            'licence_type',
            'property_of',
            'software_category',
            'number_bought',
            'parent',
            'invoice_date',
            'valid_thru',
            'order_no',
            'price',
            'accounting_id',
            'provider',
            'invoice_no',
        )

    sn = MultilineField(
        db_field_path='sn',
        label=_('Licence key'),
        required=True,
        widget=forms.Textarea(attrs={'rows': 25}),
    )
    niw = MultilineField(
        db_field_path='niw',
        label=_('Inventory number'),
        required=True,
        widget=forms.Textarea(attrs={'rows': 25}),
    )

    def clean(self):
        data = super(AddLicenceForm, self).clean()
        self.different_multival_counters(data)
        return data


class EditLicenceForm(LicenceForm):
    """Form for licence edit."""

    class Meta(LicenceForm.Meta):
        model = models_sam.Licence
        fields = (
            'asset_type',
            'manufacturer',
            'licence_type',
            'property_of',
            'software_category',
            'number_bought',
            'parent',
            'invoice_date',
            'valid_thru',
            'order_no',
            'price',
            'accounting_id',
            'assets',
            'provider',
            'invoice_no',
            'sn',
            'niw',
            'remarks',
            'service_name',
        )

    sn = forms.CharField(widget=forms.Textarea, label=_('Licence key'))
    niw = forms.CharField(label=_('Inventory number'))


class SoftwareCategorySearchForm(SearchForm):
    class Meta(object):
        Model = models_sam.SoftwareCategory
        fields = ['name']


class LicenceSearchForm(SearchForm):
    class Meta(object):
        Model = models_sam.Licence
        fields = []
    niw = MultiSearchField(label=_('NIW'))
    sn = TextSearchField(label=_('SN'))
    remarks = TextSearchField(label=_('Additional remarks'))
    software_category = RelatedAjaxSearchField(
        LOOKUPS['softwarecategory'],
    )
    property_of = RelatedSearchField(Model=AssetOwner)
    licence_type = RelatedSearchField(LicenceType)
    parent_licence = RelatedAjaxSearchField(
        LOOKUPS['licence']
    )
    valid_thru = DateRangeSearchField()
    invoice_no = ExactSearchField()
    invoice_date = DateRangeSearchField()
    order_no = ExactSearchField()
    order_date = DateRangeSearchField()
    id = MultiSearchField(widget=forms.HiddenInput())
