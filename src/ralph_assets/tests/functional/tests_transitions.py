# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import urllib

from datetime import date

import django.dispatch
from dj.choices import Country
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings


from ralph.ui.tests.global_utils import login_as_su
from ralph.ui.tests.global_utils import UserFactory
from ralph_assets import signals
from ralph_assets.models_assets import Asset
from ralph_assets.models_transition import Action
from ralph_assets.tests.utils import MessagesTestMixin
from ralph_assets.tests.utils.assets import BOAssetFactory, WarehouseFactory
from ralph_assets.tests.utils.transitions import (
    TransitionFactory,
    TransitionsHistoryFactory,
    ReportOdtSourceFactory,
    ReportOdtSourceLanguageFactory,
)
from ralph_assets.tests.utils.licences import LicenceFactory


ASSETS_TRANSITIONS = {
    'ENABLE': True,
    'SLUGS': {
        'RELEASE-ASSET': 'release-asset',
        'LOAN-ASSET': 'loan-asset',
        'RETURN-ASSET': 'return-asset',
        'CHANGE-HOSTNAME': 'change-hostname',
    }
}

REPORT_LANGUAGES = {
    'choices': (
        ('en', 'English'),
        ('pl', 'Polish'),
    ),
    'default': 'en',
}

unassign_actions = [
    'unassign_user',
    'unassign_owner',
    'unassign_loan_end_date',
    'unassign_licences'
]


def prepare_transition(slug, actions=None, required_report=False):
    action_list = actions or [
        'assign_user',
        'assign_owner',
        'assign_loan_end_date',
        'assign_warehouse',
        'change_status',
    ]

    def _prepare_transition(f):
        def wrapper(self, *args, **kwargs):
            self.transition = TransitionFactory(**{
                'name': slug,
                'slug': slug,
                'required_report': required_report,
            })
            if required_report:
                report_odt_source = ReportOdtSourceFactory(slug=slug)
                for lang in ['en', 'pl']:
                    self.odt_template = ReportOdtSourceLanguageFactory(
                        report_odt_source=report_odt_source,
                        language=lang
                    )
            actions = Action.objects.filter(name__in=action_list)
            self.transition.actions.add(*actions)
            return f(self, *args, **kwargs)
        return wrapper
    return _prepare_transition


@override_settings(ASSETS_AUTO_ASSIGN_HOSTNAME=True)
@override_settings(ASSETS_TRANSITIONS=ASSETS_TRANSITIONS)
class TestTransitionHostname(MessagesTestMixin, TestCase):

    @prepare_transition('change-hostname', actions=['change_hostname'])
    def setUp(self):
        self.client = login_as_su()

    def assertMessageEqual(self, response, text):
        """
        Asserts that the response includes the message text.
        """
        messages = [m.message for m in response.context['messages']]
        if text not in messages:
            self.fail(
                'No message with text "{}", messages were: {}'.format(
                    text, messages,
                )
            )

    def test_change_hostname_success(self):
        asset = BOAssetFactory(**{
            'hostname': '',
            'model__category__code': 'PC',
        })
        post_data = {'country': Country.pl.id}
        url_base = reverse('transition', args=('back_office',))
        url_params = {'select': asset.id, 'transition_type': 'change-hostname'}
        url = "{}?{}".format(url_base, urllib.urlencode(url_params))
        self.client.post(url, post_data, follow=True)
        changed_asset = Asset.objects.get(pk=asset.id)
        self.assertEqual(changed_asset.hostname, 'POLPC00001')

    def test_change_hostname_failed(self):
        """Asset model has not assigned category with code,
        hostname will be not generated"""
        asset = BOAssetFactory(**{
            'hostname': '',
            'model__category__code': '',
        })
        post_data = {'country': Country.pl.id}
        url_base = reverse('transition', args=('back_office',))
        url_params = {'select': asset.id, 'transition_type': 'change-hostname'}
        url = "{}?{}".format(url_base, urllib.urlencode(url_params))
        response = self.client.get(url, follow=True)
        self.assertMessageEqual(
            response,
            'Asset has no assigned category with code',
        )
        self.client.post(url, post_data, follow=True)
        changed_asset = Asset.objects.get(pk=asset.id)
        self.assertEqual(changed_asset.hostname, None)

    def _get_simple_transition_data(self):
        """Executes steps required by transition"""
        asset = BOAssetFactory(**{
            'hostname': '',
            'model__category__code': 'PC',
        })
        post_data = {'country': Country.pl.id}
        url_base = reverse('transition', args=('back_office',))
        url_params = {
            'select': asset.id,
            'transition_type': 'change-hostname',
        }
        url = "{}?{}".format(
            url_base, urllib.urlencode(url_params)
        )
        return url, post_data

    def test_successful_post_transition(self):
        """
        Transition is done successfully.
        """
        @django.dispatch.receiver(signals.post_transition)
        def post_transition_handler(
            sender, user, assets, transition, **kwargs
        ):
            pass

        url, post_data = self._get_simple_transition_data()
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(len(response.context['messages']), 1)
        self.assertEqual(
            str(response.context['messages']._loaded_messages[0]),
            "Transitions performed successfully",
        )

    def test_failed_post_transition(self):
        """
        Transition is done unsuccessfully.
        """
        @django.dispatch.receiver(signals.post_transition)
        def post_transition_handler(
            sender, user, assets, transition, **kwargs
        ):
            from ralph_assets.views import transition
            raise transition.PostTransitionException(
                "Unable to generate document - try later, please."
            )

        url, post_data = self._get_simple_transition_data()
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(len(response.context['messages']), 1)
        self.assertEqual(
            str(response.context['messages']._loaded_messages[0]),
            "Unable to generate document - try later, please.",
        )


@override_settings(ASSETS_TRANSITIONS=ASSETS_TRANSITIONS)
@override_settings(REPORT_LANGUAGES=REPORT_LANGUAGES)
class TestTransition(TestCase):
    """
    Test transition assign and unassign fields.
    """

    def setUp(self):
        self.client = login_as_su()
        self._prepare_users()
        self._prepare_warehouse()

    def _prepare_warehouse(self):
        self.warehouse = WarehouseFactory()

    def _prepare_users(self):
        self.user = UserFactory()
        self.owner = UserFactory()

    def _prepare_assets(self, custom_values={}):
        self.assets = [BOAssetFactory(**custom_values) for _ in xrange(2)]

    def _assign_licence_to_assets(self):
        for asset in self.assets:
            lic = LicenceFactory()
            lic.assign(asset)

    def _base_test_transition_form_assign(self, url_params, post_params):
        url_base = reverse('transition', args=('back_office',))

        url = "{}?{}".format(
            url_base, urllib.urlencode(url_params, doseq=True)
        )
        response = self.client.post(url, post_params, follow=True)
        self.assertEqual(response.status_code, 200)

    @prepare_transition('release-asset', required_report=True)
    def test_transition_form_assign(self):
        self._prepare_assets()
        asset_ids = Asset.objects.values_list('id', flat=True)
        url_params = {'select': asset_ids, 'transition_type': 'release-asset'}
        post_params = {
            'user': self.user.id,
            'warehouse': self.warehouse.id,
            'loan_end_date': date.today().strftime('%Y-%m-%d'),
            'document_language': self.odt_template.id,
        }
        self._base_test_transition_form_assign(url_params, post_params)
        self.assertEqual(
            Asset.objects.values(
                'warehouse', 'status', 'user', 'loan_end_date',
            ).distinct().count(),
            1,
        )

    @prepare_transition('return-asset', unassign_actions, required_report=True)
    def test_transition_form_unassign(self):
        self._prepare_assets({'user': self.user})
        self._assign_licence_to_assets()
        asset_ids = Asset.objects.values_list('id', flat=True)
        url_params = {'select': asset_ids, 'transition_type': 'return-asset'}
        post_params = {'document_language': self.odt_template.id}
        self._base_test_transition_form_assign(url_params, post_params)
        self.assertEqual(
            Asset.objects.values(
                'user', 'owner', 'loan_end_date', 'licences',
            ).distinct().count(),
            1,
        )

    @prepare_transition('return-asset', unassign_actions, required_report=True)
    def test_transition_history_file(self):
        self._prepare_assets()
        history_id = TransitionsHistoryFactory(
            **{'transition': self.transition}
        ).id
        url = reverse('transition_history_file', args=(history_id,))
        response = self.client.get(url)
        self.assertEqual(response.get('Content-Type'), 'application/pdf')

        not_found_url = reverse('transition_history_file', args=(666,))
        response = self.client.get(not_found_url)
        self.assertEqual(response.status_code, 404)

    @prepare_transition('return-asset', unassign_actions, required_report=True)
    def test_transition_history_file_not_found_in_disk(self):
        self._prepare_assets()
        transition_history = TransitionsHistoryFactory(
            **{'transition': self.transition}
        )
        transition_history.report_file = None
        transition_history.save()
        url = reverse('transition_history_file', args=(transition_history.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @prepare_transition('return-asset', required_report=True)
    @prepare_transition('release-asset', required_report=True)
    @prepare_transition('loan-asset', required_report=True)
    def test_transition_form_contains_document_language(self):
        asset = BOAssetFactory()
        url_base = reverse('transition', args=('back_office',))
        transitions = ['release-asset', 'loan-asset', 'return-asset']
        for transition in transitions:
            url_params = {
                'select': asset.id,
                'transition_type': transition,
            }
            url = "{}?{}".format(url_base, urllib.urlencode(url_params))
            response = self.client.get(url)
            self.assertIn(
                'document_language',
                response.context['transition_form'].fields.keys(),
                "Field not found in {} transition".format(transition)
            )
