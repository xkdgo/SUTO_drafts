import memcache
import time


class Store(object):
    def __init__(self, hostname="127.0.0.1",
                 port="11211",
                 retry=5,
                 timeout=1):
        self.hostname = "%s:%s" % (hostname, port)
        self.timeout = timeout
        self.retry = retry
        self.server = memcache.Client([self.hostname],
                                      dead_retry=self.retry,
                                      socket_timeout=self.timeout
                                      )

    def cache_set(self, key, value, expiry=600):
        for _ in range(self.retry):
            if self.is_server_connect() and \
                    self.server.set(key, value, expiry):
                return
            else:
                self.close_conn()
                time.sleep(0.03)
                continue
        self.server.servers[0].close_socket()

    def cache_get(self, key):
        for _ in range(self.retry):
            if not self.is_server_connect:
                time.sleep(0.03)
                continue
            ans = self.server.get(key)
            if ans:
                return ans
            else:
                time.sleep(0.03)
                continue
        self.server.servers[0].close_socket()
        return

    def get(self, key):
        for _ in range(self.retry):
            if self.is_server_connect():
                return self.server.get(key)
            else:
                time.sleep(0.03)
        raise RuntimeError("Server socket closed %s" % self.hostname)

    def close_conn(self):
        self.server.disconnect_all()

    def is_server_connect(self):
        return True if self.server.get_stats() else False
