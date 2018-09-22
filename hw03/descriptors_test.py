#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import abc
import json
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler


SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}

from collections import OrderedDict


class ValidationError(Exception):
    pass


class Descriptor:
    def __init__(self, name=None):
        self.name = name

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            return instance.__dict__[self.name]

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value
        self._validate(instance, value)

    def _validate(self, instance, value):
        pass


class StructMeta(type):
    @classmethod
    def __prepare__(mcs, name, bases):
        return OrderedDict()

    def __new__(mcs, name, bases, namespace):
        fields = []
        for key, val in namespace.items():
            if isinstance(val, Descriptor):
                fields.append(val)
                namespace[key].name = key
        cls = super().__new__(mcs, name, bases, namespace)
        cls._fields = fields
        return cls


class Structure(metaclass=StructMeta):

    def __init__(self, **kwargs):
        self.base_fields = []
        self.errors = {}
        for key, val in kwargs.items():
            try:
                setattr(self, key, val)
            except ValidationError as err:
                self.errors.update({key: err})
            self.base_fields.append(key)
            print(key)
            print(val)

        print(self.base_fields)
        self._validate()
        print(self.errors)

    def _validate(self):
        for item in self._fields:
            if item.required and item.name not in self.base_fields:
                self.errors.update({item.name: "required but not set"})


class Nullable(Descriptor):
    def __init__(self, *args, nullable=False, **kwargs):
        self.nullable = nullable
        super().__init__(*args, **kwargs)

    def _validate(self, instance, value):
        if not self.nullable and not value:
            raise ValidationError("value of %s must be filled" % self.name)


class Required(Descriptor):
    def __init__(self, *args, required=False, **kwargs):
        self.required = required
        super().__init__(*args, **kwargs)


class Typed(Descriptor):
    ty = object

    def __set__(self, instance, value):
        super().__set__(instance, value)
        if not isinstance(value, self.ty):
            raise ValidationError("%s Expected  %s" % (self.name, self.ty))


class CharType(Typed):
    ty = str
    pass


class CharField(Required, Nullable, CharType):
    pass


class EmailField(CharField):
    def _validate(self, instance, value):
        if value:
            if "@" not in value:
                raise ValidationError("%s invalid email address" % self.name)


class DictType(Typed):
    ty = dict
    pass


class ArgumentsField(Required, Nullable, DictType):
    pass


class PhoneField(Required, Nullable):
    def _validate(self, instance, value):
        super()._validate(instance, value)
        if value:
            if not isinstance(value, int) and not isinstance(value, str):
                raise ValidationError("PhoneField must be str or int")
            if not str(value).startswith("7"):
                raise ValidationError(
                    "Incorrect phone number format, should be 7XXXXXXXXXX")
            if len(str(value)) != 11:
                raise ValidationError("Phone number must be 11 digits")


class DateField(Required, Nullable):
    def _validate(self, instance, value):
        if value:
            super()._validate(instance, value)
            try:
                datetime.datetime.strptime(value, '%d.%m.%Y')
            except ValueError:
                raise ValidationError("Invalid date format, DD.MM.YYYY")


class BirthDayField(DateField):
    def _validate(self, instance, value):
        if value:
            super()._validate(instance, value)
            date = datetime.datetime.strptime(value, '%d.%m.%Y')
            timedelta = datetime.datetime.now().year - date.year
            if timedelta > 70 or timedelta <= 0:
                raise ValidationError("Incorrect birth day")



class GenderField(Required, Nullable):
    def _validate(self, instance, value):
        if value:
            if value not in GENDERS:
                raise ValidationError("Gender must be 0, 1 or 2")


class ClientIDsField(Required, Nullable, Typed):
    ty = list

    def _validate(self, instance, value):
        super()._validate(instance, value)
        for item in value:
            if not isinstance(item, int):
                raise ValidationError("All items in array %s must be int" % (
                    self.name
                ))


class Test(Structure):
    test = CharField(nullable=False, required=True)
    tset = CharField(nullable=True, required=True)
    email = EmailField(nullable=True, required=True)
    argument = ArgumentsField(nullable=True, required=True)
    phone = PhoneField(nullable=True, required=True)
    date = DateField(nullable=True, required=True)
    birthday = BirthDayField(nullable=True, required=True)
    cid = ClientIDsField(required=True)


class Test1(Structure):
    test = CharField(nullable=True, required=True)
    tset = CharField(nullable=True, required=True)



# o = Test()
# c = Test(test=None)

# d = Test()

o = Test(test=12, argument=[], phone='7912621140')

# for item in o._fields:
#     print(item.name, "nullable %s" % item.nullable)

c = Test1(test="321")
# for item in c._fields:
#     print(item.name, "nullable %s" % item.nullable)

# b = Test(email='aa')
