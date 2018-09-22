import sys
import selectors
import json
import io
import struct
import datetime
from collections import OrderedDict


class Message:

    def __init__(self, selector, sock, addr):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b''
        self._send_buffer = b''
        self.method = None
        self.uri = None
        self.request = None
        self.response_created = False
        self.responsecode = {"200": "OK",
                             "500": "Internal sever Error",
                             "405": "405_description",
                             "403": "403_description",
                             "404": "404_description",
                             }
        self.version = "HTTP/1.1"
        self.supported_methods = ["GET", "HEAD"]
        #Date, Server, Content‐Length, Content‐Type, Connection
        self.headers = dict(Server='OTUServer')

    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
        if mode == 'r':
            events = selectors.EVENT_READ
        elif mode == 'w':
            events = selectors.EVENT_WRITE
        elif mode == 'rw':
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError(f'Invalid events mask mode {repr(mode)}.')
        self.selector.modify(self.sock, events, data=self)

    def _read(self):
        try:
            # Should be ready to read
            data = self.sock.recv(4096)
        except BlockingIOError:
            # Resource temporarily unavailable (errno EWOULDBLOCK)
            pass
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError('Peer closed.')

    def _write(self):
        if self._send_buffer:
            print('sending', repr(self._send_buffer), 'to', self.addr)
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                # Resource temporarily unavailable (errno EWOULDBLOCK)
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]
                # Close when the buffer is drained. The response has been sent.
                if sent and not self._send_buffer:
                    self.close()

    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        self._read()
        if self.request is None:
            self.process_request()

    def write(self):
        if self.request:
            if not self.response_created:
                self.create_response()
        self._write()

    def close(self):
        print('closing connection to', self.addr)
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print(f'error: selector.unregister() exception for',
                  f'{self.addr}: {repr(e)}')

        try:
            self.sock.close()
        except OSError as e:
            print(f'error: socket.close() exception for',
                  f'{self.addr}: {repr(e)}')
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None

    def process_request(self):
        self.request = self._recv_buffer
        print("request = %s" % self.request)
        self._set_selector_events_mask('w')

    def create_response(self):
        response = self._create_response(self.request)
        message = response
        self.response_created = True
        self._send_buffer += message

    def _create_dummy_response(self, uri="abracadabra"):
        send_mesg = self.format_response_head("200")
        print("Sended message %s" % send_mesg)
        response = send_mesg.encode("utf-8") + uri.encode("utf-8")
        return response

    def _create_response(self, request):
        try:
            processed_str = request.decode("utf-8")
        except UnicodeDecodeError:
            send_mesg = self.format_response_head("500")
            print("Sended message %s" % send_mesg)
            response = send_mesg.encode("utf-8")
            return response
        method, uri, *_ = processed_str.split(" ")
        if method not in self.supported_methods:
            send_mesg = self.format_response_head("405")
            print("Sended message %s" % send_mesg)
            response = send_mesg.encode("utf-8") + method.upper().encode("utf-8")
            return response
        if method.upper() == "GET":
            response = self._create_dummy_response(uri=uri)
        else:
            response = self._create_dummy_response(uri=uri)
        return response

    def create_headers(self, responsecode):
        self.headers['Date'] = self.create_timestamp()
        temp_headers = [f'{key}: {value}' for key, value in self.headers.items()]
        headers = "\r\n".join(temp_headers)
        return headers

    def format_response_head(self, responsecode):
        response_string = self.responsecode[responsecode]
        version = self.version
        response_code = f'{" ".join([version, responsecode, response_string])}\r\n'
        headers = self.create_headers(responsecode)
        if headers:
            response_code = f'{response_code}{headers}\r\n\r\n'
        return response_code

    @staticmethod
    def create_timestamp():
        return datetime.datetime.strftime(datetime.datetime.now(), "%d %b %Y %H:%M")
