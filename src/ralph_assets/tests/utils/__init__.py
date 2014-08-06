# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from factory import (
    Sequence,
    lazy_attribute,
)
from factory.django import DjangoModelFactory

from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import Client


def login_as_user(user=None, password='ralph', *args, **kwargs):
    if not user:
        user = UserFactory(*args, **kwargs)
        user.set_password(password)
        user.save()
    client = Client()
    client.login(username=user.username, password=password)
    return client


class UserFactory(DjangoModelFactory):
    """
    User *password* is 'ralph'.
    """
    FACTORY_FOR = User

    username = Sequence(lambda n: 'user_%d' % n)

    @lazy_attribute
    def email(self):
        return '%s@example.com' % self.username

    @classmethod
    def _generate(cls, create, attrs):
        user = super(UserFactory, cls)._generate(create, attrs)
        user.set_password('ralph')
        user.save()
        return user


class AdminFactory(UserFactory):
    admin = True


class MessagesTestMixin(TestCase):
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
