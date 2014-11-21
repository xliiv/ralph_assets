# -*- coding: utf-8 -*-


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from ajax_select.fields import AutoCompleteSelectField
from dj.choices import Country
from django import forms
from django.utils.translation import ugettext_lazy as _

from ralph_assets.forms import LOOKUPS, RALPH_DATE_FORMAT_LIST
from ralph.ui.widgets import DateWidget


class TransitionForm(forms.Form):
    user = AutoCompleteSelectField(
        LOOKUPS['asset_user'],
        required=True,
    )
    warehouse = AutoCompleteSelectField(
        LOOKUPS['asset_warehouse'],
        required=True,
    )
    loan_end_date = forms.DateField(
        required=True, widget=DateWidget(attrs={
            'class': 'end-date-field ',
            'placeholder': _('End YYYY-MM-DD'),
            'data-collapsed': True,
        }),
        label=_('Loan end date'),
        input_formats=RALPH_DATE_FORMAT_LIST,
    )
    country = forms.ChoiceField(
        choices=[('', '----')] + Country(),
        label=_('Country'),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        self.transition = kwargs.pop('transition', None)
        if not self.transition:
            raise ValueError('Please specified transition.')
        super(TransitionForm, self).__init__(*args, **kwargs)
        if self.transition.required_report and self.transition.odt_templates:
            self.fields['document_language'] = forms.ChoiceField(
                choices=[('', '----')] + [
                    (t.id, t.get_language_display())
                    for t in self.transition.odt_templates
                ],
                label=_('Document language'),
                required=True,
            )
            if len(self.transition.odt_templates) == 1:
                self.fields['document_language'].widget = \
                    forms.HiddenInput(attrs={
                        'value': self.transition.odt_templates[0].id
                    })

    def clean(self):
        if (
            not self.transition.odt_templates
            and self.transition.required_report
        ):
            raise forms.ValidationError(_('Odt template does not exist!'))
        return super(TransitionForm, self).clean()
