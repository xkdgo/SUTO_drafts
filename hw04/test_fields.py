import pytest
import api
from datetime import datetime
from datetime import timedelta



class TestFields:

    class FieldTester(api.Structure):
        charfield = api.CharField(nullable=True) #
        emailfield = api.EmailField(nullable=True)
        phonefield = api.PhoneField(nullable=True)
        birthdayfield = api.BirthDayField(nullable=True)
        genderfield = api.GenderField(nullable=True)
        datefield = api.DateField(nullable=True)
        client_ids = api.ClientIDsField(required=True)

    def setup_class(self):
        self.instance_fieldtester = self.FieldTester()
        print("\n=== TestFields - setup class ===\n")

    def teardown_class(self):
        print("\n=== TestFields - teardown class ===\n")

    def setup(self):

        print("TestFields - setup method")

    def teardown(self):
        print("TestFields - teardown method")

    @pytest.mark.parametrize(
        "cases", ["",
                  "тестовая строка",
                  "-1"])
    def test_char_field_ok(self, cases):
        self.instance_fieldtester.charfield = cases
        assert(self.instance_fieldtester.charfield == cases)

    @pytest.mark.parametrize(
        "cases", [-1,
                  {"a": 1},
                  ("qwe", "123")])
    def test_char_field_validatefail(self, cases):
        with pytest.raises(api.ValidationError):
            self.instance_fieldtester.charfield = cases

    @pytest.mark.parametrize(
        "cases", ["a@a.ru",
                  "mail@sub.domain.com",
                  "mail.mail@sub.domain.ru.com"
                  ])
    def test_email_field_ok(self, cases):
        self.instance_fieldtester.emailfield = cases
        assert(self.instance_fieldtester.emailfield == cases)

    @pytest.mark.parametrize(
        "cases", ["@",
                  -1,
                  "-1@m.com 123",
                  "-1@+1.ru",
                  {"a": 1},
                  ("qwe", "123")])
    def test_email_field_validatefail(self, cases):
        with pytest.raises(Exception):
            self.instance_fieldtester.emailfield = cases

    @pytest.mark.parametrize("cases", [
        70123456789,
        "70123456789",
        ""
    ])
    def test_phone_field_ok(self, cases):
        self.instance_fieldtester.phonefield = cases
        assert (self.instance_fieldtester.phonefield == cases)

    @pytest.mark.parametrize("cases", [
        "7----------",
        "7-1-3-5-7-9",
        "8",
        "89104563518",
        {70123456789},
        -79154321807
    ])
    def test_phone_field_fail(self, cases):
        with pytest.raises(api.ValidationError):
            self.instance_fieldtester.phonefield = cases

    @pytest.mark.parametrize("cases", [
        "09.10.2018",
        "31.12.2018"
    ])
    def test_datefield_ok(self, cases):
        self.instance_fieldtester.datefield = cases
        assert (self.instance_fieldtester.datefield == cases)

    @pytest.mark.parametrize("cases, exc_type, exc_msg", [
        ("bad format", api.ValidationError, "Invalid date format, DD.MM.YYYY"),
        ("10.10.10", api.ValidationError, "Invalid date format, DD.MM.YYYY"),
        ("08.10.18", api.ValidationError, "Invalid date format, DD.MM.YYYY"),
        ("08.10.20181", api.ValidationError, "Invalid date format, DD.MM.YYYY"),
    ])
    def test_datefield_bad_format(self, cases, exc_type, exc_msg):
        with pytest.raises(exc_type, message=exc_msg):
            self.instance_fieldtester.datefield = cases

    @pytest.mark.parametrize("cases", [
        "99.12.2018",
        "00.12.2018",
        "10.99.2018",
        "01.00.2018",
        "01.01.0000",
    ])
    def test_datefield_bad_date(self, cases):
        with pytest.raises(api.ValidationError):
            self.instance_fieldtester.datefield = cases

    @pytest.mark.parametrize("cases", [
        1,
        0,
        2,
        "",
    ])
    def test_genderfield_ok(self, cases):
        self.instance_fieldtester.genderfield = cases
        assert (self.instance_fieldtester.genderfield == cases)

    @pytest.mark.parametrize("cases", [
        "1",
        "0",
        "2",
        -1,
        3,
        1.5,
    ])
    def test_genderfield_fail(self, cases):
        with pytest.raises(api.ValidationError):
            self.instance_fieldtester.genderfield = cases

    @pytest.mark.parametrize("cases", [
        datetime.strftime(datetime.now() - timedelta(days=366), '%d.%m.%Y'),
        datetime.strftime(datetime.now() - timedelta(weeks=52*69), '%d.%m.%Y'),
    ])
    def test_birthday_ok(self, cases):
        self.instance_fieldtester.birthdayfield = cases
        assert (self.instance_fieldtester.birthdayfield == cases)

    @pytest.mark.parametrize("cases", [
        datetime.strftime(datetime.now(), '%d.%m.%Y'),
        datetime.strftime(datetime.now() + timedelta(days=366), '%d.%m.%Y'),
        datetime.strftime(datetime.now() - timedelta(weeks=53*70), '%d.%m.%Y'),
    ])
    def test_birthday_fail(self, cases):
        with pytest.raises(api.ValidationError):
            self.instance_fieldtester.birthdayfield = cases

    @pytest.mark.parametrize("cases", [
        [1, 2, 3],
        [0],
        [-600],
        [i for i in range(-100, 101)]
    ])
    def test_client_ids_ok(self, cases):
        self.instance_fieldtester.client_ids = cases
        assert (self.instance_fieldtester.client_ids == cases)

    @pytest.mark.parametrize("cases", [
        [],
        {1, 2, 3},
        ["0"],
        "w o r d".split(),
    ])
    def test_client_ids_fail(self, cases):
        with pytest.raises(api.ValidationError):
            self.instance_fieldtester.client_ids = cases

    def test_required_true_by_client_ids(self):
        test_required_true = self.instance_fieldtester.errors['client_ids']
        assert(
            test_required_true ==
            "required but not set"
        )

    def test_required_false_by_charfield(self):
        test_required_false = self.instance_fieldtester.errors.get('charfield', "OK")
        assert (
                test_required_false == "OK"
        )
