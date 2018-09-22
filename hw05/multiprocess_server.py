#!/usr/bin/env python3

import sys
import socket
import selectors
import types
import datetime

sel = selectors.DefaultSelector()


def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    print('accepted connection from', addr)
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b'', outb=b'')
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            data.outb += recv_data
        else:
            print('closing connection to', data.addr)
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            print('echoing', repr(data.outb), 'to', data.addr)
            processed_str = data.outb.decode("utf-8")
            method, uri, *_ = processed_str.split(" ")
            version = "HTTP/1.1"
            responsecode = "200"
            response_string = "OK"
            response_code = " ".join([version, responsecode, response_string])
            headers = "Server: MultiprocessServer\r\nDate: %s" % datetime.datetime.strftime(datetime.datetime.now(), "%d %b %Y %H:%M")
            # body = "Hello %s you are %s" % (a[0], a[1])
            send_mesg = "%s\r\n%s\r\n\r\n" % (response_code, headers)
            print("Sended message %s" % send_mesg)
            data.outb = send_mesg.encode("utf-8") + method.lower().encode("utf-8")
            print(data.outb)
            while data.outb:
                sent = sock.send(data.outb)  # Should be ready to write
                data.outb = data.outb[sent:]
            sel.unregister(sock)
            sock.close()


host, port = "", 9000
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.bind((host, port))
lsock.listen(128)
print('listening on', (host, port))
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj)
            else:
                service_connection(key, mask)
except KeyboardInterrupt:
    print('caught keyboard interrupt, exiting')
finally:
    sel.close()
