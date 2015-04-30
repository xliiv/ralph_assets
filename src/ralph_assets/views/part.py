# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from bob.data_table import DataTableColumn
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from ralph_assets.forms_part import AddPartForm, EditPartForm, PartSearchForm
from ralph_assets.models import Part, PartModelType
from ralph_assets.views.base import (
    AssetsBase,
    HardwareModeMixin,
    SubmoduleModeMixin,
)
from ralph_assets.views.search import GenericSearch


class AddPart(HardwareModeMixin, SubmoduleModeMixin, AssetsBase):

    active_sidebar_item = 'add part'
    template_name = 'assets/add_part.html'

    def get_context_data(self, **kwargs):
        ret = super(AddPart, self).get_context_data(**kwargs)
        ret.update({
            'form': self.form,
        })
        return ret

    def get(self, *args, **kwargs):
        self.form = AddPartForm(mode=self.mode)
        return super(AddPart, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.form = AddPartForm(data=self.request.POST, mode=self.mode)
        if self.form.is_valid():
            serial_numbers = self.form.cleaned_data['sn']
            part_data = self.form.cleaned_data
            del part_data['sn']
            for serial_number in serial_numbers:
                Part.objects.create(
                    sn=serial_number,
                    **part_data
                )
            messages.success(self.request, _("Parts saved."))
            return HttpResponseRedirect(
                reverse('part_search', kwargs={'mode': self.mode})
            )
        messages.error(self.request, _("Please correct the errors."))
        return super(AddPart, self).get(*args, **kwargs)


class EditPart(HardwareModeMixin, SubmoduleModeMixin, AssetsBase):

    template_name = 'assets/edit_part.html'

    def get_context_data(self, **kwargs):
        ret = super(EditPart, self).get_context_data(**kwargs)
        ret.update({
            'form': self.form,
        })
        return ret

    def get(self, *args, **kwargs):
        self.part = get_object_or_404(
            Part,
            id=kwargs.get('part_id')
        )
        self.form = EditPartForm(instance=self.part, mode=self.mode)
        return super(EditPart, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.part = get_object_or_404(
            Part,
            id=kwargs.get('part_id')
        )
        self.form = EditPartForm(
            data=self.request.POST,
            instance=self.part,
            mode=self.mode,
        )
        if self.form.is_valid():
            self.form.save()
            messages.success(self.request, _("Changes were saved."))
            return HttpResponseRedirect(
                reverse(
                    'part_edit',
                    kwargs={
                        'mode': self.mode,
                        'part_id': self.part.id,
                    },
                )
            )
        messages.error(self.request, _("Please correct the errors."))
        return super(EditPart, self).get(*args, **kwargs)


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
