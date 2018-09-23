import os
import selectors
import datetime
import mimetypes
import re


class Message:
    def __init__(self, selector, sock, addr, rootdir):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b''
        self._send_buffer = b''
        self.method = None
        self.uri = None
        self.request = None
        self.response_created = False

        self.request_processor = HTTPRequestProcessor(rootdir)

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

    def _create_response(self, request):
        return self.request_processor.create_response_for_message(request)


class HTTPRequestProcessor:

    def __init__(self, rootdir):
        self.responsecode = {"200": "OK",
                             "500": "Internal sever Error",
                             "405": "Method Unsupported",
                             "403": "Access Denied",
                             "404": "Resource Not Fund",
                             }
        self.rootdir = rootdir
        # Date, Server, Content‐Length, Content‐Type, Connection
        self.headers = dict(Server='OTUServer')
        self.version = "HTTP/1.1"
        self.supported_methods = ["GET", "HEAD"]
        self.uri_pattern = re.compile(r"^\/[\/\.a-zA-Z0-9\-\_\%]*$")

    def create_response_for_message(self, request):
        try:
            processed_str = request.decode("utf-8")
        except UnicodeDecodeError:
            return self.create_response_not_200("500")
        method, uri, *_ = processed_str.split(" ")
        if method not in self.supported_methods:
            return self.create_response_not_200("405")
        if method.upper() == "GET":
            response = self.validate_uri(method, uri)
        else:
            response = self.validate_uri(method, uri)
        return response

    def create_response_not_200(self, responsecode):
        self._flush_headers()
        send_mesg = self._format_response_head(responsecode)
        print("Sended message %s" % send_mesg)
        with open(f"error_templates/{responsecode}.html", 'rb') as error_file:
            body = error_file.read()
        self.headers['Content-Length'] = self.get_file_size(f"error_templates/{responsecode}.html")
        self.headers['Content‐Type'] = mimetypes.guess_type(f"error_templates/{responsecode}.html")[0]
        self.headers['Connection'] = "close"
        response = send_mesg.encode("utf-8") + body
        return response

    def create_response_200(self, method, uri="error_templates/404.html"):
        self._flush_headers()
        body = b""
        self.headers['Content-Length'] = self.get_file_size(uri)
        self.headers['Content‐Type'] = mimetypes.guess_type(uri)[0]
        self.headers['Connection'] = "close"
        if method == "GET":
            with open(uri, "rb") as error_file:
                body = error_file.read()
        send_mesg = self._format_response_head("200")
        response = send_mesg.encode("utf-8") + body
        return response

    def validate_uri(self, method, uri):
        try:
            if "../" in uri:
                return self.create_response_not_200("403")
            # Split ? and #
            uri = uri.split("#")[0].split("?")[0]
            if not self.uri_pattern.match(uri):
                return self.create_response_not_200("403")
            # understand spaces и %XX in filename
            uri = self.unquote_uri(uri)
            uri = os.path.join(self.rootdir, uri.lstrip('/'))
            if os.path.isdir(uri):
                uri = os.path.join(uri, 'index.html')
            if not os.path.isfile(uri):
                return self.create_response_not_200("404")
            # print(uri)
            response = self.create_response_200(method=method, uri=uri)
            return response
        except Exception as e:
            print(repr(e))
            return self.create_response_not_200("500")

    def _format_response_head(self, responsecode):
        response_string = self.responsecode[responsecode]
        version = self.version
        response_code_header_str = f'{" ".join([version, responsecode, response_string])}\r\n'
        headers = self._create_headers()
        if headers:
            response_code_header_str = f'{response_code_header_str}{headers}\r\n\r\n'
        return response_code_header_str

    def _create_headers(self):
        self.headers['Date'] = self._create_timestamp()
        temp_headers = [f'{key}: {value}' for key, value in self.headers.items()]
        headers = "\r\n".join(temp_headers)
        return headers

    @staticmethod
    def _create_timestamp():
        return datetime.datetime.strftime(datetime.datetime.now(), "%d %b %Y %H:%M")

    def _flush_headers(self):
        self.headers = dict(Server='OTUServer')

    @staticmethod
    def get_file_size(uri):
        return os.path.getsize(uri)

    @staticmethod
    def unquote_uri(uri):
        # from urllib.parse lightly changed
        _hexdig = '0123456789ABCDEFabcdef'
        _hextobyte = None
        if _hextobyte is None:
            _hextobyte = {
                ("%" + a + b).encode(): bytes([int(a + b, 16)])
                for a in _hexdig for b in _hexdig
            }
        uri_encoded = uri.encode()
        for match, sub in _hextobyte.items():
            uri_encoded = uri_encoded.replace(match, sub)
        return uri_encoded.decode(errors="replace")
