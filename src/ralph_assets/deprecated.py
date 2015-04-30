# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.db.models.signals import post_save
from django.dispatch import receiver

from ralph.discovery.models_device import DeviceModel
from ralph_assets.models_dc_assets import Rack, DeprecatedRalphRack


@receiver(post_save, sender=Rack)
def update_deprecated_rack(sender, instance, **kwargs):
    def create_deprecated_rack():
        models = DeviceModel.objects.filter(
            type=DeprecatedRalphRack._model_type
        )
        if models:
            deprecated_data_center = instance.data_center.deprecated_ralph_dc
            deprecated_rack = DeprecatedRalphRack.create_deprecated_object(
                name=instance.name,
                parent=deprecated_data_center,
                model=models[0],
            )
            deprecated_rack.save()
            instance.deprecated_ralph_rack = deprecated_rack
            instance.save()

    if kwargs['created'] and not instance.deprecated_ralph_rack:
        create_deprecated_rack()
    else:
        if instance.deprecated_ralph_rack:
            instance.deprecated_ralph_rack.name = instance.name
            instance.deprecated_ralph_rack.save()
        else:
            create_deprecated_rack()
