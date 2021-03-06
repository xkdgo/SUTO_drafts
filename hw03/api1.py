#!/usr/bin/env python
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


def make_signature(names):
    return Signature(
        Parameter(name,
                  Parameter.POSITIONAL_OR_KEYWORD)
        for name in names)


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

    def __delete__(self, instance):
        del instance.__dict__[self.name]


class Nullable(Descriptor):
    def __init__(self, *args, nullable, **kwargs):
        self.nullable = nullable
        super().__init__(*args, **kwargs)

    def __set__(self, instance, value):
        if not value and not self.nullable:
            raise ValueError("Value must be not null %s %s %s" % (
                self, instance, value))
        super().__set__(instance, value)


class StructMeta(type):
    @classmethod
    def __prepare__(mcs, name, bases):
        return OrderedDict()

    def __new__(mcs, name, bases, clsdict):
        fields = [key for key, val in clsdict.items() if
                  isinstance(val, Descriptor)]
        for name in fields:
            clsdict[name].name = name

        clsobj = super().__new__(mcs, name, bases, clsdict)
        sig = make_signature(fields)
        setattr(clsobj, '__signature__', sig)
        return clsobj


class Structure(metaclass=StructMeta):
    _fields = []

    def __init__(self, *args, **kwargs):
        bound = self.__signature__.bind(*args, **kwargs)
        for name, val in bound.arguments.items():
            setattr(self, name, val)


class CharField(Nullable):
    pass



class ArgumentsField:
    pass


class EmailField(CharField):
    pass


class PhoneField:
    pass


class DateField:
    pass


class BirthDayField:
    pass


class GenderField:
    pass


class ClientIDsField:
    pass


# class CommonRequest:
#     def __init__(self, **kwargs):
#         for key, val in kwargs.items():
#             self.key = val

class ClientsInterestsRequest:
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest:
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)


class MethodRequest:
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512(datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).hexdigest()
    else:
        digest = hashlib.sha512(request.account + request.login + SALT).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx, store):
    print ("Yep Im HERE EEEEEEEEEEEEEE")
    print (request['body'].get("method", "")) #clients_interests

    print("CTX %s" % ctx) # CTX {'request_id': 'bb4904697c58434f8c825dfd1e6d9cc0'}
    print(store) # None
    response, code = OK, 200
    # response, code = None, None
    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        data_string = ""
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            data_string = data_string.decode("utf-8")
            request = json.loads(data_string)
            print("RRRRRRRRRRRRRRRRRRRRRR %s" % request)
        except:
            code = BAD_REQUEST

        if request:
            print("IM HERE !!!!!!!!!!!!!!!!!!!!!!!")
            path = self.path.strip("/")
            print("PATHHHHHHHHHHHHHHH = %s" % path) # method
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            print("Router RRRRRRR = %s" % self.router)
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write((json.dumps(r)).encode("utf-8"))
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
