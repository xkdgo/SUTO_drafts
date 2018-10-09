import pytest
from _pytest.monkeypatch import MonkeyPatch
from pytest_mock import mocker
import store


class TestSuite:

    def setup_class(self):
        print("\n=== TestSuite - setup class ===\n")
        self.context = {}
        self.headers = {}
        self.store = store.Store()
        self.monkeypatch = MonkeyPatch()

    def teardown_class(self):
        print("\n=== TestSuite - teardown class ===\n")

    def setup(self):
        print("TestSuite - setup method")

    def teardown(self):
        print("TestSuite - teardown method")

    def test_cache_set_with_connected_server(self, mocker):
        self.monkeypatch.setattr("memcache.Client.get_stats", lambda x: True)
        self.monkeypatch.setattr("memcache.Client.set", lambda self, key, value, expiry: True)
        test_mocker = mocker.patch("time.sleep")
        self.store.cache_set("a", "b", expiry=600)
        assert(test_mocker.call_count == 0)

    def test_cache_set_with_disconnected_server(self, mocker):
        self.monkeypatch.setattr("memcache.Client.get_stats", lambda x: False)
        test_mocker = mocker.patch("time.sleep")
        self.store.cache_set("a", "b", expiry=600)
        assert(test_mocker.call_count == self.store.retry)

    def test_cache_set_with_connected_server_but_failed_operation(self, mocker):
        self.monkeypatch.setattr("memcache.Client.get_stats", lambda x: True)
        self.monkeypatch.setattr("memcache.Client.set", lambda self, key, value, expiry: False)
        test_mocker = mocker.patch("time.sleep")
        self.store.cache_set("a", "b", expiry=600)
        assert(test_mocker.call_count == self.store.retry)

    def test_cache_get_with_disconnected_server(self, mocker):
        self.monkeypatch.setattr("memcache.Client.get_stats", lambda x: False)
        test_mocker = mocker.patch("time.sleep")
        self.store.cache_get("a")
        assert(test_mocker.call_count == self.store.retry)

    def test_cache_get_with_connected_server_but_failed_operation(self, mocker):
        self.monkeypatch.setattr("memcache.Client.get_stats", lambda x: True)
        test_mocker = mocker.patch("time.sleep")
        self.store.cache_get("a")
        assert(test_mocker.call_count == self.store.retry)

    def test_cache_get_ok_operation(self, mocker):
        self.monkeypatch.setattr("memcache.Client.get_stats", lambda x: True)
        self.monkeypatch.setattr("memcache.Client.get", lambda self, key: 'b')
        test_mocker = mocker.patch("time.sleep")
        ans = self.store.cache_get("a")
        assert(ans == 'b')
        assert(test_mocker.call_count == 0)

    def test_get_ok_operation(self, mocker):
        self.monkeypatch.setattr("memcache.Client.get_stats", lambda x: True)
        self.monkeypatch.setattr("memcache.Client.get", lambda self, key: 'b')
        test_mocker = mocker.patch("time.sleep")
        assert (self.store.get("key") == 'b')
        assert (test_mocker.call_count == 0)

    def test_get_failed_operation(self, mocker):
        self.monkeypatch.setattr("memcache.Client.get_stats", lambda x: False)
        test_mocker = mocker.patch("time.sleep")
        with pytest.raises(RuntimeError):
            self.store.get("key")
        assert (test_mocker.call_count == self.store.retry)

