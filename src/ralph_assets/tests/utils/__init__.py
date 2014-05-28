# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from factory import Factory, Sequence, lazy_attribute

from django.contrib.auth.models import User


class UserFactory(Factory):
    FACTORY_FOR = User

    username = Sequence(lambda n: 'user_%d' % n)

    @lazy_attribute
    def email(self):
        return '%s@example.com' % self.username


class AdminFactory(UserFactory):
    admin = True
