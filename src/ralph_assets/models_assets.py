#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Asset management models."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime
import logging
import os

from dateutil.relativedelta import relativedelta

from dj.choices import Country
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from lck.django.choices import Choices
from lck.django.common import nested_commit_on_success
from lck.django.common.models import (
    EditorTrackable,
    Named,
    SoftDeletable,
    TimeTrackable,
    WithConcurrentGetOrCreate,
    ViewableSoftDeletableManager,
)

from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import post_save, post_delete, pre_save
from django.db.utils import DatabaseError
from django.dispatch import receiver
from django.template import Context, Template
from django.utils.translation import ugettext_lazy as _

from ralph.business.models import Venture
from ralph.discovery.models_device import (
    Device,
    DeviceEnvironment,
    DeviceType,
    ServiceCatalog,
)
from ralph.discovery.models_util import SavingUser
from ralph_assets.history.models import HistoryMixin
from ralph_assets.history.utils import field_changes
from ralph.util.models import SyncFieldMixin
from ralph_assets.models_util import (
    Regionalized,
    RegionalizedDBManager,
    WithForm,
)
from ralph_assets.utils import iso2_to_iso3


logger = logging.getLogger(__name__)

SAVE_PRIORITY = 0
ASSET_HOSTNAME_TEMPLATE = getattr(settings, 'ASSET_HOSTNAME_TEMPLATE', None)
if not ASSET_HOSTNAME_TEMPLATE:
    raise ImproperlyConfigured('"ASSET_HOSTNAME_TEMPLATE" must be specified.')
HOSTNAME_FIELD_HELP_TIP = getattr(settings, 'HOSTNAME_FIELD_HELP_TIP', '')

REPORT_LANGUAGES = getattr(settings, 'REPORT_LANGUAGES', None)

INVALID_DATA_CENTER = 1
INVALID_SERVER_ROOM = 2
INVALID_ORIENTATION = 3
INVALID_POSITION = 4
REQUIRED_SLOT_NUMBER = 5


def _replace_empty_with_none(obj, fields):
    # XXX: replace '' with None, because null=True on model doesn't work
    for field in fields:
        value = getattr(obj, field, None)
        if value == '':
            setattr(obj, field, None)


def get_user_iso3_country_name(user):
    """
    :param user: instance of django.contrib.auth.models.User which has profile
        with country attribute
    """
    country_name = Country.name_from_id(user.get_profile().country).upper()
    iso3_country_name = iso2_to_iso3[country_name]
    return iso3_country_name


class AttachmentMixin(object):

    def latest_attachments(self):
        attachments = self.attachments.all().order_by('-created')
        for attachment in attachments:
            yield attachment


class CreatableFromString(object):
    """Simple objects that can be created from string."""

    @classmethod  # Decided not to play with abstractclassmethods
    def create_from_string(cls, asset_type, string_name):
        raise NotImplementedError


class Sluggy(models.Model):
    """An object with a unique slug."""

    class Meta:
        abstract = True

    slug = models.SlugField(
        max_length=100,
        unique=True,
        blank=True,
        primary_key=True
    )


class LicenseType(Choices):
    _ = Choices.Choice
    not_applicable = _("not applicable")
    oem = _("oem")
    box = _("box")


class Orientation(Choices):
    _ = Choices.Choice

    DEPTH = Choices.Group(0)
    front = _("front")
    back = _("back")
    middle = _("middle")

    WIDTH = Choices.Group(100)
    left = _("left")
    right = _("right")

    @classmethod
    def is_width(cls, orientation):
        is_width = orientation in set(
            [choice.id for choice in cls.WIDTH.choices]
        )
        return is_width

    @classmethod
    def is_depth(cls, orientation):
        is_depth = orientation in set(
            [choice.id for choice in cls.DEPTH.choices]
        )
        return is_depth


class AssetType(Choices):
    _ = Choices.Choice

    DC = Choices.Group(0)
    data_center = _("data center")

    BO = Choices.Group(100)
    back_office = _("back office")
    administration = _("administration")

    OTHER = Choices.Group(200)
    other = _("other")


MODE2ASSET_TYPE = {
    'dc': AssetType.data_center,
    'back_office': AssetType.back_office,
    'administration': AssetType.administration,
    'other': AssetType.other,
}


ASSET_TYPE2MODE = {v: k for k, v in MODE2ASSET_TYPE.items()}


class AssetPurpose(Choices):
    _ = Choices.Choice

    for_contractor = _("for contractor")
    sectional = _("sectional")
    for_dashboards = _("for dashboards")
    for_events = _("for events")
    for_tests = _("for tests")
    others = _("others")


class AssetStatus(Choices):
    _ = Choices.Choice

    HARDWARE = Choices.Group(0)
    new = _("new")
    in_progress = _("in progress")
    waiting_for_release = _("waiting for release")
    used = _("in use")
    loan = _("loan")
    damaged = _("damaged")
    liquidated = _("liquidated")
    in_service = _("in service")
    in_repair = _("in repair")
    ok = _("ok")

    SOFTWARE = Choices.Group(100)
    installed = _("installed")
    free = _("free")
    reserved = _("reserved")


class AssetSource(Choices):
    _ = Choices.Choice

    shipment = _("shipment")
    salvaged = _("salvaged")


class AssetCategoryType(Choices):
    _ = Choices.Choice

    back_office = _("back office")
    data_center = _("data center")


class AssetManufacturer(
    CreatableFromString,
    TimeTrackable,
    EditorTrackable,
    Named
):
    def __unicode__(self):
        return self.name

    @classmethod
    def create_from_string(cls, asset_type, string_name):
        return cls(name=string_name)


class AssetModel(
    CreatableFromString,
    TimeTrackable,
    EditorTrackable,
    Named.NonUnique,
    WithConcurrentGetOrCreate
):
    '''
    Asset models describing hardware and contain standard information like
    created at
    '''
    manufacturer = models.ForeignKey(
        AssetManufacturer, on_delete=models.PROTECT, blank=True, null=True)
    category = models.ForeignKey(
        'AssetCategory', null=True, blank=True, related_name='models'
    )
    power_consumption = models.IntegerField(
        verbose_name=_("Power consumption"),
        blank=True,
        default=0,
    )
    height_of_device = models.FloatField(
        verbose_name=_("Height of device"),
        blank=True,
        default=0,
    )
    cores_count = models.IntegerField(
        verbose_name=_("Cores count"),
        blank=True,
        default=0,
    )
    type = models.PositiveIntegerField(choices=AssetType(), null=True)

    def __unicode__(self):
        return "%s %s" % (self.manufacturer, self.name)

    @classmethod
    def create_from_string(cls, asset_type, string_name):
        return cls(type=asset_type, name=string_name)


class AssetOwner(
    TimeTrackable, Named, WithConcurrentGetOrCreate, CreatableFromString,
):
    """The company or other entity that are owners of assets."""

    @classmethod
    def create_from_string(cls, string_name, *args, **kwargs):
        return cls(name=string_name)


class AssetCategory(
    MPTTModel,
    TimeTrackable,
    EditorTrackable,
    WithConcurrentGetOrCreate,
    Sluggy,
):
    name = models.CharField(max_length=50, unique=False)
    type = models.PositiveIntegerField(
        verbose_name=_("type"), choices=AssetCategoryType(),
    )
    code = models.CharField(max_length=4, blank=True, default='')
    is_blade = models.BooleanField()
    parent = TreeForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='children',
    )

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name = _("Asset category")
        verbose_name_plural = _("Asset categories")

    def __unicode__(self):
        return self.name


class Warehouse(
    TimeTrackable,
    EditorTrackable,
    Named,
    WithConcurrentGetOrCreate,
    CreatableFromString,
):
    def __unicode__(self):
        return self.name

    @classmethod
    def create_from_string(cls, asset_type, string_name):
        return cls(name=string_name)


def _get_file_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = "%s.%s" % (uuid4(), ext)
    return os.path.join('assets', filename)


class BOAdminManager(models.Manager):
    def get_query_set(self):
        return super(BOAdminManager, self).get_query_set().filter(
            type__in=(AssetType.BO.choices)
        )


class DCAdminManager(models.Manager):
    def get_query_set(self):
        return super(DCAdminManager, self).get_query_set().filter(
            type__in=(AssetType.DC.choices)
        )


class AssetAdminManager(models.Manager):
    pass


class BOManager(
    BOAdminManager, ViewableSoftDeletableManager, RegionalizedDBManager
):
    pass


class DCManager(
    DCAdminManager, ViewableSoftDeletableManager, RegionalizedDBManager
):
    pass


class Attachment(SavingUser, TimeTrackable):
    original_filename = models.CharField(max_length=255, unique=False)
    file = models.FileField(upload_to=_get_file_path, blank=False, null=True)
    uploaded_by = models.ForeignKey(User, null=True, blank=True)

    def save(self, *args, **kwargs):
        filename = getattr(self.file, 'name') or 'unknown'
        self.original_filename = filename
        super(Attachment, self).save(*args, **kwargs)


class Service(Named, TimeTrackable, CreatableFromString):
    profit_center = models.CharField(max_length=1024, blank=True)
    cost_center = models.CharField(max_length=1024, blank=True)

    @classmethod
    def create_from_string(cls, string_name, *args, **kwargs):
        return cls(name=string_name)


class BudgetInfo(
    TimeTrackable,
    EditorTrackable,
    Named,
    WithConcurrentGetOrCreate,
    CreatableFromString,
):
    """
    Info pointing source of money (budget) for *assets* and *licenses*.
    """
    def __unicode__(self):
        return self.name

    @classmethod
    def create_from_string(cls, asset_type, string_name):
        return cls(name=string_name)


class AssetLastHostname(models.Model):
    prefix = models.CharField(max_length=8, db_index=True)
    counter = models.PositiveSmallIntegerField(default=1)
    postfix = models.CharField(max_length=8, db_index=True)

    class Meta:
        unique_together = ('prefix', 'postfix')

    def __unicode__(self):
        return self.formatted_hostname()

    def formatted_hostname(self, fill=5):
        return '{prefix}{counter:0{fill}}{postfix}'.format(
            prefix=self.prefix,
            counter=int(self.counter),
            fill=fill,
            postfix=self.postfix,
        )

    @classmethod
    def increment_hostname(cls, prefix, postfix=''):
        obj, created = cls.objects.get_or_create(
            prefix=prefix,
            postfix=postfix,
        )
        if not created:
            # F() avoid race condition problem
            obj.counter = models.F('counter') + 1
            obj.save()
            return cls.objects.get(pk=obj.pk)
        else:
            return obj


class Asset(
    AttachmentMixin,
    Regionalized,
    HistoryMixin,
    TimeTrackable,
    EditorTrackable,
    SavingUser,
    SoftDeletable,
    WithForm,
    SyncFieldMixin,
):
    '''
    Asset model contain fields with basic information about single asset
    '''
    device_info = models.OneToOneField(
        'DeviceInfo', null=True, blank=True, on_delete=models.CASCADE,
    )
    part_info = models.OneToOneField(
        'PartInfo', null=True, blank=True, on_delete=models.CASCADE,
    )
    office_info = models.OneToOneField(
        'OfficeInfo', null=True, blank=True, on_delete=models.CASCADE,
    )
    type = models.PositiveSmallIntegerField(choices=AssetType())
    model = models.ForeignKey(
        'AssetModel', on_delete=models.PROTECT, related_name='assets',
    )
    source = models.PositiveIntegerField(
        verbose_name=_("source"), choices=AssetSource(), db_index=True,
        null=True, blank=True,
    )
    invoice_no = models.CharField(
        max_length=128, db_index=True, null=True, blank=True,
    )
    order_no = models.CharField(max_length=50, null=True, blank=True)
    invoice_date = models.DateField(null=True, blank=True)
    sn = models.CharField(max_length=200, null=True, blank=True, unique=True)
    barcode = models.CharField(
        max_length=200, null=True, blank=True, unique=True, default=None,
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, blank=True, null=True,
    )
    support_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )
    support_period = models.PositiveSmallIntegerField(
        blank=True,
        default=0,
        null=True,
        verbose_name="support period in months"
    )
    support_type = models.CharField(max_length=150, blank=True)
    support_void_reporting = models.BooleanField(default=True, db_index=True)
    provider = models.CharField(max_length=100, null=True, blank=True)
    status = models.PositiveSmallIntegerField(
        default=AssetStatus.new.id,
        verbose_name=_("status"),
        choices=AssetStatus(),
        null=True,
        blank=True,
    )
    remarks = models.CharField(
        verbose_name='Additional remarks',
        max_length=1024,
        blank=True,
    )
    niw = models.CharField(
        max_length=200, null=True, blank=True, default=None,
        verbose_name='Inventory number',
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    location = models.CharField(max_length=128, null=True, blank=True)
    request_date = models.DateField(null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    production_use_date = models.DateField(null=True, blank=True)
    provider_order_date = models.DateField(null=True, blank=True)
    deprecation_rate = models.DecimalField(
        decimal_places=2,
        max_digits=5,
        blank=True,
        default=settings.DEFAULT_DEPRECATION_RATE,
    )
    force_deprecation = models.BooleanField(help_text=(
        'Check if you no longer want to bill for this asset'
    ))
    deprecation_end_date = models.DateField(null=True, blank=True)
    production_year = models.PositiveSmallIntegerField(null=True, blank=True)
    slots = models.FloatField(
        verbose_name='Slots',
        help_text=('For blade centers: the number of slots available in this '
                   'device. For blade devices: the number of slots occupied.'),
        max_length=64,
        default=0,
    )
    service_name = models.ForeignKey(Service, null=True, blank=True)
    admin_objects = AssetAdminManager()
    admin_objects_dc = DCAdminManager()
    admin_objects_bo = BOAdminManager()
    objects_dc = DCManager()
    objects_bo = BOManager()
    task_url = models.URLField(
        max_length=2048, null=True, blank=True, unique=False,
        help_text=('External workflow system URL'),
    )
    property_of = models.ForeignKey(
        AssetOwner,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    owner = models.ForeignKey(
        User, null=True, blank=True, related_name="owner",
    )
    user = models.ForeignKey(
        User, null=True, blank=True, related_name="user",
    )
    attachments = models.ManyToManyField(
        Attachment,
        null=True,
        blank=True,
        related_name='parents',
    )
    loan_end_date = models.DateField(
        null=True, blank=True, default=None, verbose_name=_('Loan end date'),
    )
    note = models.CharField(
        verbose_name=_('Note'),
        max_length=1024,
        blank=True,
    )
    budget_info = models.ForeignKey(
        BudgetInfo,
        blank=True,
        default=None,
        null=True,
        on_delete=models.PROTECT,
    )
    hostname = models.CharField(
        blank=True,
        default=None,
        max_length=16,
        null=True,
        unique=True,
        help_text=HOSTNAME_FIELD_HELP_TIP,
    )
    required_support = models.BooleanField(default=False)
    service = models.ForeignKey(
        ServiceCatalog,
        default=None,
        null=True,
        on_delete=models.PROTECT,
    )
    device_environment = models.ForeignKey(
        DeviceEnvironment,
        default=None,
        null=True,
        on_delete=models.PROTECT,
    )

    def __unicode__(self):
        return "{} - {} - {}".format(self.model, self.sn, self.barcode)

    @property
    def linked_device(self):
        try:
            device = self.device_info.get_ralph_device()
        except AttributeError:
            device = None
        return device

    @property
    def venture(self):
        try:
            return self.get_ralph_device().venture
        except AttributeError:
            return None

    @property
    def cores_count(self):
        """Returns cores count assigned to device in Ralph"""
        asset_cores_count = self.model.cores_count if self.model else 0
        if settings.SHOW_RALPH_CORES_DIFF:
            device_cores_count = None
            try:
                if self.device_info and self.device_info.ralph_device_id:
                    device_cores_count = Device.objects.get(
                        pk=self.device_info.ralph_device_id,
                    ).get_core_count()
            except Device.DoesNotExist:
                pass
            if (device_cores_count is not None and
               asset_cores_count != device_cores_count):
                logger.warning(
                    ('Cores count for <{}> different in ralph than '
                     'in assets ({} vs {})').format(
                        self,
                        device_cores_count,
                        asset_cores_count,
                    )
                )
        return asset_cores_count

    @classmethod
    def create(cls, base_args, device_info_args=None, part_info_args=None):
        asset = Asset(**base_args)
        if device_info_args:
            d = DeviceInfo(**device_info_args)
            d.save()
            asset.device_info = d
        elif part_info_args:
            d = PartInfo(**part_info_args)
            d.save()
            asset.part_info = d
        asset.save()
        return asset

    def get_data_type(self):
        if self.part_info:
            return 'part'
        else:
            return 'device'

    def _try_assign_hostname(self, commit):
        if self.owner and self.model.category and self.model.category.code:
            template_vars = {
                'code': self.model.category.code,
                'country_code': self.country_code,
            }
            if not self.hostname:
                self.generate_hostname(commit, template_vars)
            else:
                user_country = get_user_iso3_country_name(self.owner)
                different_country = user_country not in self.hostname
                if different_country:
                    self.generate_hostname(commit, template_vars)

    def get_ralph_device(self):
        if not self.device_info or not self.device_info.ralph_device_id:
            return None
        try:
            return Device.objects.get(
                pk=self.device_info.ralph_device_id,
            )
        except Device.DoesNotExist:
            return None

    def get_synced_objs_and_fields(self):
        # Implementation of the abstract method from SyncFieldMixin.
        fields = ['service', 'device_environment']
        obj = self.get_ralph_device()
        return [(obj, fields)] if obj else []

    @property
    def exists(self):
        """Check if object is a new db record"""
        return self.pk is not None

    def handle_device_linkage(self, force_unlink):
        """When try to match it with an existing device or create a dummy
        (stock) device and then match with it instead.
        Note: it does not apply to assets created with 'add part' button.

        Cases:
        when adding asset:
            no barcode -> add asset + create dummy device
            set barcode from unlinked device -> add asset + link device
            set barcode from linked device -> error
            set barcode from linked device + force unlink -> add + relink

        when editing asset:
            do nothing
        """
        try:
            ralph_device_id = self.device_info.ralph_device_id
        except AttributeError:
            # asset created with 'add part'
            pass
        else:
            if not self.exists:
                if not ralph_device_id:
                    device = self.find_device_to_link()
                    if device:
                        if force_unlink:
                            asset = device.get_asset()
                            asset.device_info.ralph_device_id = None
                            asset.device_info.save()
                        self.device_info.ralph_device_id = device.id
                        self.device_info.save()
                    else:
                        self.create_stock_device()

    def save(self, commit=True, force_unlink=False, *args, **kwargs):
        _replace_empty_with_none(self, ['source', 'hostname'])
        self.handle_device_linkage(force_unlink)
        return super(Asset, self).save(commit=commit, *args, **kwargs)

    def get_data_icon(self):
        if self.get_data_type() == 'device':
            return 'fugue-computer'
        elif self.get_data_type() == 'part':
            return 'fugue-box'
        else:
            raise UserWarning('Unknown asset data type!')

    @property
    def type_is_data_center(self):
        return self.type == AssetType.data_center

    def find_device_to_link(self):
        if not self.type_is_data_center or (not self.barcode and not self.sn):
            return None
        device = None
        if self.barcode:
            try:
                device = Device.objects.get(barcode=self.barcode)
            except Device.DoesNotExist:
                pass
        if not device and self.sn:
            try:
                device = Device.objects.get(sn=self.sn)
            except Device.DoesNotExist:
                device = None
        return device

    def create_stock_device(self):
        if not self.type_is_data_center:
            return
        if not self.device_info.ralph_device_id:
            try:
                venture = Venture.objects.get(name='Stock')
            except Venture.DoesNotExist:
                venture = Venture(name='Stock', symbol='stock')
                venture.save()
            device = Device.create(
                sn=self.sn or 'bc-' + self.barcode,
                barcode=self.barcode,
                model_name='Unknown',
                model_type=DeviceType.unknown,
                priority=SAVE_PRIORITY,
                venture=venture,
            )
            device.name = getattr(self.model, 'name', 'Unknown')
            device.remarks = self.order_no or ''
            device.dc = getattr(self.warehouse, 'name', '')
            device.save()
            self.device_info.ralph_device_id = device.id
            self.device_info.save()

    def get_parts_info(self):
        return PartInfo.objects.filter(device=self)

    def get_parts(self):
        return Asset.objects.filter(part_info__device=self)

    def has_parts(self):
        return PartInfo.objects.filter(device=self).exists()

    def __init__(self, *args, **kwargs):
        self.save_comment = None
        self.saving_user = None
        super(Asset, self).__init__(*args, **kwargs)

    def get_deprecation_months(self):
        return int(
            (1 / (self.deprecation_rate / 100) * 12)
            if self.deprecation_rate else 0
        )

    def is_deprecated(self, date=None):
        date = date or datetime.date.today()
        if self.force_deprecation or not self.invoice_date:
            return True
        if self.deprecation_end_date:
            deprecation_date = self.deprecation_end_date
        else:
            deprecation_date = self.invoice_date + relativedelta(
                months=self.get_deprecation_months(),
            )
        return deprecation_date < date

    def delete_with_info(self, *args, **kwargs):
        """
        Remove Asset with linked info-tables alltogether, because cascade
        works bottom-up only.
        """
        if self.part_info:
            self.part_info.delete()
        elif self.office_info:
            self.office_info.delete()
        elif self.device_info:
            self.device_info.delete()
        return super(Asset, self).delete(*args, **kwargs)

    @property
    def is_discovered(self):
        if self.part_info:
            if self.part_info.device:
                return self.part_info.device.is_discovered()
            return False
        try:
            dev = self.device_info.get_ralph_device()
        except AttributeError:
            return False
        else:
            if not dev or not dev.model:
                return False
            return dev.model.type != DeviceType.unknown.id

    @property
    def url(self):
        return reverse('device_edit', kwargs={
            'mode': ASSET_TYPE2MODE[self.type],
            'asset_id': self.id,
        })

    @property
    def country_code(self):
        iso2 = Country.name_from_id(self.owner.profile.country).upper()
        return iso2_to_iso3.get(iso2, 'POL')

    @nested_commit_on_success
    def generate_hostname(self, commit=True, template_vars={}):
        def render_template(template):
            template = Template(template)
            context = Context(template_vars)
            return template.render(context)
        prefix = render_template(
            ASSET_HOSTNAME_TEMPLATE.get('prefix', ''),
        )
        postfix = render_template(
            ASSET_HOSTNAME_TEMPLATE.get('postfix', ''),
        )
        counter_length = ASSET_HOSTNAME_TEMPLATE.get('counter_length', 5)
        last_hostname = AssetLastHostname.increment_hostname(prefix, postfix)
        self.hostname = last_hostname.formatted_hostname(fill=counter_length)
        if commit:
            self.save()

    @property
    def asset_type(self):
        return self.type


class DeprecatedRalphDCManager(models.Manager):
    def get_query_set(self):
        query_set = super(DeprecatedRalphDCManager, self).get_query_set()
        data_centers = query_set.filter(model__type=DeviceType.data_center)
        return data_centers


class DeprecatedRalphDC(Device):
    objects = DeprecatedRalphDCManager()

    class Meta:
        proxy = True


class DeprecatedRalphRackManager(models.Manager):
    def get_query_set(self):
        query_set = super(DeprecatedRalphRackManager, self).get_query_set()
        racks = query_set.filter(model__type=DeviceType.rack)
        return racks


class DeprecatedRalphRack(Device):
    objects = DeprecatedRalphRackManager()

    class Meta:
        proxy = True


class DataCenter(Named):
    deprecated_ralph_dc = models.ForeignKey(
        DeprecatedRalphDC, null=True, blank=True,
    )


class ServerRoom(Named.NonUnique):
    data_center = models.ForeignKey(DataCenter, verbose_name=_("data center"))


class Rack(Named.NonUnique):
    class Meta:
        unique_together = ('name', 'data_center')

    data_center = models.ForeignKey(DataCenter, null=False, blank=False)
    server_room = models.ForeignKey(
        ServerRoom, verbose_name=_("server room"),
        null=True,
        blank=True,
    )
    max_u_height = models.IntegerField(default=48)
    deprecated_ralph_rack = models.ForeignKey(
        DeprecatedRalphRack, null=True, related_name='deprecated_asset_rack',
        blank=True,
    )


class DeviceInfo(TimeTrackable, SavingUser, SoftDeletable):
    ralph_device_id = models.IntegerField(
        verbose_name=_("Ralph device id"),
        null=True,
        blank=True,
        unique=True,
        default=None,
    )
    u_level = models.CharField(max_length=10, null=True, blank=True)
    u_height = models.CharField(max_length=10, null=True, blank=True)
    data_center = models.ForeignKey(DataCenter, null=True, blank=False)
    server_room = models.ForeignKey(ServerRoom, null=True, blank=False)
    rack = models.ForeignKey(Rack, null=True, blank=True)
    # deperecated field, use rack instead
    rack_old = models.CharField(max_length=10, null=True, blank=True)
    slot_no = models.IntegerField(
        verbose_name=_("slot number"), null=True, blank=True,
    )
    position = models.IntegerField(null=True)
    orientation = models.PositiveIntegerField(
        choices=Orientation(),
        default=Orientation.front.id,
    )

    def clean_fields(self, exclude=None):
        """
        Constraints:
        - picked rack is from picked server-room
        - picked server-room is from picked data-center
        - postion = 0: orientation(left, right)
        - postion > 0: orientation(front, middle, back)
        - position <= rack.max_u_height
        - slot_no: asset is_blade=True
        """
        if self.rack and self.server_room:
            if self.rack.server_room != self.server_room:
                msg = 'Valid server room for this rack is: "{}"'.format(
                    self.rack.server_room.name,
                )
                raise ValidationError(
                    {'server_room': msg}, code=INVALID_SERVER_ROOM,
                )
        if self.server_room and self.data_center:
            if self.server_room.data_center != self.data_center:
                msg = 'Valid data center for this server room is: "{}"'.format(
                    self.server_room.data_center.name,
                )
                raise ValidationError(
                    {'data_center': msg}, code=INVALID_DATA_CENTER,
                )
        if self.position == 0 and not Orientation.is_width(self.orientation):
            msg = 'Valid orientations for picked position are: {}'.format(
                ', '.join(
                    choice.desc for choice in Orientation.WIDTH.choices
                )
            )
            raise ValidationError(
                {'orientation': msg}, code=INVALID_ORIENTATION
            )
        if self.position > 0 and not Orientation.is_depth(self.orientation):
            msg = 'Valid orientations for picked position are: {}'.format(
                ', '.join(
                    choice.desc for choice in Orientation.DEPTH.choices
                )
            )
            raise ValidationError(
                {'orientation': msg}, code=INVALID_ORIENTATION,
            )
        if self.rack and self.position > self.rack.max_u_height:
            msg = 'Position is higher than "max u height" = {}'.format(
                self.rack.max_u_height,
            )
            raise ValidationError({'position': msg}, code=INVALID_POSITION)
        try:
            is_blade = self.asset.model.category.is_blade
        except (AttributeError, Asset.DoesNotExist):
            is_blade = False
        else:
            if is_blade and self.slot_no is None:
                msg = "'slot number' is required when asset is blade"
                raise ValidationError(
                    {'slot_no': msg}, code=REQUIRED_SLOT_NUMBER,
                )

    @property
    def size(self):
        """Deprecated. Kept for backwards compatibility."""
        return 0

    def __unicode__(self):
        return "{} - {}".format(
            self.ralph_device_id,
            self.size,
        )

    def get_ralph_device(self):
        if not self.ralph_device_id:
            return None
        try:
            dev = Device.objects.get(id=self.ralph_device_id)
            return dev
        except Device.DoesNotExist:
            return None

    def __init__(self, *args, **kwargs):
        self.save_comment = None
        self.saving_user = None
        super(DeviceInfo, self).__init__(*args, **kwargs)


@receiver(
    post_delete,
    sender=Device,
    dispatch_uid='discovery.device.post_delete',
)
def device_post_delete(sender, instance, **kwargs):
    for deviceinfo in DeviceInfo.objects.filter(ralph_device_id=instance.id):
        deviceinfo.ralph_device_id = None
        deviceinfo.save()


@receiver(post_save, sender=Device, dispatch_uid='ralph_assets.device_delete')
def device_post_save(sender, instance, **kwargs):
    """
    A hook for cleaning ``ralph_device_id`` in ``DeviceInfo`` when device
    linked to it gets soft-deleted (hence post-save signal instead of
    pre-delete or post-delete).
    """
    if instance.deleted:
        try:
            di = DeviceInfo.objects.get(ralph_device_id=instance.id)
            di.ralph_device_id = None
            di.save()
        except (DeviceInfo.DoesNotExist, DatabaseError):
            pass


class CoaOemOs(Named):
    """Define oem installed operating system"""


class OfficeInfo(TimeTrackable, SavingUser, SoftDeletable):
    license_key = models.TextField(null=True, blank=True,)
    coa_number = models.CharField(
        max_length=256, verbose_name="COA number", null=True, blank=True,
    )
    coa_oem_os = models.ForeignKey(
        CoaOemOs, verbose_name="COA oem os", null=True, blank=True,
    )
    imei = models.CharField(
        max_length=18, null=True, blank=True, unique=True
    )
    purpose = models.PositiveSmallIntegerField(
        verbose_name=_("purpose"), choices=AssetPurpose(), null=True,
        blank=True, default=None
    )

    def get_purpose(self):
        return AssetPurpose.from_id(self.purpose).raw if self.purpose else None

    def save(self, commit=True, *args, **kwargs):
        _replace_empty_with_none(self, ['purpose'])
        instance = super(OfficeInfo, self).save(commit=commit, *args, **kwargs)
        return instance

    def __unicode__(self):
        return "{} - {} - {}".format(
            self.coa_oem_os,
            self.coa_number,
            self.purpose,
            self.imei,
        )

    def __init__(self, *args, **kwargs):
        self.save_comment = None
        self.saving_user = None
        super(OfficeInfo, self).__init__(*args, **kwargs)


class PartInfo(TimeTrackable, SavingUser, SoftDeletable):
    barcode_salvaged = models.CharField(max_length=200, null=True, blank=True)
    source_device = models.ForeignKey(
        Asset, null=True, blank=True, related_name='source_device'
    )
    device = models.ForeignKey(
        Asset, null=True, blank=True, related_name='device'
    )

    def __unicode__(self):
        return "{} - {}".format(self.device, self.barcode_salvaged)

    def __init__(self, *args, **kwargs):
        self.save_comment = None
        self.saving_user = None
        super(PartInfo, self).__init__(*args, **kwargs)


class ReportOdtSource(Named, SavingUser, TimeTrackable):
    slug = models.SlugField(max_length=100, unique=True, blank=False)

    @property
    def template(self):
        "Return first template - it's only for backward compatibility."
        return self.templates[0].template

    @property
    def templates(self):
        return self.odt_templates.all() if self.odt_templates.count() else []


class ReportOdtSourceLanguage(SavingUser, TimeTrackable):
    template = models.FileField(upload_to=_get_file_path, blank=False)
    language = models.CharField(max_length=3, **REPORT_LANGUAGES)
    report_odt_source = models.ForeignKey(
        ReportOdtSource,
        related_name='odt_templates',
    )

    class Meta:
        unique_together = ('language', 'report_odt_source')

    @property
    def slug(self):
        return self.report_odt_source.slug


@receiver(pre_save, sender=Asset, dispatch_uid='ralph_assets.views.device')
def device_hostname_assigning(sender, instance, raw, using, **kwargs):
    """A hook for assigning ``hostname`` value when an asset is edited."""
    if getattr(settings, 'ASSETS_AUTO_ASSIGN_HOSTNAME', None):
        for field, orig, new in field_changes(instance):
            status_desc = AssetStatus.in_progress.desc
            if all((
                field == 'status', orig != status_desc, new == status_desc
            )):
                instance._try_assign_hostname(commit=False)
