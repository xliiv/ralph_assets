# -*- coding: utf-8 -*-

from ralph_assets.forms_support import (
    AddSupportForm,
    EditSupportForm,
    SupportSearchForm,
)
from ralph_assets.models_support import Support
from ralph_assets.views.base import AssetsBase, get_return_link
from ralph_assets.views.search import GenericSearch
from ralph_assets.views.asset import HISTORY_PAGE_SIZE, MAX_PAGE_SIZE
from bob.data_table import DataTableColumn
from ralph_assets.models_assets import (
    MODE2ASSET_TYPE,
    Asset,
    ASSET_TYPE2MODE,
)
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from ralph_assets.views.sam import CheckBoxColumn
from ralph_assets.models_history import SupportHistoryChange


class SupportLinkColumn(DataTableColumn):
    """A column that links to the edit page of a support simply displaying
    'Support' in a grid"""
    def render_cell_content(self, resource):
        return '<a href="{url}">{support}</a>'.format(
            url=resource.url,
            support=unicode(_('Support')),
        )


class SupportView(AssetsBase):
    """Base view that displays support form."""

    template_name = 'assets/add_support.html'
    sidebar_selected = None

    def _get_form(self, data=None, **kwargs):
        self.form = self.form_class(
            mode=self.mode, data=data, **kwargs
        )

    def get_context_data(self, **kwargs):
        ret = super(SupportView, self).get_context_data(**kwargs)
        ret.update({
            'form': self.form,
            'form_id': 'add_support_form',
            'edit_mode': False,
            'caption': self.caption,
            'support': getattr(self, 'support', None),
            'mode': self.mode,
        })
        return ret

    def _save(self, request, *args, **kwargs):
        try:
            support = self.form.save(commit=False)
            if support.asset_type is None:
                support.asset_type = MODE2ASSET_TYPE[self.mode]
            support.save(user=self.request.user)
            self.form.save_m2m()
            messages.success(self.request, self.message)
            return HttpResponseRedirect(support.url)
        except ValueError:
            return super(SupportView, self).get(request, *args, **kwargs)


class AddSupportView(SupportView):
    """Add a new support"""

    caption = _('Add Support')
    mainmenu_selected = 'supports'
    message = _('Support added')

    def __init__(self, *args, **kwargs):
        self.form_class = AddSupportForm
        super(AddSupportView, self).__init__(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        self._get_form()
        return super(AddSupportView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self._get_form(request.POST)
        if self.form.is_valid():
            self.form.instance.pk = None
            support = self.form.save(commit=False)
            if support.asset_type is None:
                support.asset_type = MODE2ASSET_TYPE[self.mode]
            support.save(user=self.request.user)
            messages.success(self.request, self.message)
            return HttpResponseRedirect(reverse('support_list'))
        else:
            return super(AddSupportView, self).get(request, *args, **kwargs)


class SupportList(GenericSearch):
    """The support list."""

    mainmenu_selected = 'supports'
    Form = SupportSearchForm
    Model = Support

    columns = [
        CheckBoxColumn(
            _('Dropdown'),
            selectable=True,
            bob_tag=True,
        ),
        SupportLinkColumn(
            _('Type'),
            bob_tag=True,
        ),
        DataTableColumn(
            _('Contract id'),
            bob_tag=True,
            field='contract_id',
            sort_expression='contract_id',
        ),
        DataTableColumn(
            _('Name'),
            bob_tag=True,
            field='name',
            sort_expression='name',
        ),
        DataTableColumn(
            _('Date from'),
            bob_tag=True,
            field='date_from',
            sort_expression='date_from',
        ),
        DataTableColumn(
            _('Date to'),
            bob_tag=True,
            field='date_to',
            sort_expression='date_to',
        ),
        DataTableColumn(
            _('Price'),
            bob_tag=True,
            field='price',
            sort_expression='price',
        ),
    ]

    def get_context_data(self, *args, **kwargs):
        data = super(SupportList, self).get_context_data(
            *args, **kwargs
        )
        if self.mode:
            data['supports'] = Support.objects.filter(
                asset_type=MODE2ASSET_TYPE[self.mode],
            )
        else:
            data['supports'] = Support.objects.all()
        return data


class EditSupportView(SupportView):
    """Edit support"""
    detect_changes = True

    def __init__(self, *args, **kwargs):
        self.form_class = EditSupportForm
        super(EditSupportView, self).__init__(*args, **kwargs)

    caption = _('Edit Support')
    message = _('Support changed')
    Form = EditSupportForm

    def get(self, request, support_id, *args, **kwargs):
        self.support = Support.objects.get(pk=support_id)
        self._get_form(instance=self.support)
        return super(EditSupportView, self).get(request, *args, **kwargs)

    def post(self, request, support_id, *args, **kwargs):
        self.support = Support.objects.get(pk=support_id)
        self._get_form(request.POST, instance=self.support)
        return self._save(request, *args, **kwargs)


class DeleteSupportView(AssetsBase):
    """Delete a support."""

    def post(self, *args, **kwargs):
        record_id = self.request.POST.get('record_id')
        try:
            support = Support.objects.get(pk=record_id)
        except Asset.DoesNotExist:
            messages.error(self.request, _("Selected asset doesn't exists."))
            return HttpResponseRedirect(get_return_link(self.mode))
        self.back_to = reverse(
            'support_list',
            kwargs={'mode': ASSET_TYPE2MODE[support.asset_type]},
        )
        support.delete(user=self.request.user)
        return HttpResponseRedirect(self.back_to)


class HistorySupport(AssetsBase):
    template_name = 'assets/history.html'

    def get_context_data(self, **kwargs):
        query_variable_name = 'history_page'
        ret = super(HistorySupport, self).get_context_data(**kwargs)
        support_id = kwargs.get('support_id')
        support = Support.objects.get(id=support_id)
        history = SupportHistoryChange.objects.filter(
            support=support,
        ).order_by('-date')
        try:
            page = int(self.request.GET.get(query_variable_name, 1))
        except ValueError:
            page = 1
        if page == 0:
            page = 1
            page_size = MAX_PAGE_SIZE
        else:
            page_size = HISTORY_PAGE_SIZE
        history_page = Paginator(history, page_size).page(page)
        ret.update({
            'history': history,
            'history_page': history_page,
            'show_status_button': False,
            'query_variable_name': query_variable_name,
            'object': support,
            'object_url': reverse(
                'edit_support',
                kwargs={
                    'support_id': support.id,
                    'mode': self.mode,
                }
            ),
            'title': _('History support'),
        })
        return ret
