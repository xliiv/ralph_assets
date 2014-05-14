# -*- coding: utf-8 -*-
import datetime
import django.db
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'AssetModel', fields ['name']
        db.delete_unique('ralph_assets_assetmodel', ['name'])

        # Removing index on 'AssetModel', fields ['name']
        try:
            db.delete_index('ralph_assets_assetmodel', ['name'])
        except django.db.utils.DatabaseError:
            pass

    def backwards(self, orm):
        # Adding unique constraint on 'AssetModel', fields ['name']
        db.create_unique('ralph_assets_assetmodel', ['name'])


    models = {
        'account.profile': {
            'Meta': {'object_name': 'Profile'},
            'activation_token': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '40', 'blank': 'True'}),
            'birth_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'company': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'cost_center': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'blank': 'True'}),
            'country': ('django.db.models.fields.PositiveIntegerField', [], {'default': '153'}),
            'department': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'employee_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'gender': ('django.db.models.fields.PositiveIntegerField', [], {'default': '2'}),
            'home_page': (u'dj.choices.fields.ChoiceField', [], {'unique': 'False', 'primary_key': 'False', 'db_column': 'None', 'blank': 'False', u'default': '1', 'null': 'False', '_in_south': 'True', 'db_index': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_active': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'manager': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'blank': 'True'}),
            'nick': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '30', 'blank': 'True'}),
            'profit_center': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'blank': 'True'}),
            'time_zone': ('django.db.models.fields.FloatField', [], {'default': '1.0'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ralph_assets.action': {
            'Meta': {'object_name': 'Action'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75', 'db_index': 'True'})
        },
        'ralph_assets.asset': {
            'Meta': {'object_name': 'Asset'},
            'attachments': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['ralph_assets.Attachment']", 'null': 'True', 'blank': 'True'}),
            'barcode': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'cache_version': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': "orm['account.Profile']", 'blank': 'True', 'null': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'delivery_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'deprecation_rate': ('django.db.models.fields.DecimalField', [], {'default': '25', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'device_info': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['ralph_assets.DeviceInfo']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'force_deprecation': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'invoice_no': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'loan_end_date': ('django.db.models.fields.DateField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'model': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ralph_assets.AssetModel']", 'on_delete': 'models.PROTECT'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': "orm['account.Profile']", 'blank': 'True', 'null': 'True'}),
            'niw': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'note': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'blank': 'True'}),
            'office_info': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['ralph_assets.OfficeInfo']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'order_no': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'owner'", 'null': 'True', 'to': "orm['auth.User']"}),
            'part_info': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['ralph_assets.PartInfo']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'production_use_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'production_year': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'property_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ralph_assets.AssetOwner']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'provider_order_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'remarks': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'blank': 'True'}),
            'request_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'service_name': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ralph_assets.Service']", 'null': 'True', 'blank': 'True'}),
            'slots': ('django.db.models.fields.FloatField', [], {'default': '0', 'max_length': '64'}),
            'sn': ('django.db.models.fields.CharField', [], {'max_length': '200', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'source': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'support_period': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'support_price': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'support_type': ('django.db.models.fields.CharField', [], {'max_length': '150', 'blank': 'True'}),
            'support_void_reporting': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'db_index': 'True'}),
            'task_url': ('django.db.models.fields.URLField', [], {'max_length': '2048', 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'user'", 'null': 'True', 'to': "orm['auth.User']"}),
            'warehouse': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ralph_assets.Warehouse']", 'on_delete': 'models.PROTECT'})
        },
        'ralph_assets.assetcategory': {
            'Meta': {'object_name': 'AssetCategory'},
            'cache_version': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': "orm['account.Profile']", 'blank': 'True', 'null': 'True'}),
            'is_blade': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': "orm['account.Profile']", 'blank': 'True', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "u'children'", 'null': 'True', 'to': "orm['ralph_assets.AssetCategory']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'primary_key': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'type': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'ralph_assets.assethistorychange': {
            'Meta': {'object_name': 'AssetHistoryChange'},
            'asset': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['ralph_assets.Asset']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'device_info': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['ralph_assets.DeviceInfo']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'field_name': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'new_value': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255'}),
            'office_info': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['ralph_assets.OfficeInfo']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'old_value': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255'}),
            'part_info': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['ralph_assets.PartInfo']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['auth.User']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'})
        },
        'ralph_assets.assetmanufacturer': {
            'Meta': {'object_name': 'AssetManufacturer'},
            'cache_version': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': "orm['account.Profile']", 'blank': 'True', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': "orm['account.Profile']", 'blank': 'True', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75', 'db_index': 'True'})
        },
        'ralph_assets.assetmodel': {
            'Meta': {'object_name': 'AssetModel'},
            'cache_version': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ralph_assets.AssetCategory']", 'null': 'True', 'blank': 'True'}),
            'cores_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': "orm['account.Profile']", 'blank': 'True', 'null': 'True'}),
            'height_of_device': ('django.db.models.fields.FloatField', [], {'default': '0', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manufacturer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ralph_assets.AssetManufacturer']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': "orm['account.Profile']", 'blank': 'True', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '75'}),
            'power_consumption': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'type': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'})
        },
        'ralph_assets.assetowner': {
            'Meta': {'object_name': 'AssetOwner'},
            'cache_version': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75', 'db_index': 'True'})
        },
        'ralph_assets.attachment': {
            'Meta': {'object_name': 'Attachment'},
            'cache_version': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'uploaded_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'ralph_assets.coaoemos': {
            'Meta': {'object_name': 'CoaOemOs'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75', 'db_index': 'True'})
        },
        'ralph_assets.deviceinfo': {
            'Meta': {'object_name': 'DeviceInfo'},
            'cache_version': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'rack': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'ralph_device_id': ('django.db.models.fields.IntegerField', [], {'default': 'None', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'u_height': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'u_level': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'})
        },
        'ralph_assets.importproblem': {
            'Meta': {'object_name': 'ImportProblem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'severity': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'ralph_assets.licence': {
            'Meta': {'object_name': 'Licence'},
            'accounting_id': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'asset_type': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'assets': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['ralph_assets.Asset']", 'symmetrical': 'False'}),
            'attachments': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['ralph_assets.Attachment']", 'null': 'True', 'blank': 'True'}),
            'cache_version': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'invoice_no': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'licence_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ralph_assets.LicenceType']", 'on_delete': 'models.PROTECT'}),
            'manufacturer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ralph_assets.AssetManufacturer']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'niw': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'number_bought': ('django.db.models.fields.IntegerField', [], {}),
            'order_no': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "u'children'", 'null': 'True', 'to': "orm['ralph_assets.Licence']"}),
            'price': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '10', 'decimal_places': '2', 'blank': 'True'}),
            'property_of': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ralph_assets.AssetOwner']", 'null': 'True', 'on_delete': 'models.PROTECT'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'sn': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'software_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ralph_assets.SoftwareCategory']", 'on_delete': 'models.PROTECT'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'valid_thru': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'})
        },
        'ralph_assets.licencehistorychange': {
            'Meta': {'object_name': 'LicenceHistoryChange'},
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'field_name': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['ralph_assets.Licence']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'new_value': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255'}),
            'old_value': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['auth.User']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'})
        },
        'ralph_assets.licencetype': {
            'Meta': {'object_name': 'LicenceType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75', 'db_index': 'True'})
        },
        'ralph_assets.officeinfo': {
            'Meta': {'object_name': 'OfficeInfo'},
            'cache_version': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'coa_number': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'coa_oem_os': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ralph_assets.CoaOemOs']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imei': ('django.db.models.fields.CharField', [], {'max_length': '18', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'license_key': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'purpose': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'})
        },
        'ralph_assets.partinfo': {
            'Meta': {'object_name': 'PartInfo'},
            'barcode_salvaged': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'cache_version': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'device': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'device'", 'null': 'True', 'to': "orm['ralph_assets.Asset']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'source_device': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'source_device'", 'null': 'True', 'to': "orm['ralph_assets.Asset']"})
        },
        'ralph_assets.reportodtsource': {
            'Meta': {'object_name': 'ReportOdtSource'},
            'cache_version': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75', 'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'}),
            'template': ('django.db.models.fields.files.FileField', [], {'max_length': '100'})
        },
        'ralph_assets.service': {
            'Meta': {'object_name': 'Service'},
            'cache_version': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'cost_center': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75', 'db_index': 'True'}),
            'profit_center': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'blank': 'True'})
        },
        'ralph_assets.softwarecategory': {
            'Meta': {'object_name': 'SoftwareCategory'},
            'asset_type': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75', 'db_index': 'True'})
        },
        'ralph_assets.transition': {
            'Meta': {'object_name': 'Transition'},
            'actions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['ralph_assets.Action']", 'symmetrical': 'False'}),
            'cache_version': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'from_status': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75', 'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'}),
            'to_status': ('django.db.models.fields.PositiveSmallIntegerField', [], {})
        },
        'ralph_assets.transitionshistory': {
            'Meta': {'ordering': "[u'-created']", 'object_name': 'TransitionsHistory'},
            'affected_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'affected user'", 'to': "orm['auth.User']"}),
            'assets': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['ralph_assets.Asset']", 'symmetrical': 'False'}),
            'cache_version': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logged_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'logged user'", 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'report_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'report_filename': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'transition': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ralph_assets.Transition']"}),
            'uid': ('django.db.models.fields.CharField', [], {'max_length': '36'})
        },
        'ralph_assets.warehouse': {
            'Meta': {'object_name': 'Warehouse'},
            'cache_version': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': "orm['account.Profile']", 'blank': 'True', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'+'", 'on_delete': 'models.SET_NULL', 'default': 'None', 'to': "orm['account.Profile']", 'blank': 'True', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '75', 'db_index': 'True'})
        }
    }

    complete_apps = ['ralph_assets']
