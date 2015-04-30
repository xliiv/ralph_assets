# -*- coding: utf-8 -*-
"""Forms for support module."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from ajax_select.fields import AutoCompleteSelectField
from collections import OrderedDict
from django.db.models import Q
from django.forms import ChoiceField, ModelForm
from django.forms.widgets import Textarea
from django.utils.translation import ugettext_lazy as _
from django_search_forms.fields import (
    SearchField,
    TextSearchField,
)
from django_search_forms.fields_ajax import RelatedAjaxSearchField
from django_search_forms.form import SearchForm

from ralph_assets.forms import (
    MultilineField,
    MultivalFieldForm,
    validate_snbcs,
)
from ralph_assets.forms import LOOKUPS
from ralph_assets.models_assets import AssetType
from ralph_assets.models_parts import Part, PartModelType


class ChoiceSearchField(SearchField, ChoiceField):
    def __init__(self, choices, *args, **kwargs):
        kwargs['choices'] = [('', '----')] + choices
        super(ChoiceSearchField, self).__init__(*args, **kwargs)

    def get_query(self, value):
        return Q(**{self.name: int(value)})


class PartSearchForm(SearchForm):
    class Meta(object):
        Model = Part
        fields = []
    model__model_type = ChoiceSearchField(
        required=False,
        choices=PartModelType(),
        label=_('Type'),
    )
    model = RelatedAjaxSearchField(
        ('ralph_assets.models', 'PartModelLookup'),
    )
    sn = TextSearchField(label=_('SN'),)
    order_no = TextSearchField()
    service = RelatedAjaxSearchField(
        LOOKUPS['service'],
        required=False,
    )


class EditPartForm(ModelForm):

    model = AutoCompleteSelectField(
        LOOKUPS['part_model'],
        required=True,
        plugin_options={
            'add_link': '/admin/ralph_assets/partmodel/add/?name=',
        },
    )
    service = AutoCompleteSelectField(
        LOOKUPS['service'],
        required=True,
        label=_('Service catalog'),
    )
    warehouse = AutoCompleteSelectField(
        LOOKUPS['part_warehouse'],
        required=True,
        plugin_options={
            'add_link': '/admin/ralph_assets/warehouse/add/?name=',
        }
    )

    class Meta:
        model = Part
        fields = (
            'asset_type',
            'model',
            'sn',
            'service',
            'part_environment',
            'warehouse',
            'order_no',
            'price',
        )

    def __init__(self, mode, *args, **kwargs):
        self.fieldsets = OrderedDict([
            (
                _('Basic Info'),
                [
                    'sn', 'asset_type', 'model', 'service',
                    'part_environment', 'warehouse',
                ],
            ),
            (_('Financial Info'), ['order_no', 'price']),
        ])
        self.mode = mode
        super(EditPartForm, self).__init__(*args, **kwargs)
        if self.mode == "dc":
            self.fields['asset_type'].choices = [
                (choice.id, choice.desc) for choice in AssetType.DC.choices
            ]
        elif self.mode == "back_office":
            self.fields['asset_type'].choices = [
                (choice.id, choice.desc) for choice in AssetType.BO.choices
            ]


class AddPartForm(EditPartForm, MultivalFieldForm):

    multival_fields = ['sn']

    sn = MultilineField(
        db_field_path='sn', label=_('SN/SNs'), required=True,
        widget=Textarea(attrs={'rows': 25}),
        validators=[validate_snbcs],
    )

    def __init__(self, *args, **kwargs):
        super(AddPartForm, self).__init__(*args, **kwargs)
        for fieldset_name, fields in self.fieldsets.iteritems():
            if 'sn' in fields:
                fields.remove('sn')
