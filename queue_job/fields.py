# -*- coding: utf-8 -*-
# copyright 2016 Camptocamp
# license agpl-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import json
from datetime import datetime, date

import dateutil
import dateutil.parser

from openerp import fields, models
from openerp import osv

import simplejson


class job_serialized(osv.fields._column):
    """ A field able to store an arbitrary python data structure.

        Note: only plain components allowed.
    """
    _type = 'job_serialized'
    __slots__ = []

    def _symbol_set_struct(val):
        return simplejson.dumps(val)

    def _symbol_get_struct(self, val):
        return simplejson.loads(val or '{}')

    _symbol_c = '%s'
    _symbol_f = _symbol_set_struct
    _symbol_set = (_symbol_c, _symbol_f)
    _symbol_get = _symbol_get_struct

    def __init__(self, *args, **kwargs):
        kwargs['_prefetch'] = kwargs.get('_prefetch', False)
        super(job_serialized, self).__init__(*args, **kwargs)


osv.fields.job_serialized = job_serialized
models.FIELDS_TO_PGTYPES[job_serialized] = 'text'


class JobSerialized(fields.Field):
    """ Serialized fields provide the storage for sparse fields. """
    type = 'job_serialized'
    column_type = ('text', 'text')

    def convert_to_column(self, value, record):
        return json.dumps(value, cls=JobEncoder)

    def convert_to_cache(self, value, record, validate=True):
        return value


fields.JobSerialized = JobSerialized


class JobEncoder(json.JSONEncoder):
    """ Encode Odoo recordsets so that we can later recompose them """

    def default(self, obj):
        if isinstance(obj, models.BaseModel):
            return {'_type': 'odoo_recordset',
                    'model': obj._name,
                    'ids': obj.ids,
                    'uid': obj.env.uid,
                    }
        elif isinstance(obj, datetime):
            return {'_type': 'datetime_isoformat',
                    'value': obj.isoformat()}
        elif isinstance(obj, date):
            return {'_type': 'date_isoformat',
                    'value': obj.isoformat()}
        return json.JSONEncoder.default(self, obj)


class JobDecoder(json.JSONDecoder):
    """ Decode json, recomposing recordsets """

    def __init__(self, *args, **kwargs):
        env = kwargs.pop('env')
        super(JobDecoder, self).__init__(
            object_hook=self.object_hook, *args, **kwargs
        )
        assert env
        self.env = env

    def object_hook(self, obj):
        if '_type' not in obj:
            return obj
        type_ = obj['_type']
        if type_ == 'odoo_recordset':
            model = self.env[obj['model']]
            if obj.get('uid'):
                model = model.sudo(obj['uid'])
            return model.browse(obj['ids'])
        elif type_ == 'datetime_isoformat':
            return dateutil.parser.parse(obj['value'])
        elif type_ == 'date_isoformat':
            return dateutil.parser.parse(obj['value']).date()
        return obj
