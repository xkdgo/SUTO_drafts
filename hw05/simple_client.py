import http.client
c = http.client.HTTPConnection("127.0.0.1", 80)
# c.putrequest("GET", "/")
c.putrequest("GET", "/httptest/splash.css")
# c.putrequest("HEAD", "/index.html")
c.putheader("Someheader", "Somevalue")
c.endheaders()
r = c.getresponse()
data = r.read()
print(data)
c.close()
