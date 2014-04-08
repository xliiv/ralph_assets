"""Utilities for using forms to upload tabular data."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import csv
import xlrd
import itertools as it

from django import forms
from django.db.models.fields import NOT_PROVIDED
from django.contrib.contenttypes.models import ContentType
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

from ralph_assets.models_assets import AssetType


def get_amendment_model(mode):
    return {
        'dc': ('device_info', 'ralph_assets.deviceinfo'),
        'back_office': ('office_info', 'ralph_assets.officeinfo'),
    }[mode]


class DataUploadField(forms.FileField):
    """A field that gets the uploaded XLS or CSV data and returns data
    prepared for add/update."""

    def _process_xls(self, file_):
        book = xlrd.open_workbook(
            filename=file_.name,
            file_contents=file_.read(),
        )
        names_per_sheet = {}
        update_per_sheet = {}
        add_per_sheet = {}
        for sheet_name, sheet in (
            (sheet_name, book.sheet_by_name(sheet_name)) for
            sheet_name in book.sheet_names()
        ):
            if not sheet.nrows:
                continue
            name_row = sheet.row(0)
            update = name_row[0].value == 'id'
            if update:
                name_row = name_row[1:]
            names_per_sheet[sheet_name] = col_names = [
                cell.value for cell in name_row
            ]
            update_per_sheet[sheet_name] = {}
            add_per_sheet[sheet_name] = []
            if update:
                for row in (sheet.row(i) for i in xrange(1, sheet.nrows)):
                    asset_id = int(row[0].value)
                    update_per_sheet[sheet_name][asset_id] = {}
                    for key, cell in it.izip(col_names, row[1:]):
                        update_per_sheet[sheet_name][asset_id][slugify(key)] =\
                            cell.value
            else:
                for row in (sheet.row(i) for i in xrange(1, sheet.nrows)):
                    asset_data = {}
                    add_per_sheet[sheet_name].append(asset_data)
                    for key, cell in it.izip(col_names, row):
                        asset_data[slugify(key)] = cell.value

        return names_per_sheet, update_per_sheet, add_per_sheet

    def _process_csv(self, file_):
        def unicode_rows(reader):
            for row in reader:
                try:
                    yield [cell.decode('utf-8') for cell in row]
                except UnicodeDecodeError:
                    raise forms.ValidationError(
                        'Problems with character encoding. Use UTF-8'
                    )
        reader = unicode_rows(csv.reader(file_))
        update_per_sheet = {'csv': {}}
        add_per_sheet = {'csv': []}
        name_row = next(reader)
        update = name_row[0] == 'id'
        if update:
            name_row = name_row[1:]
            for row in reader:
                asset_id = int(row[0])
                update_per_sheet['csv'].setdefault(asset_id, {})
                for key, value in it.izip(name_row, row[1:]):
                    update_per_sheet['csv'][asset_id][key] = value
        else:
            for row in reader:
                asset_data = {}
                add_per_sheet['csv'].append(asset_data)
                for key, value in it.izip(name_row, row[:]):
                    asset_data[key] = value
        names_per_sheet = {'csv': name_row}
        return names_per_sheet, update_per_sheet, add_per_sheet

    def to_python(self, value):
        file_ = super(DataUploadField, self).to_python(value)
        if file_ is None:
            raise forms.ValidationError(
                _('Please provide a file for import.')
            )
        try:
            filetype = {
                'application/vnd.openxmlformats-officedocument.'
                'spreadsheetml.sheet': 'xls',
                'text/csv': 'csv',
                'application/csv': 'csv',
                'application/vnd.ms-excel': 'csv',  # Browsers Y U NO RFC 4180?
            }[file_.content_type]
        except KeyError:
            raise forms.ValidationError(
                'Unsupported file type. Use CSV of Excel.'
            )
        return (
            self._process_xls if filetype == 'xls' else self._process_csv
        )(file_)


class ModelChoiceField(forms.ChoiceField):

    def __init__(self, *args, **kwargs):
        kwargs['choices'] = [
            ('ralph_assets.asset', 'Asset'),
            ('ralph_assets.licence', 'Licence'),
        ]
        super(ModelChoiceField, self).__init__(*args, **kwargs)


class ColumnChoiceField(forms.ChoiceField):
    """A field that allows to choose a field from a model."""

    def __init__(self, model, mode, *args, **kwargs):
        kwargs['choices'] = [('', '-----')]
        Model = get_model_by_name(model)
        kwargs['choices'] += [
            (field.name, unicode(field.verbose_name))
            for field in it.chain(Model._meta.fields, Model._meta.many_to_many)
            if field.name != 'id'
        ]
        if model == 'ralph_assets.asset':
            amd_field, amd_model = get_amendment_model(mode)
            AmdModel = get_model_by_name(amd_model)
            kwargs['choices'] += [
                (
                    '.'.join([amd_field, field.name]),
                    unicode(field.verbose_name)
                )
                for field in AmdModel._meta.fields if field.name != 'id'
            ]
        kwargs['required'] = False
        super(ColumnChoiceField, self).__init__(*args, **kwargs)


class XlsUploadForm(forms.Form):
    """The first step for uploading the XLS file for asset bulk update."""
    model = ModelChoiceField()
    file = DataUploadField()


class XlsColumnChoiceForm(forms.Form):
    """The column choice. This form will be filled on the fly."""

    def clean(self, *args, **kwargs):
        result = super(XlsColumnChoiceForm, self).clean(*args, **kwargs)
        if self.update:
            return result
        matched = set(result.values()) - {''}
        Model = get_model_by_name(self.model_reflected)
        required = {
            field.name
            for field in Model._meta.fields
            if not (
                field.blank or
                field.default != NOT_PROVIDED or
                field.choices == AssetType() or
                field.name in {'rght', 'tree_id', 'lft', 'level'}
            )
        }
        missing = required - matched
        if missing:
            raise forms.ValidationError(
                _('Missing fields: %s' % ', '.join(missing))
            )
        return result


class XlsConfirmForm(forms.Form):
    """The confirmation of XLS submission. A form with a button only."""


XLS_UPLOAD_FORMS = [
    ('upload', XlsUploadForm),
    ('column_choice', XlsColumnChoiceForm),
    ('confirm', XlsConfirmForm),
]


def get_model_by_name(name):
    return ContentType.objects.get_by_natural_key(
        *name.split('.')
    ).model_class()
