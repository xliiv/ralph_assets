# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.forms.formsets import formset_factory
from django.forms.models import modelformset_factory

from ralph_assets.views.base import (
    AssetsBase,
    SubmoduleModeMixin,
)
from ralph_assets.parts.forms import ChangeBaseForm, AttachForm, DetachForm


class DebugViewMixin(object):
    def get_context_data(self, **kwargs):
        import json
        context = super(DebugViewMixin, self).get_context_data(**kwargs)
        context['post_data'] = json.dumps(self.request.POST, indent=4)
        context['get_data'] = json.dumps(self.request.GET, indent=4)
        return context


class ChangePartsView(SubmoduleModeMixin, DebugViewMixin, AssetsBase):
    detect_changes = True
    template_name = 'assets/parts/change_parts.html'

    def get_formset(self, prefix):
        return formset_factory(ChangeBaseForm)(
            self.request.POST or None, prefix=prefix
        )

    def get_formsets(self):
        formsets = {}
        for prefix in ['add', 'delete']:
            formsets['{}_formset'.format(prefix)] = self.get_formset(prefix)
        return formsets

    def get(self, request, *args, **kwargs):
        kwargs.update(self.get_formsets())
        return super(ChangePartsView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        formsets = self.get_formsets()
        for formset in formsets.values():
            formset.is_valid()
        kwargs.update(formsets)
        return super(ChangePartsView, self).get(request, *args, **kwargs)




from ralph_assets.models_parts import Part
#TODO:: rename it
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from django.db import transaction
class AssignToAssetView(SubmoduleModeMixin, AssetsBase):

    #TODO:: what's this?
    #detect_changes = True
    template_name = 'assets/parts/assign_to_asset.html'

    def get_formset(self, prefix, queryset=None):
        if prefix == 'attach':
            form = AttachForm
        if prefix == 'detach':
            form = DetachForm
        return modelformset_factory(Part, form=form, extra=0)(
            self.request.POST or None, queryset=queryset, prefix=prefix
        )

    def get_context_data(self, *args, **kwargs):
        #self.mode = 'dc'
        context = super(AssignToAssetView, self).get_context_data(
            *args, **kwargs
        )
        context['asset_id'] = kwargs['asset_id']
        return context

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
        detach_sns = [1, 2]
        up_to_create_sns = self._find_non_existing(detach_sns)
        detach_parts = self._create_parts(up_to_create_sns, 'detach')

        attach_sns = [3, 4]
        up_to_create_sns2 = self._find_non_existing(attach_sns)
        attach_parts = self._create_parts(up_to_create_sns2, 'attach')

        Part.objects.bulk_create(detach_parts + attach_parts)

        # detach form
        context = self.get_context_data(**kwargs)
        detach_parts = Part.objects.filter(id__in=detach_sns)
        context['detach_formset'] = self.get_formset('detach', queryset=detach_parts)
        attach_parts = Part.objects.filter(id__in=attach_sns)
        context['attach_formset'] = self.get_formset('attach', queryset=attach_parts)
        return self.render_to_response(context)

    @transaction.commit_on_success
    def move_parts(self, detach_formset):
        #TODO:: docstring
        for form in detach_formset.forms:
            form.instance.asset = None
            #TODO:: optimize it
            form.instance.save()

    def post(self, request, *args, **kwargs):
        ###TODO:: save attach file & detach
        #TODO:: attach form - all fields
        #TODO:: detach form - service & environment
        detach_formset = self.get_formset('detach')
        attach_formset = self.get_formset('attach')
        if detach_formset.is_valid():
            #TODO:: validation: here and GET?
            #TODO:: force attach and detach are disjoint sets
            #TODO:: force parts here are from asset from url
            self.move_parts(detach_formset)

            msg = 'Successfully detached {} parts'.format(len(detach_formset.forms))
            messages.info(self.request, _(msg))
            #TODO:: better url
            return HttpResponseRedirect('/assets/parts')
        else:
            #TODO:: when part has different asset, what's then
            context = self.get_context_data(**kwargs)
            context['detach_formset'] = detach_formset
            return self.render_to_response(context)
