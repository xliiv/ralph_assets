# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from factory import Sequence, SubFactory
from factory.django import DjangoModelFactory, FileField

from ralph.ui.tests.global_utils import UserFactory
from ralph_assets.models_assets import (
    AssetStatus,
    ReportOdtSource,
    ReportOdtSourceLanguage,
)
from ralph_assets.models_transition import Transition, TransitionsHistory


class TransitionFactory(DjangoModelFactory):
    """Actions in transition must by added manually in tests"""

    FACTORY_FOR = Transition

    name = 'change-hostname'
    slug = 'change-hostname'
    to_status = AssetStatus.in_progress
    required_report = False


class TransitionsHistoryFactory(DjangoModelFactory):
    FACTORY_FOR = TransitionsHistory

    transition = SubFactory(TransitionFactory)
    logged_user = SubFactory(UserFactory)
    affected_user = SubFactory(UserFactory)
    report_filename = Sequence(lambda n: 'report'.format(n))
    uid = Sequence(lambda n: 'uid {}'.format(n))
    report_file = FileField(
        data=b'uploaded_file_content', filename='report_file.txt',
    )


class ReportOdtSourceFactory(DjangoModelFactory):
    FACTORY_FOR = ReportOdtSource
    name = Sequence(lambda n: 'name #{}'.format(n))
    slug = Sequence(lambda n: 'name-{}'.format(n))


class ReportOdtSourceLanguageFactory(DjangoModelFactory):
    FACTORY_FOR = ReportOdtSourceLanguage

    template = FileField(
        data=b'uploaded_file_content', filename='report_file.txt',
    )
    report_odt_source = SubFactory(ReportOdtSourceFactory)
