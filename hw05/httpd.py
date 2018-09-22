#!/usr/bin/env python3

import sys
import socket
import selectors
import traceback
import lib_for_http_server as lib_helper


class MultiprocessSocketServer:

    def __init__(self, host="", port=8080, workers=1):
        self.host = host
        self.port = port
        self.sel = selectors.DefaultSelector()
        self.workers = workers

    def serve_forever(self):
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Avoid bind() exception: OSError: [Errno 48] Address already in use
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lsock.bind((self.host, self.port))
        lsock.listen()
        print('listening on', (self.host, self.port))
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, data=None)
        try:
            while True:
                events = self.sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        self.accept_wrapper(key.fileobj)
                    else:
                        message = key.data
                        try:
                            message.process_events(mask)
                        except Exception:
                            print('main: error: exception for',
                                  f'{message.addr}:\n{traceback.format_exc()}')
                            message.close()
        except KeyboardInterrupt:
            print('caught keyboard interrupt, exiting')
        finally:
            self.terminate()

    def accept_wrapper(self, sock):

        conn, addr = sock.accept()  # Should be ready to read
        print('accepted connection from', addr)
        conn.setblocking(False)
        message = lib_helper.Message(self.sel, conn, addr)
        self.sel.register(conn, selectors.EVENT_READ, data=message)

    def terminate(self):
        self.sel.close()


server = MultiprocessSocketServer()
server.serve_forever()

