# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import csv
import cStringIO
import textwrap

from django.core.management.base import BaseCommand
from django.utils.encoding import smart_str
from optparse import make_option

from ralph_assets.others import get_assets_rows, get_licences_rows


class Command(BaseCommand):
    """Export relations report included relations between asset, user and
    licences."""
    help = textwrap.dedent(__doc__).strip()
    option_list = BaseCommand.option_list + (
        make_option(
            '--assets',
            action='store_true',
            dest='only_assets',
            default=False,
            help="Run command to get only Assets report without relations",
        ),
        make_option(
            '--licences',
            action='store_true',
            dest='only_licences',
            default=False,
            help="Run command to get Licences relations with assets and users",
        ),
        make_option(
            '--only-assigned-licences',
            action='store_true',
            dest='only_assigned_licences',
            default=False,
            help="Licences list show assigned items without base when only an "
            "item has assigned, in other case, shows same licence info",
        ),
        make_option(
            '--filter',
            type="choice",
            dest='filter_type',
            choices=["all", "dc", "back_office"],
            default="all",
            help="Filter items, all, dc, back_office",
        ),
    )

    def handle(self, *args, **options):
        only_licences = options['only_licences']
        only_assets = options['only_assets']
        filter_type = options['filter_type']
        only_assigned_licences = options['only_assigned_licences']
        if not any((only_licences, only_assets)):
            self.stdout.write(
                'Arguments required, type --help for more informations\n',
            )
        output = cStringIO.StringIO()
        writer = csv.writer(output)
        if only_assets and not only_licences:
            for row in get_assets_rows(filter_type):
                writer.writerow([smart_str(item) for item in row if item])
            self.stdout.write(output.getvalue())
        elif only_licences and not only_assets:
            for row in get_licences_rows(filter_type, only_assigned_licences):
                writer.writerow([smart_str(item) for item in row])
            self.stdout.write(output.getvalue())
