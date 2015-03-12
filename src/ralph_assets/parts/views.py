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
from ralph_assets.parts.forms import ChangeBaseForm, DeattachForm


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
class AssignToAssetView(SubmoduleModeMixin, AssetsBase):

    #TODO:: what's this?
    #detect_changes = True
    template_name = 'assets/parts/assign_to_asset.html'

    #def get_formset(self, prefix):
    #    return formset_factory(ChangeBaseForm)(
    #        self.request.POST or None, prefix=prefix
    #    )

    def get_formset(self):
        return modelformset_factory(Part, form=DeattachForm, extra=0)

    def get_context_data(self, *args, **kwargs):
        #self.mode = 'dc'
        context = super(AssignToAssetView, self).get_context_data(
            *args, **kwargs
        )
        context['asset_id'] = kwargs['asset_id']
        return context

    def get(self, request, *args, **kwargs):
        # TODO:: make it the same to attached
        attach_sns = [3, 4]

        deattach_sns = [1, 2]
        existing_sns = Part.objects.filter(pk__in=deattach_sns).values_list('pk', flat=True)
        up_to_create_sns = set(deattach_sns)
        up_to_create_sns.difference_update(set(existing_sns))

        parts_to_create = []
        for sn in up_to_create_sns:
            part = Part(sn=sn)
            parts_to_create.append(part)
        Part.objects.bulk_create(parts_to_create)

        # deattach form
        deattach_parts = Part.objects.filter(id__in=deattach_sns)
        context = self.get_context_data(**kwargs)
        context['deattach_formset'] = modelformset_factory(
            Part, form=DeattachForm, extra=0
        )(queryset=deattach_parts)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):

        deattach_formset = self.get_formset()(request.POST)
        if deattach_formset.is_valid():
            #TODO:: deattach parts
            pass
            #TODO:: better url
            messages.info(self.request, _('fak yea'))
            return HttpResponseRedirect('/assets')
        else:
            context = self.get_context_data(**kwargs)
            context['deattach_formset'] = deattach_formset
            return self.render_to_response(context)
