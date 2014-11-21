#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import logging

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from lck.django.common.models import (
    Named,
    TimeTrackable,
    WithConcurrentGetOrCreate,
)
from ralph_assets.models_assets import (
    Asset,
    AssetStatus,
    ReportOdtSourceLanguage,
)


logger = logging.getLogger(__name__)


def _get_file_path(instance, filename):
    return os.path.join('assets', filename)


class Action(Named):
    """
    Actions performed in the transaction
    """


class Transition(Named, TimeTrackable, WithConcurrentGetOrCreate):
    slug = models.SlugField(max_length=100, unique=True, blank=False)
    from_status = models.PositiveSmallIntegerField(
        verbose_name=_("from"),
        choices=AssetStatus(),
        null=True,
        blank=True,
    )
    to_status = models.PositiveSmallIntegerField(
        verbose_name=_("to"),
        choices=AssetStatus(),
    )
    actions = models.ManyToManyField(Action)
    required_report = models.BooleanField(default=False)

    @property
    def actions_names(self, *args, **kwargs):
        return [action.name for action in self.actions.all()]

    @cached_property
    def odt_templates(self):
        return ReportOdtSourceLanguage.objects.filter(
            report_odt_source__slug=self.slug
        )


class TransitionsHistory(TimeTrackable, WithConcurrentGetOrCreate):
    class Meta:
        ordering = ['-created']
    transition = models.ForeignKey(Transition)
    assets = models.ManyToManyField(Asset)
    logged_user = models.ForeignKey(
        User, related_name='logged_user_transition_histories'
    )
    affected_user = models.ForeignKey(
        User,
        related_name='affected_user_transition_histories',
        null=True,
        blank=True,
        default=None
    )
    report_filename = models.CharField(max_length=256, null=True, blank=True)
    uid = models.CharField(max_length=36, null=True, blank=True, default=None)
    report_file = models.FileField(upload_to=_get_file_path)

    def __unicode__(self, *args, **kwargs):
        return "{} - {}".format(self.transition, self.affected_user)

    @classmethod
    def create(
        cls,
        transition,
        assets,
        logged_user,
        affected_user,
        report_filename,
        uid,
        report_file_path,
    ):
        transition_history = TransitionsHistory()
        transition_history.transition = transition
        transition_history.logged_user = logged_user
        transition_history.affected_user = affected_user
        transition_history.report_filename = report_filename
        transition_history.uid = uid
        if report_filename:
            try:
                with open(report_file_path, 'rb') as f:
                    content = f.read()
                    f.close()
                    content = ContentFile(content)
                    transition_history.report_file.save(
                        report_filename, content, save=True,
                    )
            except IOError as e:
                logger.error(
                    "Can not read report file: {} ({})".format(
                        report_file_path, e,
                    ),
                )
        transition_history.save()
        transition_history.assets.add(*assets)
        return transition_history
