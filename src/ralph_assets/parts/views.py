# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from urllib import urlencode
from collections import defaultdict

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.forms.formsets import formset_factory

from ralph_assets.views.base import (
    AssetsBase,
    SubmoduleModeMixin,
)
from ralph_assets.parts.forms import ChangeBaseForm


class ChangePartsView(SubmoduleModeMixin, AssetsBase):
    detect_changes = True
    template_name = 'assets/parts/change_parts.html'
    prefixes = ['in', 'out']
    form_values = ['sn']

    def _to_url_params(self, formsets):
        # TODO: please, make me less complex and more beautiful
        params = {}
        data_dict = defaultdict(list)
        for key, formset in formsets.iteritems():
            for data in formset.cleaned_data:
                for data_key, data_value in data.iteritems():
                    if data_key in self.form_values:
                        dict_key = '{}_{}'.format(
                            key.replace('_formset', ''), data_key
                        )
                        data_dict[dict_key].append(data_value)
        for key, value in data_dict.iteritems():
            params[key] = ','.join(value)
        return urlencode(params)

    def get_formset(self, prefix):
        return formset_factory(ChangeBaseForm)(
            self.request.POST or None, prefix=prefix
        )

    def get_formsets(self):
        formsets = {}
        for prefix in self.prefixes:
            formsets['{}_formset'.format(prefix)] = self.get_formset(prefix)
        return formsets

    def get(self, request, *args, **kwargs):
        kwargs.update(self.get_formsets())
        return super(ChangePartsView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        formsets = self.get_formsets()
        is_valid = True
        for formset in formsets.viewvalues():
            if not formset.is_valid():
                is_valid = False
        if is_valid:
            encoded_params = self._to_url_params(formsets)
            # TODO: redirect to step 2
            redirect_url = '{}?{}'.format(
                reverse('change_parts', kwargs={
                    'asset_id': kwargs['asset_id']
                }),
                encoded_params
            )
            return HttpResponseRedirect(redirect_url)
        kwargs.update(formsets)
        return super(ChangePartsView, self).get(request, *args, **kwargs)
