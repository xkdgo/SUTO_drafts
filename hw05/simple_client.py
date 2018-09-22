import http.client
c = http.client.HTTPConnection("127.0.0.1", 9000)
c.putrequest("GET", "/index.html")
c.putheader("Someheader", "Somevalue")
c.endheaders()
r = c.getresponse()
data = r.read()
print(data)
c.close()
