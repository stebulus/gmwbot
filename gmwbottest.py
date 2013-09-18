class mockhttpconn(object):
    def __init__(self, app):
        self._app = app
    def request(self, method, url):
        environ = {
            }
        self._response = mockhttpresponse()
        def start_response(status, headers):
            code, reason = status.split(None, 1)
            self._response.status = code
            self._response.reason = reason
            self._response._headers = headers
        body = []
        for chunk in self._app(environ, start_response):
            body.append(chunk)
        self._response._body = ''.join(body)
    def getresponse(self):
        resp = self._response
        self._response = None
        return resp

class mockhttpresponse(object):
    def getheaders(self):
        return self._headers[:]
    def read(self, amt=None):
        if amt is None:
            return self._body
        else:
            ret = self._body[:amt]
            self._body = self._body[amt:]
            return ret
