# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import urllib

import django.dispatch
from dj.choices import Country
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings


from ralph.ui.tests.global_utils import login_as_su
from ralph_assets import signals
from ralph_assets.models_assets import Asset
from ralph_assets.models_transition import Action
from ralph_assets.tests.utils import MessagesTestMixin
from ralph_assets.tests.utils.assets import BOAssetFactory
from ralph_assets.tests.utils.transitions import TransitionFactory


ASSETS_TRANSITIONS = {
    'ENABLE': True,
    'SLUGS': {
        'RELEASE-ASSET': 'release-asset',
        'LOAN-ASSET': 'loan-asset',
        'RETURN-ASSET': 'return-asset',
        'CHANGE-HOSTNAME': 'change-hostname',
    }
}


@override_settings(ASSETS_AUTO_ASSIGN_HOSTNAME=True)
@override_settings(ASSETS_TRANSITIONS=ASSETS_TRANSITIONS)
class TestTransitionHostname(MessagesTestMixin, TestCase):

    def setUp(self):
        self.client = login_as_su()
        self.prepare_transition()

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

    def prepare_transition(self):
        self.transition = TransitionFactory()
        self.transition.actions.add(Action.objects.get(name='change_hostname'))

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
