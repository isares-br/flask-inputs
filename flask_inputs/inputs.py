import functools
import collections
from itertools import chain
from future.utils import iteritems

from werkzeug.datastructures import MultiDict

from wtforms.form import BaseForm
from wtforms.fields import Field

from flask import request


def validate_input(Input):
    """Validate Input decorator
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            inputs = Input(request)
            if not inputs.validate():
                return {'error': inputs.errors}, 400
            return func(*args, **kwargs)
        return wrapper
    return decorator


class Inputs(object):
    #: flask.Request attributes available for validation
    valid_attrs = ['args', 'form', 'values', 'cookies',
                   'headers', 'json', 'rule']
    
    # Error message templates
    error_messages = {}

    def __init__(self, request):
        """Base class for input validation. Subclass to add validators.

        :param request: flask.Request object to validate.
        """

        #: List of errors from all validators.
        self.errors = []

        self._request = request
        self._forms = dict()

        for name in dir(self):
            if not name.startswith('_') and name not in ['errors', 'validate', 'valid_attrs']:
                input = getattr(self, name)
                fields = dict()

                if isinstance(input, dict):
                    for field, validators in iteritems(input):
                        fields[field] = Field(validators=validators)
                elif isinstance(input, collections.abc.Iterable):
                    fields['_input'] = Field(validators=input)

                self._forms[name] = BaseForm(fields)

    def _get_values(self, attribute, coerse=True):
        """Compatability function to return MultiDict objects with values from
        a flask.Request object.

        :param attribute: Request attribute to return values for.
        :param coerse: Return single input with raw data.

        :returns: werkzeug.datastructures.MultiDict
        """
        if attribute in self.valid_attrs:
            if attribute == 'rule':
                ret = self._request.view_args
            else:
                ret = getattr(self._request, attribute)

            if coerse:
                return MultiDict(ret)
            else:
                return MultiDict(dict(_input=ret))

    def validate(self):
        """Validate incoming request data. Returns True if all data is valid.
        Adds each of the validator's error messages to Inputs.errors if not valid.

        :returns: Boolean
        """
        success = True

        for attribute, form in iteritems(self._forms):
            if '_input' in form._fields:
                form.process(self._get_values(attribute, coerse=False))
            else:
                form.process(self._get_values(attribute))

            if not form.validate():
                success = False
                self.errors += chain(*form.errors.values())

        if success:
            success = self._validate()
        return success

    def _validate(self):
        """Override this method to add custom validation.

        :returns: Boolean
        """
        return True

    def _fail(self, key):
        """Add to errors if validation fails.
        """
        self.errors.append(self.error_messages[key])
