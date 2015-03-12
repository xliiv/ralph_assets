# -*- coding: utf-8 -*-
"""Forms for support module."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.db.models import Q
from django.forms import ChoiceField
from django.utils.translation import ugettext_lazy as _
from django_search_forms.fields import (
    SearchField,
    TextSearchField,
)
from django_search_forms.fields_ajax import RelatedAjaxSearchField
from django_search_forms.form import SearchForm


from ralph_assets.models_parts import Part, PartModelType
from ralph_assets.forms import LOOKUPS


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
