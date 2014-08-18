# -*- coding: utf-8 -*-
"""Forms for support module."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from ajax_select.fields import AutoCompleteSelectMultipleField
from collections import OrderedDict
from django import forms
from django.forms.widgets import Textarea
from django.utils.translation import ugettext_lazy as _

from django_search_forms.fields import (
    DateRangeSearchField,
    RelatedSearchField,
    TextSearchField,
)
from django_search_forms.form import SearchForm

from ralph.ui.widgets import DateWidget
from ralph_assets import models_support
from ralph_assets.forms import LOOKUPS
from ralph_assets.models_support import SupportType


class SupportForm(forms.ModelForm):
    """Support add/edit form for supports."""

    class Meta:
        model = models_support.Support
        fieldset = OrderedDict([
            ('Info', [
                'asset_type', 'support_type', 'status', 'contract_id', 'name',
                'description', 'price', 'date_from', 'date_to',
                'escalation_path', 'contract_terms', 'additional_notes',
                'sla_type', 'producer', 'supplier', 'serial_no', 'invoice_no',
                'invoice_date', 'period_in_months', 'property_of',
            ]),
        ])
        widgets = {
            'date_from': DateWidget,
            'date_to': DateWidget,
            'description': Textarea(attrs={'rows': 5}),
            'escalation_path': Textarea(attrs={'rows': 5}),
            'contract_terms': Textarea(attrs={'rows': 5}),
            'additional_notes': Textarea(attrs={'rows': 5}),
            'sla_type': Textarea(attrs={'rows': 5}),
            'invoice_date': DateWidget,
        }
        fields = (
            'additional_notes',
            'asset_type',
            'contract_id',
            'contract_terms',
            'date_from',
            'date_to',
            'description',
            'escalation_path',
            'invoice_date',
            'invoice_no',
            'name',
            'period_in_months',
            'price',
            'producer',
            'property_of',
            'serial_no',
            'sla_type',
            'status',
            'supplier',
            'support_type',
        )

    def __init__(self, mode, *args, **kwargs):
        self.mode = mode
        super(SupportForm, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        result = super(SupportForm, self).clean(*args, **kwargs)
        return result


class AddSupportForm(SupportForm):
    """Support add form for supports."""


class EditSupportForm(SupportForm):
    """Support edit form for supports."""

    assets = AutoCompleteSelectMultipleField(
        LOOKUPS['asset_all'], required=False
    )

    class Meta(SupportForm.Meta):
        fieldset = OrderedDict([
            ('Info', [
                'asset_type', 'support_type', 'status', 'contract_id', 'name',
                'description', 'price', 'date_from', 'date_to',
                'escalation_path', 'contract_terms', 'additional_notes',
                'sla_type', 'producer', 'supplier', 'serial_no', 'invoice_no',
                'invoice_date', 'period_in_months', 'property_of', 'assets',
            ]),
        ])
        fields = (
            'additional_notes',
            'asset_type',
            'assets',
            'contract_id',
            'contract_terms',
            'date_from',
            'date_to',
            'description',
            'escalation_path',
            'invoice_date',
            'invoice_no',
            'name',
            'period_in_months',
            'price',
            'producer',
            'property_of',
            'serial_no',
            'sla_type',
            'status',
            'supplier',
            'support_type',
        )


class SupportSearchForm(SearchForm):
    class Meta(object):
        Model = models_support.Support
        fields = []
    support_type = RelatedSearchField(SupportType)
    contract_id = TextSearchField()
    name = TextSearchField()
    description = TextSearchField()
    date_from = DateRangeSearchField()
    date_to = DateRangeSearchField()
    additional_notes = TextSearchField()
    assets = TextSearchField(
        filter_field='assets__sn', label=_('by sn (of assigned asset)'),
    )
