from __future__ import division
from HTMLParser import HTMLParser
from time import time, sleep
from urllib import urlencode

class Error(Exception):
    pass

class gmwclient(object):
    def __init__(self, conn):
        self.conn = conn
        resp = self.conn.getresponse()
        self.form = htmlform.fromstr(resp.read())
        self.lower = None
        self.upper = None
    def __cmp__(self, other):
        for i,(typ,nam,val) in enumerate(self.form.controls):
            if nam == 'guess':
                self.form.controls[i] = (typ,nam,str(other))
                break
        self.conn.request(*self.form.submit())
        resp = self.conn.getresponse()
        body = resp.read()
        result = GMWResultParser()
        result.feed(body)
        self.form = htmlform.fromstr(body)
        lower = formget01(self.form, 'lower')
        upper = formget01(self.form, 'upper')
        if result.result is None:
            raise Error('could not interpret reply from GMW')
        if result.result > 0 and (self.lower is None or other > self.lower):
            self.lower = other
        if result.result < 0 and (self.upper is None or other < self.upper):
            self.upper = other
        if result.result != 0 and (lower != self.lower or upper != self.upper):
            raise Error('expected range %r-%r, not %r-%r'
                % (self.lower, self.upper, lower, upper))
        return result.result

class GMWResultParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self._p = 0
        self._data = []
        self.result = None
    def handle_starttag(self, tag, attrs):
        if tag == 'p':
            self._p += 1
    def handle_data(self, data):
        if self._p > 0:
            self._data.append(data)
    def handle_endtag(self, tag):
        if tag == 'p':
            self._p -= 1
            if self._p == 0:
                self.handle_p(''.join(self._data))
                self._data = []
    def handle_p(self, text):
        if text == 'You guessed it! well done.':
            self.result = 0
        elif text.startswith('My word is before '):
            self.result = -1
        elif text.startswith('My word is after '):
            self.result = 1

class throttledfunc(object):
    def __init__(self, mingap, func):
        self._mingap = mingap
        self._nexttime = None
        self._func = func
    def __call__(self, *args, **kwargs):
        if self._nexttime is not None:
            now = time()
            if self._nexttime > now:
                sleep(self._nexttime-now)
        self._nexttime = time() + self._mingap
        return self._func(*args, **kwargs)
def throttled(mingap):  # for use as decorator
    def throttle(func):
        return throttledfunc(mingap, func)
    return throttle

class binarysearcher(object):
    def __init__(self, words):
        self._words = [None] + words + [None]
    def __call__(self, word):
        lft = 0
        rt = len(self._words)-1
        while lft+1 < rt:
            mid = (lft+rt)//2
            c = cmp(word, self._words[mid])
            if c == 0:
                return self._words[mid]
            elif c < 0:
                rt = mid
            else:
                lft = mid
        else:
            return None

class HTMLFormParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.controls = []
        self.method = 'GET'
    def handle_starttag(self, tag, attrs):
        if tag == 'form':
            for n,v in attrs:
                n = n.lower()
                if n == 'action':
                    self.action = v
                elif n == 'method':
                    self.method = v.upper()
        if tag == 'input':
            typ = None
            nam = None
            val = None
            for n,v in attrs:
                n = n.lower()
                if n == 'type':
                    typ = v
                elif n == 'name':
                    nam = v
                elif n == 'value':
                    val = v
            self.controls.append((typ,nam,val))

class htmlform(object):
    @classmethod
    def fromstr(cls, s):
        parser = HTMLFormParser()
        parser.feed(s)
        parser.close()
        return cls(parser.action, parser.method, parser.controls)

    def __init__(self, action, method, controls):
        self.action = action
        self.method = method
        self.controls = controls

    def values(self, name):
        return [val for typ,nam,val in self.controls if nam == name]

    def submit(self):
        dataset = []
        for typ,nam,val in self.controls:
            if nam is not None:
                dataset.append((nam,val))
        dataset = urlencode(dataset)
        if self.method == 'POST':
            return (self.method, self.action,
                dataset,
                {'Content-Type': 'application/x-www-form-urlencoded',
                 'Accept': '*'})
        elif self.method == 'GET':
            return (self.method, self.action + '?' + dataset)
        else:
            raise ValueError('unknown form submission method %r' % (self.method,))

def formget01(form, key):
    lst = form.values(key)
    if len(lst) > 1:
        raise Error("more than one value for %r" % (key,))
    if lst:
        return lst[0]
    else:
        return None

def formget1(form, key):
    lst = form.values(key)
    if lst is None:
        raise Error("no value for %r" % (key,))
    if len(lst) > 1:
        raise Error("more than one value for %r" % (key,))
    return lst[0]
