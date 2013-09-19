from StringIO import StringIO

class mockhttpconn(object):
    """Mock of httplib.HTTPConnection, hosting a WSGI application."""
    def __init__(self, app):
        self._app = app
    def request(self, method, url, body=None):
        environ = {
            'REQUEST_METHOD': method,
            'SCRIPT_NAME': '',
            'PATH_INFO': url,
            'SERVER_NAME': 'example.com',
            'SERVER_PORT': '80',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'wsgi.version': (1,0),
            'wsgi.url_scheme': 'mock',
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
            }
        if body is None:
            body = ''
        environ['wsgi.input'] = StringIO(body)
        self._response = mockhttpresponse()
        def start_response(status, headers):
            code, reason = status.split(None, 1)
            self._response.status = code
            self._response.reason = reason
            self._response._headers = headers
            def write(data):
                body.append(data)
            return write
        body = []
        for chunk in self._app(environ, start_response):
            body.append(chunk)
        self._response._body = ''.join(body)
    def getresponse(self):
        resp = self._response
        self._response = None
        return resp

class mockhttpresponse(object):
    """Mock of httplib.HTTPResponse, generated by mockhttpconn."""
    def getheaders(self):
        return self._headers[:]
    def read(self, amt=None):
        if amt is None:
            return self._body
        else:
            ret = self._body[:amt]
            self._body = self._body[amt:]
            return ret

def dumpresponse(app, method, url, body=None):
    conn = mockhttpconn(app)
    conn.request(method, url, body)
    resp = conn.getresponse()
    print resp.status, resp.reason
    for hdr, val in resp.getheaders():
        print hdr + ':', val
    print
    print resp.read(),

_MOCKGMW_FIRSTFORM = """\
<p>This is a crude imitation of the Guess My Word CGI program.</p>
<form action="/~pahk/dictionary/guess.cgi" method="post" name="myform">
<div align="center">What is your guess?
<input type="text" name="guess" size="15" maxlength="15">
<input type="submit" value="Guess">
<input type="submit" name="result" value="I give up! Tell me!" value="no">
</div>
<input type="hidden" name="by" value="joon">
<input type="hidden" name="date" value="">
<input type="hidden" name="starttime" value="">
</form>
"""
def mockgmw(environ, start_response):
    """A WSGI application imitating "Guess my word!", for testing purposes."""
    if environ['REQUEST_METHOD'] == 'GET':
        start_response("200 OK", [])
        return [_MOCKGMW_FIRSTFORM]
