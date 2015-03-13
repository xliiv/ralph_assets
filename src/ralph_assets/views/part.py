# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

from bob.data_table import DataTableColumn
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from ralph_assets.forms import (
    AddPartForm,
    BasePartForm,
    EditPartForm,
    OfficeForm,
)
from ralph_assets.forms_part import PartSearchForm
from ralph_assets.models import Asset
from ralph_assets.models_parts import Part, PartModelType
from ralph_assets.views.base import (
    AssetsBase,
    HardwareModeMixin,
    SubmoduleModeMixin,
    get_return_link,
)
from ralph_assets.views.search import GenericSearch
from ralph_assets.views.utils import (
    _create_part,
    _update_asset,
    _update_office_info,
    _move_data,
    _update_part_info,
)

logger = logging.getLogger(__name__)


class AddPart(HardwareModeMixin, SubmoduleModeMixin, AssetsBase):
    active_sidebar_item = 'add part'
    template_name = 'assets/add_part.html'

    def get_context_data(self, **kwargs):
        ret = super(AddPart, self).get_context_data(**kwargs)
        ret.update({
            'asset_form': self.asset_form,
            'part_info_form': self.part_info_form,
            'form_id': 'add_part_form',
            'edit_mode': False,
        })
        return ret

    def initialize_vars(self):
        self.device_id = None

    def get(self, *args, **kwargs):
        self.initialize_vars()
        mode = self.mode
        self.asset_form = AddPartForm(mode=mode)
        self.device_id = self.request.GET.get('device')
        part_form_initial = {}
        if self.device_id:
            part_form_initial['device'] = self.device_id
        self.part_info_form = BasePartForm(
            initial=part_form_initial, mode=mode)
        return super(AddPart, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.initialize_vars()
        mode = self.mode
        self.asset_form = AddPartForm(self.request.POST, mode=mode)
        self.part_info_form = BasePartForm(self.request.POST, mode=mode)
        if self.asset_form.is_valid() and self.part_info_form.is_valid():
            creator_profile = self.request.user.get_profile()
            asset_data = self.asset_form.cleaned_data
            for f_name in {
                "barcode", "category", "company", "cost_center", "department",
                "employee_id", "imei", "licences", "manager", "profit_center",
                "supports", "segment",
            }:
                if f_name in asset_data:
                    del asset_data[f_name]
            asset_data['barcode'] = None
            serial_numbers = self.asset_form.cleaned_data['sn']
            del asset_data['sn']
            if 'imei' in asset_data:
                del asset_data['imei']
            ids = []
            for sn in serial_numbers:
                ids.append(
                    _create_part(
                        creator_profile, asset_data,
                        self.part_info_form.cleaned_data, sn
                    )
                )
            messages.success(self.request, _("Assets saved."))
            cat = self.request.path.split('/')[2]
            if len(ids) == 1:
                return HttpResponseRedirect(
                    '/assets/%s/edit/part/%s/' % (cat, ids[0])
                )
            else:
                return HttpResponseRedirect(
                    '/assets/%s/bulkedit/?select=%s' % (
                        cat, '&select='.join(["%s" % id for id in ids]))
                )
            return HttpResponseRedirect(get_return_link(self.mode))
        else:
            messages.error(self.request, _("Please correct the errors."))
        return super(AddPart, self).get(*args, **kwargs)


class EditPart(HardwareModeMixin, SubmoduleModeMixin, AssetsBase):
    detect_changes = True
    template_name = 'assets/edit_part.html'

    def initialize_vars(self):
        self.office_info_form = None

    def get_context_data(self, **kwargs):
        context = super(EditPart, self).get_context_data(**kwargs)
        context.update({
            'asset_form': self.asset_form,
            'office_info_form': self.office_info_form,
            'part_info_form': self.part_info_form,
            'form_id': 'edit_part_form',
            'edit_mode': True,
            'parent_link': self.get_parent_link(),
            'asset': self.asset,
        })
        return context

    def get(self, *args, **kwargs):
        self.initialize_vars()
        self.asset = get_object_or_404(
            Asset.admin_objects,
            id=kwargs.get('asset_id')
        )
        if self.asset.device_info:  # it isn't part asset
            raise Http404()
        self.asset_form = EditPartForm(instance=self.asset, mode=self.mode)
        self.write_office_info2asset_form()
        self.part_info_form = BasePartForm(
            instance=self.asset.part_info, mode=self.mode,
        )
        return super(EditPart, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.asset = get_object_or_404(
            Asset.admin_objects,
            id=kwargs.get('asset_id')
        )
        mode = self.mode
        self.asset_form = EditPartForm(
            self.request.POST,
            instance=self.asset,
            mode=mode
        )
        self.office_info_form = OfficeForm(
            self.request.POST, self.request.FILES)
        self.part_info_form = BasePartForm(self.request.POST, mode=mode)
        if all((
            self.asset_form.is_valid(),
            self.office_info_form.is_valid(),
            self.part_info_form.is_valid()
        )):
            modifier_profile = self.request.user.get_profile()
            self.asset = _update_asset(
                modifier_profile, self.asset,
                self.asset_form.cleaned_data
            )
            new_src, new_dst = _move_data(
                self.asset_form.cleaned_data,
                self.office_info_form.cleaned_data,
                ['imei'],
            )
            self.asset_form.cleaned_data = new_src
            self.office_info_form.cleaned_data = new_dst
            self.asset = _update_office_info(
                modifier_profile.user, self.asset,
                self.office_info_form.cleaned_data
            )
            self.asset = _update_part_info(
                modifier_profile.user, self.asset,
                self.part_info_form.cleaned_data
            )
            self.asset.save(user=self.request.user)
            self.asset.supports.clear()
            for support in self.asset_form.cleaned_data.get(
                'supports', []
            ):
                self.asset.supports.add(support)
            messages.success(self.request, _("Part of asset was edited."))
            cat = self.request.path.split('/')[2]
            return HttpResponseRedirect(
                '/assets/%s/edit/part/%s/' % (cat, self.asset.id)
            )
        else:
            messages.error(self.request, _("Please correct the errors."))
            messages.error(self.request, self.asset_form.non_field_errors())
        return super(EditPart, self).get(*args, **kwargs)

    def get_parent_link(self):
        asset = self.asset.part_info.source_device
        if asset:
            return reverse('device_edit', kwargs={
                'asset_id': asset.id,
                'mode': self.mode,
            })


class PartLinkColumn(DataTableColumn):
    """
    A column that links to the edit page of a part simply displaying
    'Part' in a grid
    """
    def render_cell_content(self, resource):
        return '<a href="{url}">{part}</a>'.format(
            url=resource.url,
            part=unicode(_('Part')),
        )


class ChoiceColumn(DataTableColumn):
    """
    DataTableColumn with proper rendering of Choices items.
    """
    def __init__(self, choices, *args, **kwargs):
        self.choices = choices
        super(ChoiceColumn, self).__init__(*args, **kwargs)

    def render_cell_content(self, resource):
        if self.field:
            for part in self.field.split('__'):
                try:
                    resource = getattr(resource, part)
                except AttributeError:
                    return ''
            return unicode(self.choices.name_from_id(resource))
        else:
            raise NotImplementedError(
                "Either implement 'render_cell_content' method or set 'field' "
                "on this column"
            )


class PartList(HardwareModeMixin, SubmoduleModeMixin, GenericSearch):
    """List of parts."""

    Form = PartSearchForm
    Model = Part

    submodule_name = 'hardware'
    active_sidebar_item = 'search parts'
    template_name = 'assets/part_list.html'
    csv_file_name = 'parts'
    sort_variable_name = 'sort'
    columns = [
        PartLinkColumn(
            _('Type'),
            bob_tag=True,
        ),
        ChoiceColumn(
            PartModelType,
            _('Model type'),
            bob_tag=True,
            field='model__model_type',
            sort_expression='model__model_type',
        ),
        DataTableColumn(
            _('Model'),
            bob_tag=True,
            field='model__name',
            sort_expression='model__name',
        ),
        DataTableColumn(
            _('SN'),
            bob_tag=True,
            field='sn',
            sort_expression='sn',
        ),
        DataTableColumn(
            _('Order no.'),
            bob_tag=True,
            field='order_no',
            sort_expression='order_no',
        ),
        DataTableColumn(
            _('Price'),
            bob_tag=True,
            field='price',
            sort_expression='price',
        ),
        DataTableColumn(
            _('Service / Environment'),
            bob_tag=True,
            field='service_environment',
        ),
    ]

    def set_mode(self, mode):
        self.header = 'Search {} Parts'.format(
            {
                'dc': 'DC',
                'back_office': 'BO',
            }[mode]
        )
        super(PartList, self).set_mode(mode)

    def get_context_data(self, *args, **kwargs):
        ret = super(PartList, self).get_context_data(*args, **kwargs)
        ret.update({
            'header': self.header,
            'bo_mode_url': reverse(
                'part_search',
                kwargs={'mode': 'back_office'}
            ),
            'dc_mode_url': reverse('part_search', kwargs={'mode': 'dc'}),
        })
        return ret

    def _get_objects(self):
        if self.mode == 'dc':
            return self.Model.objects_dc
        else:
            return self.Model.objects_bo
