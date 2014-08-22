# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.forms.models import formset_factory
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseRedirect

from ralph_assets import models as assets_models
from ralph_assets.forms import AttachmentForm
from ralph_assets.models_assets import Attachment
from ralph_assets.views.base import AssetsBase


logger = logging.getLogger(__name__)


class BaseAttachment(AssetsBase):

    def get_back_url(self, parent_name):
        mapping = {
            'asset': 'dc',
            'licence': 'licence_list',
            'support': 'support_list',
        }
        return reverse(mapping[parent_name])

    def set_mainmenu_selection(self, parent):
        if parent in set(['licence', 'support']):
            self.mainmenu_selected = parent + 's'

    def dispatch(self, request, parent, *args, **kwargs):
        if parent == 'license':
            parent = 'licence'
        self.Parent = getattr(assets_models, parent.title())
        self.parent_name = parent
        self.set_mainmenu_selection(parent)
        return super(BaseAttachment, self).dispatch(
            request, mode='', *args, **kwargs
        )


class AddAttachment(BaseAttachment):
    """
    Adding attachments to Parent.
    Parent can be one of these models: License, Asset, Support.
    """
    template_name = 'assets/add_attachment.html'

    def get_context_data(self, **kwargs):
        ret = super(AddAttachment, self).get_context_data(**kwargs)
        ret.update({
            'selected_parents': self.selected_parents,
            'formset': self.attachments_formset,
        })
        return ret

    def get(self, *args, **kwargs):
        url_parents_ids = self.request.GET.getlist('select')
        self.selected_parents = self.Parent.objects.filter(
            pk__in=url_parents_ids,
        )
        if not self.selected_parents.exists():
            messages.warning(self.request, _("Nothing to edit."))
            return HttpResponseRedirect(self.get_back_url(self.parent_name))

        AttachmentFormset = formset_factory(
            form=AttachmentForm, extra=1,
        )
        self.attachments_formset = AttachmentFormset()
        return super(AddAttachment, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        url_parents_ids = self.request.GET.getlist('select')
        self.selected_parents = self.Parent.objects.filter(
            id__in=url_parents_ids,
        )
        AttachmentFormset = formset_factory(
            form=AttachmentForm, extra=0,
        )
        self.attachments_formset = AttachmentFormset(
            self.request.POST, self.request.FILES,
        )
        if self.attachments_formset.is_valid():
            for form in self.attachments_formset.forms:
                attachment = form.save(commit=False)
                attachment.uploaded_by = self.request.user
                form.save()
                for parent in self.selected_parents:
                    parent.attachments.add(attachment)
            messages.success(self.request, _("Changes saved."))
            return HttpResponseRedirect(self.get_back_url(self.parent_name))
        messages.error(self.request, _("Please correct the errors."))
        return super(AddAttachment, self).get(*args, **kwargs)


class DeleteAttachment(BaseAttachment):

    def post(self, *args, **kwargs):
        parent_id = self.request.POST.get('parent_id')
        attachment_id = self.request.POST.get('attachment_id')
        try:
            attachment = Attachment.objects.get(pk=attachment_id)
        except Attachment.DoesNotExist:
            messages.error(
                self.request, _("Selected attachment doesn't exists.")
            )
            return HttpResponseRedirect(self.get_back_url(self.parent_name))
        try:
            self.parent = self.Parent.objects.get(pk=parent_id)
        except self.Parent.DoesNotExist:
            messages.error(
                self.request,
                _("Selected {} doesn't exists.").format(self.parent_name),
            )
            return HttpResponseRedirect(self.parent.url)
        delete_type = self.request.POST.get('delete_type')
        if delete_type == 'from_one':
            if attachment in self.parent.attachments.all():
                self.parent.attachments.remove(attachment)
                self.parent.save()
                msg = _("Attachment was deleted")
            else:
                msg = _(
                    "{} does not include the attachment any more".format(
                        self.parent_name.title()
                    )
                )
            messages.success(self.request, _(msg))

        elif delete_type == 'from_all':
            Attachment.objects.filter(id=attachment.id).delete()
            messages.success(self.request, _("Attachments was deleted"))
        else:
            msg = "Unknown delete type: {}".format(delete_type)
            messages.error(self.request, _(msg))
        return HttpResponseRedirect(self.parent.url)
