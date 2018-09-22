from socket import *
import datetime


s = socket(AF_INET, SOCK_STREAM)
print("init %s %s" % s.getsockname())
s.bind(("", 9000))
print("after bind operation %s %s" % s.getsockname())
s.listen(5)
while True:
    c, a = s.accept()
    print("Accepted socket is: \n%s" % c)
    print("Received connection from %s to %s" % (a, c.getsockname()))
    data = c.recv(10000)
    print("Recieved data %s" % data)
    version = "HTTP/1.1"
    responsecode = "200"
    response_string = "OK"
    response_code = " ".join([version, responsecode, response_string])
    headers = "Server: Simple Server\r\nDate: %s" % datetime.datetime.strftime(datetime.datetime.now(), "%d %b %Y %H:%M")
    body = "Hello %s you are %s" % (a[0], a[1])
    send_mesg = "%s\r\n%s\r\n\r\n%s" % (response_code, headers, body)
    print("Sended message %s" % send_mesg)
    send_bytes = send_mesg.encode("utf-8")
    c.send(send_bytes)
    c.close()
