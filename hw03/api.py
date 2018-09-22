#!/usr/bin/env/python3
# -*- coding: utf-8 -*-

import abc
import json
import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import OrderedDict
import random

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
        self.not_null = []
        self.errors = {}
        for key, val in kwargs.items():
            try:
                setattr(self, key, val)
            except ValidationError as err:
                self.errors.update({key: str(err)})
            self.base_fields.append(key)
            if val:
                self.not_null.append(key)
        print(self.base_fields)
        self._validate()

    def _validate(self):
        for item in self._fields:
            if item.required and item.name not in self.base_fields:
                self.errors.update({item.name: "required but not set"})


class Nullable(Descriptor):
    def __init__(self, *args, nullable=True, **kwargs):
        self.nullable = nullable
        super().__init__(*args, **kwargs)

    def _validate(self, instance, value):
        if not self.nullable and not value:
            raise ValidationError("%s Value must be not null" % self.name)


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


class DictType(Typed):
    ty = dict
    pass


class CharField(Required, Nullable, CharType):
    pass


class ArgumentsField(Required, Nullable, DictType):
    pass


class EmailField(CharField):
    def _validate(self, instance, value):
        if value:
            if "@" not in value:
                raise ValidationError("%s invalid email address" % self.name)


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
                raise ValidationError("%s must be 0, 1 or 2" % self.name)


class ClientIDsField(Required, Nullable, Typed):
    ty = list

    def _validate(self, instance, value):
        super()._validate(instance, value)
        for item in value:
            if not isinstance(item, int):
                raise ValidationError("All items in array %s must be int" % (
                    self.name
                ))


class ClientsInterestsRequest(Structure):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)

    def compile_cid_interest(self):
        result_cid_interests = {}
        for item in self.client_ids:
            result_cid_interests[item] = self.get_interests()
        return result_cid_interests

    @staticmethod
    def get_interests():
        interests = ["cars", "pets", "travel", "hi-tech", "sport", "music", "books", "tv", "cinema", "geek", "otus"]
        return random.sample(interests, 2)


class OnlineScoreRequest(Structure):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def _validate(self):
        super()._validate()
        arg_pairs = [
            ("phone", "email"),
            ("first_name", "last_name"),
            ("gender", "birthday")
        ]
        if not any(all(name in self.not_null for name in field) for field in arg_pairs):
            self.errors["arguments"] = "Missing values in pairs of required arguments"

    def get_score(self):
        score = 0
        if self.phone:
            score += 1.5
        if self.email:
            score += 1.5
        if self.birthday and self.gender:
            score += 1.5
        if self.first_name and self.last_name:
            score += 0.5
        return score


class MethodRequest(Structure):
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
        digest_str = datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT
        digest = hashlib.sha512(digest_str.encode("utf-8")).hexdigest()
        print(digest)
    else:
        digest_str = request.account + request.login + SALT
        digest = hashlib.sha512(digest_str.encode("utf-8")).hexdigest()
        print(digest)
    if digest == request.token:
        return True
    return False


def clients_interests_handler(ctx, metreq):
    client_int_r = ClientsInterestsRequest(**metreq.arguments)
    if client_int_r.errors:
        return client_int_r.errors, INVALID_REQUEST
    ctx["nclients"] = len(client_int_r.client_ids)
    return client_int_r.compile_cid_interest(), OK


def online_score_handler(ctx, metreq):
    osr = OnlineScoreRequest(**metreq.arguments)
    if osr.errors:
        return osr.errors, INVALID_REQUEST
    ctx["has"] = osr.not_null
    score = 42 if metreq.is_admin else osr.get_score()
    return {"score": score}, OK


def method_handler(request, ctx, store):
    method_router = {
        "clients_interests": clients_interests_handler,
        "online_score": online_score_handler
    }
    metreq = MethodRequest(**request["body"])
    if metreq.errors:
        return metreq.errors, INVALID_REQUEST
    if not check_auth(metreq):
        return "Forbidden", FORBIDDEN
    try:
        response, code = method_router[request['body'].get("method", "")](ctx, metreq)
    except KeyError:
        return "unknown method", INVALID_REQUEST
    print(request['body'].get("method", ""))  # clients_interests
    print(type(request['body'].get("arguments", "")))
    # response, code = None, None
    # response, code = "OK", 200
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
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
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
