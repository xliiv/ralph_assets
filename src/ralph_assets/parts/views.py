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
from django.forms.models import modelformset_factory

from ralph_assets.parts.forms import ChangeBaseForm, AttachForm, DetachForm
from ralph_assets.models_assets import Asset
from ralph_assets.views.base import (
    AssetsBase,
    SubmoduleModeMixin,
)


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


from ralph_assets.models_parts import Part
#TODO:: rename it
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from django.db import transaction
class AssignToAssetView(SubmoduleModeMixin, AssetsBase):

    template_name = 'assets/parts/assign_to_asset.html'

    def get_formset(self, prefix, queryset=None):
        if prefix == 'attach':
            form = AttachForm
        if prefix == 'detach':
            form = DetachForm
        FormsetClass = modelformset_factory(Part, form=form, extra=0)

        class FromsetWithCustomValidation(FormsetClass):
            def is_valid(self, asset, *args, **kwargs):
                #TODO:: validation: here and GET?
                #TODO:: force attach and detach are disjoint sets
                return super(FromsetWithCustomValidation, self).is_valid(*args, **kwargs)

        return FromsetWithCustomValidation(
            self.request.POST or None, queryset=queryset, prefix=prefix
        )

    def _find_non_existing(self, sns):
        existing_sns = Part.objects.filter(
            pk__in=sns,
        ).values_list('pk', flat=True)
        up_to_create_sns = set(sns)
        up_to_create_sns.difference_update(set(existing_sns))
        return up_to_create_sns

    def _create_parts(self, sns, part_type):
        #TODO:: doctring
        parts = []
        for sn in sns:
            #TODO:: create part with necessery data
            part = Part(sn=sn)
            parts.append(part)
        return parts

    def get(self, request, *args, **kwargs):
        #TODO:: is part really from processed asset?
        #TODO:: get it from request
        detach_sns = [1, 2]

        up_to_create_sns = self._find_non_existing(detach_sns)
        detach_parts = self._create_parts(up_to_create_sns, 'detach')

        attach_sns = [3, 4]
        up_to_create_sns2 = self._find_non_existing(attach_sns)
        attach_parts = self._create_parts(up_to_create_sns2, 'attach')

        Part.objects.bulk_create(detach_parts + attach_parts)

        # detach form
        detach_parts = Part.objects.filter(id__in=detach_sns)
        kwargs['detach_formset'] = self.get_formset('detach', queryset=detach_parts)
        attach_parts = Part.objects.filter(id__in=attach_sns)
        kwargs['attach_formset'] = self.get_formset('attach', queryset=attach_parts)

        is_valid = (kwargs['detach_formset'].is_valid() and kwargs['attach_formset'].is_valid())
        if not is_valid:
            msg = 'Some of selected parts are not from edited asset'
            messages.wanring(request, _(msg))
        return super(AssignToAssetView, self).get(request, *args, **kwargs)

    @transaction.commit_on_success
    def move_parts(self, asset, attach_formset, detach_formset):
        #TODO:: docstring
        #TODO:: optimize it + make one loop
        for form in detach_formset.forms:
            form.save(commit=False)
            form.instance.asset = None
            form.instance.save()

        for form in attach_formset.forms:
            form.save(commit=False)
            form.instance.asset = asset
            form.instance.save()

    def post(self, request, *args, **kwargs):
        detach_formset = self.get_formset('detach')
        attach_formset = self.get_formset('attach')
        if detach_formset.is_valid():
            asset = Asset.objects.get(pk=kwargs['asset_id'])
            self.move_parts(asset, attach_formset, detach_formset)

            msg = 'Successfully detached {} parts'.format(len(detach_formset.forms))
            messages.info(self.request, _(msg))
            #TODO:: better url
            return HttpResponseRedirect('/assets/parts')
        else:
            kwargs['detach_formset'] = detach_formset
            kwargs['attach_formset'] = attach_formset
            return super(AssignToAssetView, self).get(request, *args, **kwargs)
