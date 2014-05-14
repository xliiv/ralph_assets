#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from lck.django.common.admin import ModelAdmin

from ralph_assets.models import (
    Asset,
    AssetCategory,
    AssetCategoryType,
    AssetManufacturer,
    AssetModel,
    AssetOwner,
    CoaOemOs,
    Licence,
    ReportOdtSource,
    Service,
    Transition,
    TransitionsHistory,
    get_edit_url,
    Warehouse,
)
from ralph_assets.models_util import ImportProblem
from ralph_assets import models_sam


admin.site.register(AssetOwner)
admin.site.register(Licence)
admin.site.register(models_sam.LicenceType)
admin.site.register(models_sam.SoftwareCategory)


class ImportProblemAdmin(ModelAdmin):
    change_form_template = "assets/import_problem_change_form.html"

    def change_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        problem = get_object_or_404(ImportProblem, pk=object_id)
        extra_context['resource_link'] = get_edit_url(problem.resource)
        return super(ImportProblemAdmin, self).change_view(
            request,
            object_id,
            extra_context,
        )

admin.site.register(ImportProblem, ImportProblemAdmin)


class WarehouseAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name',)
    search_fields = ('name',)


admin.site.register(Warehouse, WarehouseAdmin)


class AssetAdmin(ModelAdmin):
    fields = (
        'sn',
        'type',
        'model',
        'status',
        'warehouse',
        'source',
        'invoice_no',
        'order_no',
        'price',
        'support_price',
        'support_type',
        'support_period',
        'support_void_reporting',
        'provider',
        'remarks',
        'barcode',
        'request_date',
        'provider_order_date',
        'delivery_date',
        'invoice_date',
        'production_use_date',
        'production_year',
        'deleted',
    )
    search_fields = (
        'sn',
        'barcode',
        'device_info__ralph_device_id',
    )
    list_display = ('sn', 'model', 'type', 'barcode', 'status', 'deleted')
    list_filter = ('type',)

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Asset, AssetAdmin)


class AssetModelAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name', 'type', 'category')
    list_filter = ('type', 'category')
    search_fields = ('name',)


admin.site.register(AssetModel, AssetModelAdmin)


class AssetCategoryAdminForm(forms.ModelForm):
    def clean(self):
        data = self.cleaned_data
        parent = self.cleaned_data.get('parent')
        type = self.cleaned_data.get('type')
        if parent and parent.type != type:
            raise ValidationError(
                _("Parent type must be the same as selected type")
            )
        return data


class AssetCategoryAdmin(ModelAdmin):
    def name(self):
        type = AssetCategoryType.desc_from_id(self.type)
        if self.parent:
            name = '|-- ({}) {}'.format(type, self.name)
        else:
            name = '({}) {}'.format(type, self.name)
        return name
    form = AssetCategoryAdminForm
    save_on_top = True
    list_display = (name, 'parent', 'slug', 'type')
    list_filter = ('type',)
    search_fields = ('name',)
    prepopulated_fields = {"slug": ("type", "parent", "name")}


admin.site.register(AssetCategory, AssetCategoryAdmin)


class AssetManufacturerAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name',)
    search_fields = ('name',)


admin.site.register(AssetManufacturer, AssetManufacturerAdmin)


class ReportOdtSourceAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name', 'slug',)
    prepopulated_fields = {"slug": ("name",)}


admin.site.register(ReportOdtSource, ReportOdtSourceAdmin)


class TransitionAdmin(ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ('actions',)


admin.site.register(Transition, TransitionAdmin)


class TransitionsHistoryAdmin(ModelAdmin):
    list_display = ('transition', 'logged_user', 'affected_user', 'created')
    readonly_fields = (
        'transition', 'assets', 'logged_user', 'affected_user', 'report_file',
    )

    def has_add_permission(self, request):
        return False


admin.site.register(TransitionsHistory, TransitionsHistoryAdmin)


class CoaOemOsAdmin(ModelAdmin):
    list_display = ('name',)


admin.site.register(CoaOemOs, CoaOemOsAdmin)


class ServiceAdmin(ModelAdmin):
    list_display = ('name', 'profit_center', 'cost_center')


admin.site.register(Service, ServiceAdmin)
