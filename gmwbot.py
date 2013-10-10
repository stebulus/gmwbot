#!/usr/bin/env python
from __future__ import division
from HTMLParser import HTMLParser
from time import time, sleep
from urllib import urlencode
from urlparse import urljoin

class Error(Exception):
    pass
class NonwordError(Error):
    def __init__(self, nonword, response):
        Error.__init__(self,
            "gmw server says '%s' is not a word" % nonword)
        self.nonword = nonword
        self.response = response

class gmwclient(object):
    def __init__(self, url, request, by='joon', leaderboardname=None):
        self._request = request
        resp = self._request('GET', url, params={'by': by})
        self.form = htmlform.fromstr(resp.content, baseurl=resp.url)
        self.lower = None
        self.upper = None
        self.leaderboardname = leaderboardname
    def __cmp__(self, other):
        for i,(typ,nam,val) in enumerate(self.form.controls):
            if nam == 'guess':
                self.form.controls[i] = (typ,nam,str(other))
                break
        resp = self.form.submit(self._request)
        result = GMWResultParser()
        result.feed(resp.content)
        self.form = htmlform.fromstr(resp.content, baseurl=resp.url)
        lower = formget01(self.form, 'lower')
        upper = formget01(self.form, 'upper')
        if result.result is None:
            raise Error('could not interpret reply from GMW')
        if result.result == 'nonword':
            raise NonwordError(other, resp)
        if result.result > 0 and (self.lower is None or other > self.lower):
            self.lower = other
        if result.result < 0 and (self.upper is None or other < self.upper):
            self.upper = other
        if result.result != 0 and (lower != self.lower or upper != self.upper):
            raise Error('expected range %r-%r, not %r-%r'
                % (self.lower, self.upper, lower, upper))
        if result.result == 0 and self.leaderboardname is not None:
            for i,(typ,nam,val) in enumerate(self.form.controls):
                if nam == 'guess':
                    self.form.controls[i] = (typ,nam,str(self.leaderboardname))
                    break
            self.form.submit(self._request)
            self.form = None
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
        elif text.startswith("I couldn't find "):
            self.result = 'nonword'

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
    def _indexsearch(self, word, left=None, right=None):
        if left is None:
            left = 0
        if right is None:
            right = len(self._words)-1
        yield (left, right)
        while left+1 < right:
            mid = (left+right)//2
            c = cmp(word, self._words[mid])
            if c == 0:
                yield (True, mid)
                break
            elif c < 0:
                right = mid
            else:
                left = mid
            yield (left, right)
    def __call__(self, word, left=None, right=None):
        if left is None:
            lft = 0
        else:
            i, j = last(self._indexsearch(left))
            if i is True:
                lft = j
            else:
                lft = i
        if right is None:
            rt = len(self._words)-1
        else:
            i, j = last(self._indexsearch(right))
            rt = j
        for i,j in self._indexsearch(word, lft, rt):
            if i is True:
                yield (True, self._words[j])
            else:
                yield (self._words[i], self._words[j])

def last(it):
    for x in it:
        pass
    return x

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
    def fromstr(cls, s, baseurl=None):
        parser = HTMLFormParser()
        parser.feed(s)
        parser.close()
        return cls(parser.action, parser.method, parser.controls,
            baseurl=baseurl)

    def __init__(self, action, method, controls, baseurl=None):
        self.action = urljoin(baseurl, action)
        self.method = method
        self.controls = controls

    def values(self, name):
        return [val for typ,nam,val in self.controls if nam == name]

    def submit(self, f):
        dataset = {}
        for typ,nam,val in self.controls:
            if nam is not None:
                dataset.setdefault(nam,[]).append(val)
        if self.method == 'GET':
            return f(self.method, self.action, params=dataset)
        elif self.method == 'POST':
            return f(self.method, self.action,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': '*'},
                data=urlencode(dataset,doseq=True))
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

PAHK_URL='http://www.people.fas.harvard.edu/~pahk/dictionary/guess.cgi'

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2 or sys.argv[1] not in ['joon','mike']:
        print >>sys.stderr, 'usage: %s (joon|mike)' % sys.argv[0]
        sys.exit(2)
    by = sys.argv[1]

    words = []
    with open('8plus') as f:
        for line in f:
            words.append(line.strip().lower().split()[0])
    search = binarysearcher(words)

    import requests
    def request(*args, **kwargs):
        config = kwargs.setdefault('config',{})
        if 'verbose' not in config:
            config['verbose'] = sys.stderr
        return requests.request(*args, **kwargs)
    gmw = gmwclient(PAHK_URL, throttledfunc(60, request),
        by=by, leaderboardname='sjtbot1')
    for x in search(gmw):
        print x
