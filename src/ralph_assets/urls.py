# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.conf.urls.defaults import include, patterns, url
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView
from tastypie.api import Api

from ralph_assets.api import (
    AssetManufacturerResource,
    AssetModelResource,
    AssetOwnerResource,
    AssetsResource,
    LicenceResource,
    LicenceTypeResource,
    ServiceResource,
    SoftwareCategoryResource,
    UserAssignmentsResource,
    UserResource,
    WarehouseResource,
)
from ralph_assets.views import (
    AddAttachment,
    AddDevice,
    AddPart,
    AssetSearch,
    BulkEdit,
    CategoryDependencyView,
    ModelDependencyView,
    DeleteAsset,
    DeleteAttachment,
    DeleteLicence,
    EditDevice,
    EditPart,
    EditUser,
    HistoryAsset,
    SplitDeviceView,
    UserDetails,
    UserList,
)
from ralph_assets.views_import import XlsUploadView
from ralph_assets.views_sam import (
    AddLicence,
    EditLicence,
    HistoryLicence,
    LicenceList,
    SoftwareCategoryList,
)
from ralph_assets.views_invoice_report import (
    AssetInvoiceReport,
    LicenceInvoiceReport,
)
from ralph_assets.forms_import import XLS_UPLOAD_FORMS
from ralph_assets.views_transition import (
    TransitionView,
    TransitionHistoryFileHandler,
)

v09_api = Api(api_name='v0.9')
for r in (
    AssetManufacturerResource,
    AssetModelResource,
    AssetOwnerResource,
    AssetsResource,
    LicenceResource,
    LicenceTypeResource,
    ServiceResource,
    SoftwareCategoryResource,
    UserAssignmentsResource,
    UserResource,
    WarehouseResource,
):
    v09_api.register(r())


urlpatterns = patterns(
    '',
    url(r'^api/', include(v09_api.urls)),
    url(r'^$',
        RedirectView.as_view(url='/assets/dc/search'),
        name='dc'),
    url(r'dc/$', RedirectView.as_view(url='/assets/dc/search'),
        name='dc'),
    url(r'back_office/$',
        RedirectView.as_view(url='/assets/back_office/search'),
        name='dc'),

    url(r'(?P<mode>(back_office|dc))/search',
        login_required(AssetSearch.as_view()),
        name='asset_search'),
    url(r'(?P<mode>(back_office|dc))/add/device/',
        login_required(AddDevice.as_view()),
        name='add_device'),
    url(r'(?P<mode>(back_office|dc))/add/part/',
        login_required(AddPart.as_view()),
        name='add_part'),
    url(r'(?P<mode>(back_office|dc))/edit/device/(?P<asset_id>[0-9]+)/$',
        login_required(EditDevice.as_view()),
        name='device_edit'),
    url(r'(?P<mode>(back_office|dc))/edit/part/(?P<asset_id>[0-9]+)/$',
        login_required(EditPart.as_view()),
        name='part_edit'),
    url(r'ajax/dependencies/category/$',
        CategoryDependencyView.as_view(),
        name='category_dependency_view'),
    url(r'ajax/dependencies/model/$',
        ModelDependencyView.as_view(),
        name='model_dependency_view'),
    url(r'(?P<mode>(back_office|dc))/history/device/(?P<asset_id>[0-9]+)/$',
        login_required(HistoryAsset.as_view()),
        name='device_history'),
    url(r'(?P<mode>(back_office|dc))/history/part/(?P<asset_id>[0-9]+)/$',
        login_required(HistoryAsset.as_view()),
        name='part_history'),
    url(r'(?P<mode>(back_office|dc))/bulkedit/$',
        login_required(BulkEdit.as_view()),
        name='dc'),
    url(r'(?P<mode>(back_office|dc))/delete/asset/$',
        login_required(DeleteAsset.as_view()),
        name='dc'),
    url(r'(?P<mode>(back_office|dc))/split/asset/(?P<asset_id>[0-9]+)/$',
        login_required(SplitDeviceView.as_view()),
        name='device_split'),
    url(
        r'(?P<mode>(back_office|dc))/invoice_report/$',
        login_required(AssetInvoiceReport.as_view()),
        name='assets_invoice_report',
    ),
    url(
        r'sam/licences/invoice_report/$',
        login_required(LicenceInvoiceReport.as_view()),
        name='sam_invoice_report',
    ),
    url(
        r'(?P<mode>(back_office|dc))/transition/$',
        login_required(TransitionView.as_view()),
        name='transition',
    ),
    url(
        r'(?P<mode>(back_office|dc))/add_attachment/(?P<parent>(asset|license))/$',  # noqa
        login_required(AddAttachment.as_view()),
        name='add_attachment'
    ),
    url(
        r'xls/$',
        login_required(XlsUploadView.as_view(XLS_UPLOAD_FORMS)),
        name='xls_upload',
    ),
    url(
        r'sam/categories/$',
        login_required(SoftwareCategoryList.as_view()),
        name='software_categories',
    ),
    url(
        r'sam/licences/$',
        login_required(LicenceList.as_view()),
        name='licence_list',
    ),
    url(
        r'sam/licences/$',
        login_required(LicenceList.as_view()),
        name='licence_list',
    ),
    url(
        r'sam/add_licence/$',
        login_required(AddLicence.as_view()),
        name='add_licence',
    ),
    url(
        r'(?P<mode>(back_office|dc))/sam/edit_licence/(?P<licence_id>[0-9]+)$',
        login_required(EditLicence.as_view()),
        name='edit_licence',
    ),
    url(
        r'(?P<mode>(back_office|dc))/sam/delete/$',
        login_required(DeleteLicence.as_view()),
        name='delete_licence',
    ),
    url(
        r'(?P<mode>(back_office|dc))/delete/(?P<parent>(asset|license))/attachment/$',  # noqa
        login_required(DeleteAttachment.as_view()),
        name='delete_attachment',
    ),
    url(
        r'users/$',
        login_required(UserList.as_view()),
        name='user_list',
    ),
    url(
        r'user/relations/(?P<username>[^\/]+)/$',
        login_required(EditUser.as_view()),
        name='edit_user_relations',
    ),
    url(
        r'user/details/(?P<username>[^\/]+)/$',
        login_required(UserDetails.as_view()),
        name='user_view',
    ),
    url(
        r'(?P<mode>(back_office|dc))/history/licence/(?P<licence_id>[0-9]+)/$',
        login_required(HistoryLicence.as_view()),
        name='licence_history',
    ),
    url(
        r'transition-history-file/(?P<history_id>[0-9]+)$',
        login_required(TransitionHistoryFileHandler.as_view()),
        name='transition_history_file',
    ),
)
