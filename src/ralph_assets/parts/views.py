# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.forms.formsets import formset_factory

from ralph_assets.views.base import (
    AssetsBase,
    SubmoduleModeMixin,
)
from ralph_assets.parts.forms import ChangeBaseForm


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

