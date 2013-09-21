from StringIO import StringIO
from urlparse import parse_qs

class mockhttpconn(object):
    """Mock of httplib.HTTPConnection, hosting a WSGI application."""
    def __init__(self, app):
        self._app = app
    def request(self, method, url, body=None, headers=None):
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
        if headers is not None:
            for k,v in headers.items():
                k = 'HTTP_' + k.replace('-', '_').upper()
                environ[k] = environ.get(k,'') + v
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

def dumpresponse(app, method, url, body=None, headers=None):
    conn = mockhttpconn(app)
    conn.request(method, url, body, headers)
    resp = conn.getresponse()
    print resp.status, resp.reason
    for hdr, val in resp.getheaders():
        print hdr + ':', val
    print
    print resp.read(),

_MOCKGMW_FIRSTFORM = """\
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

_MOCKGMW_INTERMED = """\
<div align="center">What is your guess?
<input type="text" name="guess" size="15" maxlength="15">
<input type="submit" value="Guess">
<input type="submit" name="result" value="I give up! Tell me!" value="no">
</div>
<input type="hidden" name="by" value="%(by)s">
<input type="hidden" name="date" value="">
<input type="hidden" name="starttime" value="%(starttime)s">
"""

_MOCKGMW_WINNER = """\
<div align="center">Enter your name for the daily leaderboard (optional):
<input type="text" name="guess" size="30" maxlength="30">
<input type="submit" value="Submit">
</div>
<input type="hidden" name="result" value="winner">
<input type="hidden" name="numguesses" value="%(numguesses)d">
<input type="hidden" name="guesstime" value="6815">
<input type="hidden" name="by" value="%(by)s">
<input type="hidden" name="hist" value="%(hist)s">
"""

def _hidden(name, value):
    return '<input type="hidden" name="%s" value="%s">\n' % (name, value)

class mockgmw():
    """A WSGI application imitating "Guess my word!", for testing purposes."""
    def __init__(self):
        self.time = 0
    def __call__(self, environ, start_response):
        if environ['REQUEST_METHOD'] == 'GET':
            start_response("200 OK", [])
            return [_MOCKGMW_FIRSTFORM]
        elif environ['REQUEST_METHOD'] == 'POST':
            try:
                dataset = parse_qs(environ['wsgi.input'].read())
                guesses = dataset.get('guesses',[])
                lower = get01(dataset, 'lower')
                upper = get01(dataset, 'upper')
                guess = get1(dataset, 'guess')
                by = get1(dataset, 'by')
                starttime = get01(dataset, 'starttime')
                if starttime is None:
                    if guesses:
                        raise BadRequest("previous guesses, but no starttime")
                    starttime = self.time
            except BadRequest, e:
                start_response("400 Bad Request",
                    [('Content-Type', 'text/plain')])
                return ["bad request: ", e.msg]
            guesses.append(guess)
            c = cmp(self.word, guess)
            if c > 0 and (lower is None or lower < guess):
                lower = guess
            if c < 0 and (upper is None or upper > guess):
                upper = guess

            start_response("200 OK", [('Content-Type', 'text/html')])
            output = []
            output.append('<p>Your guesses so far:</p>\n')
            output.append('<ol>\n')
            for g in guesses:
                if g == upper:
                    color = 'red'
                elif g == lower:
                    color = 'blue'
                else:
                    color = 'black'
                output.append('<li><span style="color:%(color)s">%(guess)s</span></li>\n' % {'guess': g, 'color': color})
            output.append('</ol>\n')
            output.append('<p align="center">')
            if c == 0:
                output.append('You guessed it! well done.')
            else:
                output.append('My word is ')
                if c < 0:
                    output.append('before')
                else:
                    output.append('after')
                output.append(' %s.' % (guess,))
            output.append('</p>\n')
            output.append('<form action="/~pahk/dictionary/guess.cgi" method="post" name="myform">\n')
            if c == 0:
                output.append(_MOCKGMW_WINNER % {
                    'numguesses': len(guesses),
                    'by': by,
                    'hist': '-'.join(guesses),
                    })
            else:
                output.append(_MOCKGMW_INTERMED % {
                    'starttime': starttime,
                    'by': by,
                    })
                for x in guesses:
                    output.append(_hidden('guesses',x))
                if lower is not None:
                    output.append(_hidden('lower',lower))
                if upper is not None:
                    output.append(_hidden('upper',upper))
            output.append('</form>\n')
            return output

class BadRequest(Exception):
    def __init__(self, msg):
        self.msg = msg

def get01(dataset, key):
    lst = dataset.get(key, [])
    if len(lst) > 1:
        raise BadRequest("more than one value for %r" % (key,))
    if lst:
        return lst[0]
    else:
        return None

def get1(dataset, key):
    lst = dataset.get(key, None)
    if lst is None:
        raise BadRequest("no value for %r" % (key,))
    if len(lst) > 1:
        raise BadRequest("more than one value for %r" % (key,))
    return lst[0]

class cmplog(object):
    def __init__(self, cmpable):
        self._cmpable = cmpable
    def __cmp__(self, other):
        c = cmp(self._cmpable, other)
        if c < 0:
            op = '<'
        elif c == 0:
            op = '='
        else:
            op = '>'
        print '? %s %s' % (op, other)
        return c
