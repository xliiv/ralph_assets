# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
from collections import Counter

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db import transaction
from django.forms.models import formset_factory
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404

from ralph.util.api_assets import get_device_components
from ralph_assets.forms import (
    AddDeviceForm,
    DeviceForm,
    MoveAssetPartForm,
    OfficeForm,
    SplitDevice,
)
from ralph_assets.models import Asset, AssetModel, PartInfo
from ralph_assets.models_history import AssetHistoryChange
from ralph_assets.models_assets import AssetType
from ralph_assets.views.base import AssetsBase
from ralph_assets.views.utils import (
    _create_device,
    _move_data,
    _update_office_info,
    _update_asset,
    _update_device_info,
)


logger = logging.getLogger(__name__)


class AddDevice(AssetsBase):
    template_name = 'assets/add_device.html'
    sidebar_selected = 'add device'

    def get_context_data(self, **kwargs):
        ret = super(AddDevice, self).get_context_data(**kwargs)
        ret.update({
            'asset_form': self.asset_form,
            'additional_info': self.additional_info,
            'form_id': 'add_device_asset_form',
            'edit_mode': False,
            'multivalue_fields': ['sn', 'barcode', 'imei'],
        })
        return ret

    def _set_additional_info_form(self):
        if self.mode == 'dc':
            # XXX: how to clean it?
            if self.request.method == 'POST':
                self.additional_info = DeviceForm(
                    self.request.POST,
                    mode=self.mode,
                    exclude='create_stock',
                )
            else:
                self.additional_info = DeviceForm(
                    mode=self.mode,
                    exclude='create_stock',
                )
        elif self.mode == 'back_office':
            if self.request.method == 'POST':
                self.additional_info = OfficeForm(self.request.POST)
            else:
                self.additional_info = OfficeForm()

    def get(self, *args, **kwargs):
        self.asset_form = AddDeviceForm(mode=self.mode)
        device_form_class = self.form_dispatcher('AddDevice')
        self.asset_form = device_form_class(mode=self.mode)
        self._set_additional_info_form()
        return super(AddDevice, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        device_form_class = self.form_dispatcher('AddDevice')
        self.asset_form = device_form_class(self.request.POST, mode=self.mode)
        self._set_additional_info_form()
        if self.asset_form.is_valid() and self.additional_info.is_valid():
            creator_profile = self.request.user.get_profile()
            asset_data = {}
            for f_name, f_value in self.asset_form.cleaned_data.items():
                if f_name not in {
                    "barcode", "category", "company", "cost_center",
                    "department", "employee_id", "imei", "licences", "manager",
                    "sn", "profit_center", "supports",
                }:
                    asset_data[f_name] = f_value
            sns = self.asset_form.cleaned_data.get('sn', [])
            barcodes = self.asset_form.cleaned_data.get('barcode', [])
            imeis = (
                self.asset_form.cleaned_data.pop('imei')
                if 'imei' in self.asset_form.cleaned_data else None
            )
            ids = []
            for index in range(len(sns or barcodes)):
                asset_data['sn'] = sns[index] if sns else None
                asset_data['barcode'] = barcodes[index] if barcodes else None
                if imeis:
                    self.additional_info.cleaned_data['imei'] = imeis[index]
                device = _create_device(
                    creator_profile,
                    asset_data,
                    self.additional_info.cleaned_data,
                    self.mode,
                )
                ids.append(device.id)
            messages.success(self.request, _("Assets saved."))
            cat = self.request.path.split('/')[2]
            if len(ids) == 1:
                return HttpResponseRedirect(
                    '/assets/%s/edit/device/%s/' % (cat, ids[0])
                )
            else:
                return HttpResponseRedirect(
                    '/assets/%s/bulkedit/?select=%s' % (
                        cat, '&select='.join(["%s" % id for id in ids]))
                )
        else:
            messages.error(self.request, _("Please correct the errors."))
        return super(AddDevice, self).get(*args, **kwargs)


class EditDevice(AssetsBase):
    detect_changes = True
    template_name = 'assets/edit_device.html'
    sidebar_selected = 'edit device'

    def initialize_vars(self, *args, **kwargs):
        self.asset = get_object_or_404(
            Asset.admin_objects,
            id=kwargs.get('asset_id'),
        )
        self.parts = Asset.objects.filter(part_info__device=self.asset)
        device_form_class = self.form_dispatcher('EditDevice')
        self.asset_form = device_form_class(
            self.request.POST or None,
            instance=self.asset,
            mode=self.mode,
        )
        self.part_form = MoveAssetPartForm(self.request.POST or None)
        self._set_additional_info_form()

    def get_context_data(self, **kwargs):
        ret = super(EditDevice, self).get_context_data(**kwargs)
        status_history = AssetHistoryChange.objects.all().filter(
            asset=kwargs.get('asset_id'), field_name__exact='status'
        ).order_by('-date')
        ret.update({
            'asset_form': self.asset_form,
            'additional_info': self.additional_info,
            'part_form': self.part_form,
            'form_id': 'edit_device_asset_form',
            'edit_mode': True,
            'status_history': status_history,
            'parts': self.parts,
            'asset': self.asset,
            'history_link': self.get_history_link(),
        })
        return ret

    def _update_additional_info(self, modifier):
        if self.asset.type in AssetType.DC.choices:
            self.asset = _update_device_info(
                modifier, self.asset, self.additional_info.cleaned_data
            )
            if self.additional_info.cleaned_data.get('create_stock'):
                self.asset.create_stock_device()
        elif self.asset.type in AssetType.BO.choices:
            new_src, new_dst = _move_data(
                self.asset_form.cleaned_data,
                self.additional_info.cleaned_data,
                ['imei', 'purpose'],
            )
            self.asset_form.cleaned_data = new_src
            self.additional_info.cleaned_data = new_dst
            self.asset = _update_office_info(
                modifier, self.asset, self.additional_info.cleaned_data
            )

    def _set_additional_info_form(self):
        if self.mode == 'dc':
            # XXX: how do it better, differ only by one arg?
            if self.request.method == 'POST':
                self.additional_info = DeviceForm(
                    self.request.POST,
                    instance=self.asset.device_info,
                    mode=self.mode,
                )
            else:
                self.additional_info = DeviceForm(
                    instance=self.asset.device_info,
                    mode=self.mode,
                )
        elif self.mode == 'back_office':
            # XXX: how do it better, differ only by one arg?
            if self.request.method == 'POST':
                self.additional_info = OfficeForm(
                    self.request.POST,
                    instance=self.asset.office_info,
                )
            else:
                self.additional_info = OfficeForm(
                    instance=self.asset.office_info,
                )
                fields = ['imei', 'purpose']
                for field in fields:
                    if field in self.asset_form.fields:
                        self.asset_form.fields[field].initial = (
                            getattr(self.asset.office_info, field, '')
                        )

    def get(self, *args, **kwargs):
        self.initialize_vars(*args, **kwargs)
        return super(EditDevice, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        post_data = self.request.POST
        self.initialize_vars(*args, **kwargs)
        self.part_form = MoveAssetPartForm(post_data or None)
        if 'move_parts' in post_data.keys():
            destination_asset = post_data.get('new_asset')
            if not destination_asset or not Asset.objects.filter(
                id=destination_asset,
            ):
                messages.error(
                    self.request,
                    _("Source device asset does not exist"),
                )
            elif kwargs.get('asset_id') == destination_asset:
                messages.error(
                    self.request,
                    _("You can't move parts to the same device"),
                )
            else:
                if post_data.getlist('part_ids'):
                    for part_id in post_data.getlist('part_ids'):
                        info_part = PartInfo.objects.get(asset=part_id)
                        info_part.device_id = destination_asset
                        info_part.save()
                    messages.success(
                        self.request, _("Selected parts was moved."),
                    )
                    self.part_form = MoveAssetPartForm()
                else:
                    messages.error(
                        self.request, _("Please select one or more parts."),
                    )
        elif 'asset' in post_data.keys():
            if all((
                self.asset_form.is_valid(),
                self.additional_info.is_valid(),
            )):
                modifier_profile = self.request.user.get_profile()
                self.asset = _update_asset(
                    modifier_profile, self.asset, self.asset_form.cleaned_data
                )
                self._update_additional_info(modifier_profile.user)
                self.asset.save(user=self.request.user)
                self.asset.licence_set.clear()
                for licence in self.asset_form.cleaned_data.get(
                    'licences', []
                ):
                    self.asset.licence_set.add(licence)
                self.asset.supports.clear()
                for support in self.asset_form.cleaned_data.get(
                    'supports', []
                ):
                    self.asset.supports.add(support)
                messages.success(self.request, _("Assets edited."))
                cat = self.request.path.split('/')[2]
                return HttpResponseRedirect(
                    '/assets/%s/edit/device/%s/' % (cat, self.asset.id)
                )
            else:
                messages.error(self.request, _("Please correct the errors."))
                messages.error(
                    self.request, self.asset_form.non_field_errors(),
                )
        return super(EditDevice, self).get(*args, **kwargs)

    def get_history_link(self):
        asset_id = self.asset.id
        url = reverse('device_history', kwargs={
            'asset_id': asset_id,
            'mode': self.mode,
        })
        return url


class SplitDeviceView(AssetsBase):
    template_name = 'assets/split_edit.html'
    sidebar_selected = ''

    def get_context_data(self, **kwargs):
        ret = super(SplitDeviceView, self).get_context_data(**kwargs)
        ret.update({
            'formset': self.asset_formset,
            'device': {
                'model': self.asset.model,
                'sn': self.asset.sn,
                'price': self.asset.price,
                'id': self.asset.id,
            },
        })
        return ret

    def get(self, *args, **kwargs):
        self.asset_id = self.kwargs.get('asset_id')
        self.asset = get_object_or_404(Asset, id=self.asset_id)
        if self.asset.has_parts():
            messages.error(self.request, _("This asset was splited."))
            return HttpResponseRedirect(
                reverse('device_edit', args=[self.asset.id, ])
            )
        if self.asset.device_info.ralph_device_id:
            initial = self.get_proposed_components()
        else:
            initial = []
            messages.error(
                self.request,
                _(
                    'Asset not linked with ralph device, proposed components '
                    'not available'
                ),
            )
        extra = 0 if initial else 1
        AssetFormSet = formset_factory(form=SplitDevice, extra=extra)
        self.asset_formset = AssetFormSet(initial=initial)
        return super(SplitDeviceView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.asset_id = self.kwargs.get('asset_id')
        self.asset = Asset.objects.get(id=self.asset_id)
        AssetFormSet = formset_factory(
            form=SplitDevice,
            extra=0,
        )
        self.asset_formset = AssetFormSet(self.request.POST)
        if self.asset_formset.is_valid():
            with transaction.commit_on_success():
                for instance in self.asset_formset.forms:
                    form = instance.save(commit=False)
                    model_name = instance['model_user'].value()
                    form.model = self.create_asset_model(model_name)
                    form.type = AssetType.data_center
                    form.part_info = self.create_part_info()
                    form.modified_by = self.request.user.get_profile()
                    form.save(user=self.request.user)
            messages.success(self.request, _("Changes saved."))
            return HttpResponseRedirect(self.request.get_full_path())
        self.valid_duplicates('sn')
        self.valid_duplicates('barcode')
        self.valid_total_price()
        messages.error(self.request, _("Please correct the errors."))
        return super(SplitDeviceView, self).get(*args, **kwargs)

    def valid_total_price(self):
        total_price = 0
        for instance in self.asset_formset.forms:
            total_price += float(instance['price'].value() or 0)
        valid_price = True if total_price == self.asset.price else False
        if not valid_price:
            messages.error(
                self.request,
                _(
                    "Total parts price must be equal to the asset price. "
                    "Total parts price (%s) != Asset "
                    "price (%s)" % (total_price, self.asset.price)
                )
            )
            return True

    def valid_duplicates(self, name):
        def get_duplicates(list):
            cnt = Counter(list)
            return [key for key in cnt.keys() if cnt[key] > 1]
        items = []
        for instance in self.asset_formset.forms:
            value = instance[name].value().strip()
            if value:
                items.append(value)
        duplicates_items = get_duplicates(items)
        for instance in self.asset_formset.forms:
            value = instance[name].value().strip()
            if value in duplicates_items:
                if name in instance.errors:
                    instance.errors[name].append(
                        'This %s is duplicated' % name
                    )
                else:
                    instance.errors[name] = ['This %s is duplicated' % name]
        if duplicates_items:
            messages.error(
                self.request,
                _("This %s is duplicated: (%s) " % (
                    name,
                    ', '.join(duplicates_items)
                )),
            )
            return True

    def create_asset_model(self, model_name):
        try:
            model = AssetModel.objects.get(name=model_name)
        except AssetModel.DoesNotExist:
            model = AssetModel()
            model.name = model_name
            model.save()
        return model

    def create_part_info(self):
        part_info = PartInfo()
        part_info.source_device = self.asset
        part_info.device = self.asset
        part_info.save(user=self.request.user)
        return part_info

    def get_proposed_components(self):
        try:
            components = list(get_device_components(
                ralph_device_id=self.asset.device_info.ralph_device_id
            ))
        except LookupError:
            components = []
        return components
