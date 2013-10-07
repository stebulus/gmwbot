from StringIO import StringIO
from urllib import urlencode
from urlparse import parse_qs
from requests.structures import CaseInsensitiveDict

class mockrequests(object):
    """A mock version of requests, sending all requests to a WSGI application."""
    def __init__(self, app):
        self._app = app
    def request(self, method, url, params=None, data=None, headers=None):
        resp = self.Response()
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
        if params is not None:
            environ['QUERY_STRING'] = urlencode(params, doseq=True)
        try:
            items = data.items()
        except AttributeError:
            if data is None:
                data = ''
        else:
            data = urlencode(items, doseq=True)
        environ['wsgi.input'] = StringIO(data)
        if headers is not None:
            for k,v in headers.items():
                k = 'HTTP_' + k.replace('-', '_').upper()
                environ[k] = environ.get(k,'') + v
        def start_response(status, headers):
            resp.status_code = int(status[:3])
            resp.headers = CaseInsensitiveDict(headers)
            def write(data):
                chunks.append(data)
            return write
        chunks = []
        for chunk in self._app(environ, start_response):
            chunks.append(chunk)
        resp.content = ''.join(chunks)
        return resp
    class Response(object):
        pass

def dumpresponse(app, method, url, params=None, data=None, headers=None):
    req = mockrequests(app)
    resp = req.request(method, url, params=params, data=data, headers=headers)
    print resp.status_code
    headers = resp.headers.items()
    headers.sort()
    for hdr, val in headers:
        print hdr + ':', val
    print
    print resp.content,

class mockgmw():
    """A WSGI application imitating "Guess my word!", for testing purposes."""
    _FIRSTFORM = """\
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

    _INTERMED = """\
<div align="center">What is your guess?
<input type="text" name="guess" size="15" maxlength="15">
<input type="submit" value="Guess">
<input type="submit" name="result" value="I give up! Tell me!" value="no">
</div>
<input type="hidden" name="by" value="%(by)s">
<input type="hidden" name="date" value="">
<input type="hidden" name="starttime" value="%(starttime)s">
"""

    _WINNER = """\
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

    _LEADERBOARD = """\
<h3>Correct solvers for today:</h3>
<table border=1>
<tr><th>Rank</th><th>Name</th><th>Guesses</th><th>Time</th><th>History (mouse over)</th></tr>
<tr><td>1</td><td>You</td><td>1</td><td>0:00</td><td title="rankle">Guess history</td></tr>
</table>
"""

    def _hidden(self, name, value):
        return '<input type="hidden" name="%s" value="%s">\n' % (name, value)

    def __init__(self, logfile=None):
        self.time = 0
        self._replaceupper = None
        self._replacelower = None
        self._logfile = logfile
    def _log(self, msg):
        if self._logfile is not None:
            print >>self._logfile, msg
    def __call__(self, environ, start_response):
        if environ['REQUEST_METHOD'] == 'GET':
            self._log('GMW: initial request')
            start_response("200 OK", [])
            return [self._FIRSTFORM]
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
                self._log('GMW: 400 Bad Request: %s' % e.msg)
                start_response("400 Bad Request",
                    [('Content-Type', 'text/plain')])
                return ["bad request: ", e.msg]
            if dataset.get('result',[]) == ['winner']:
                self._log('GMW: leaderboard submission: %s' % (guess,))
                return [self._LEADERBOARD]
            else:
                self._log('GMW: guess: %s' % (guess,))
                guesses.append(guess)
                c = cmp(self.word, guess)
                if c > 0 and (lower is None or lower < guess):
                    lower = guess
                if c < 0 and (upper is None or upper > guess):
                    upper = guess

                if self._replacelower is not None:
                    lower = self._replacelower
                    self._replacelower = None
                if self._replaceupper is not None:
                    upper = self._replaceupper
                    self._replaceupper = None

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
                    output.append(self._WINNER % {
                        'numguesses': len(guesses),
                        'by': by,
                        'hist': '-'.join(guesses),
                        })
                else:
                    output.append(self._INTERMED % {
                        'starttime': starttime,
                        'by': by,
                        })
                    for x in guesses:
                        output.append(self._hidden('guesses',x))
                    if lower is not None:
                        output.append(self._hidden('lower',lower))
                    if upper is not None:
                        output.append(self._hidden('upper',upper))
                output.append('</form>\n')
                return output

    def replaceupper(self, upper):
        self._replaceupper = upper
    def replacelower(self, lower):
        self._replacelower = lower

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
