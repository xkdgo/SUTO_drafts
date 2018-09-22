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
from inspect import Parameter, Signature


# def make_signature(names):
#     return Signature(
#         Parameter(name,
#                   Parameter.POSITIONAL_OR_KEYWORD)
#         for name in names)


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

    # def __delete__(self, instance):
    #     del instance.__dict__[self.name]


class StructMeta(type):
    @classmethod
    def __prepare__(mcs, name, bases):
        return OrderedDict()

    def __new__(mcs, name, bases, namespace):
        fields = []
        for key, val in namespace.items():
            if isinstance(val, Descriptor):
                fields.append(val)

        cls = super().__new__(mcs, name, bases, namespace)
        cls._fields = fields
        return cls


# class Structure(metaclass=StructMeta):
#
#     def __init__(self, data=None):
#         if data is None:
#             return
#         data = json.loads(data)
#         if not isinstance(data, dict):
#             raise ValueError("Invalid JSON")
#         for key, val in data.items():
#             setattr(self, key, val)
#             print(key)
#             print(val)

class Structure(metaclass=StructMeta):

    def __init__(self, **kwargs):
        # if data is None:
        #     return
        # data = json.loads(data)
        # if not isinstance(data, dict):
        #     raise ValueError("Invalid JSON")
        self.base_fields = []
        for key, val in kwargs.items():
            setattr(self, key, val)
            print(key)
            print(val)
        for field_name, value in kwargs.items():
            setattr(self, field_name, value)
            self.base_fields.append(field_name)
        print(self.base_fields)
        self._validate()

    def _validate(self):
        for item in self._fields:
            if item.required and item not in self.base_fields:
                print(item.name, "required but not set")
            # print(item.name, "nullable %s" % item.nullable)
#     def to_json(self):
#         data = {}
#         for key, _ in self.__dict__.items():
#             if key in self._fields:
#                 data[key] = getattr(self, key)
#         return json.dumps(data)


# class StructMeta(type):
#     @classmethod
#     def __prepare__(mcs, name, bases):
#         return OrderedDict()
#
#     def __new__(mcs, name, bases, clsdict):
#         fields = [key for key, val in clsdict.items() if
#                   isinstance(val, Descriptor)]
#         print(fields)
#         # print(bases)
#         for name in fields:
#             clsdict[name].name = name
#         clsobj = super().__new__(mcs, name, bases, dict(clsdict))
#         sig = make_signature(fields)
#         setattr(clsobj, '__signature__', sig)
#         return clsobj
#
#
# class Structure(metaclass=StructMeta):
#     # _fields = []
#
#     def __init__(self, *args, **kwargs):
#         # print (args)
#         bound = self.__signature__.bind_partial(*args, **kwargs)
#         for name, val in bound.arguments.items():
#             setattr(self, name, val)
#


class Nullable(Descriptor):
    def __init__(self, *args, nullable=False, **kwargs):
        self.nullable = nullable
        super().__init__(*args, **kwargs)

    # def __set__(self, instance, value):
    #     if not value and not self.nullable:
    #         raise ValueError("Value must be not null")
    #     super().__set__(instance, value)
    def _validate(self, instance, value):
        if not value and not self.nullable:
            raise ValueError("Value must be not null")


class Required(Descriptor):
    def __init__(self, *args, required=False, nullable=False, **kwargs):
        self.required = required
        self.nullable = nullable
        # print(args)
        # print ("!!!", kwargs)
        super().__init__(*args, **kwargs)




class CharField(Required, Nullable):
    pass


class Test(Structure):
    test = CharField("test", nullable=True, required=True)
    tset = CharField("tset", nullable=False, required=True)



class Test1(Structure):
    test = CharField("test", nullable=False, required=True)
    tset = CharField("tset", nullable=True, required=True)



o = Test()
# c = Test(test=None)

d = Test()

o = Test(test='123')

# for item in o._fields:
#     print(item.name, "nullable %s" % item.nullable)

c = Test1(test="321")
# for item in c._fields:
#     print(item.name, "nullable %s" % item.nullable)

b = Test1(test=None)