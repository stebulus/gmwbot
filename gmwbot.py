#!/usr/bin/env python
from __future__ import division
from datetime import datetime
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
        initp = GMWInitialParser()
        initp.feed(resp.content)
        self.wordtime = initp.wordtime
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

class ParagraphTextParser(HTMLParser):
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
class GMWResultParser(ParagraphTextParser):
    def handle_p(self, text):
        if text == 'You guessed it! well done.':
            self.result = 0
        elif text.startswith('My word is before '):
            self.result = -1
        elif text.startswith('My word is after '):
            self.result = 1
        elif text.startswith("I couldn't find "):
            self.result = 'nonword'
class GMWInitialParser(ParagraphTextParser):
    def handle_p(self, text):
        if text.startswith('This word was updated on '):
            self.wordtime = datetime.strptime(
                text.split('.',1)[0],
                'This word was updated on %H:%M Eastern, %m/%d/%Y')

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
            i, j = self.index(left)
            if i is True:
                lft = j+1
            else:
                lft = i+1
        if right is None:
            rt = len(self._words)-1
        else:
            i, j = self.index(right)
            rt = j+1
        for i,j in self._indexsearch(word, lft, rt):
            if i is True:
                yield (True, self._words[j])
            else:
                yield (self._words[i], self._words[j])
    def index(self, word):
        for i,j in self._indexsearch(word):
            pass
        if i is True:
            return i,j-1
        else:
            return i-1,j-1

def array(n):
    a = []
    for i in range(n):
        a.append([None]*n)
    return a
class obstsearcher(object):
    def __init__(self, words, intweights, extweights):
        n = len(words)
        p = [None] + intweights  # for 1-indexing as in Knuth
        q = extweights
        c = array(n+1)
        r = array(n+1)
        w = array(n+1)
        for i in range(0,n+1):
            c[i][i] = 0
            w[i][i] = q[i]
            r[i][i] = i
            for j in range(i+1,n+1):
                w[i][j] = w[i][j-1] + p[j] + q[j]
        for j in range(1,n+1):
            c[j-1][j] = w[j-1][j]
            r[j-1][j] = j
        for d in range(2,n+1):
            for j in range(d,n+1):
                i = j-d
                bestk = None
                bestc = None
                for k in range(r[i][j-1], r[i+1][j]+1):
                    currc = c[i][k-1] + c[k][j]
                    if bestk is None or currc < bestc:
                        bestk = k
                        bestc = currc
                c[i][j] = w[i][j] + bestc
                r[i][j] = bestk
        self._words = [None] + words + [None]
        self._c = c
        self._r = r
        self._w = w
    def cost(self,i,j):
        return self._c[i][j]
    def root(self,i,j):
        return self._r[i][j]
    def weight(self,i,j):
        return self._w[i][j]
    def __call__(self, word, left=None, right=None):
        # Following Knuth's setup, root(lft,rt) is the root of the
        # optimal binary search tree for internal weights p[lft+1]
        # through p[rt] inclusive and external weights q[lft] through
        # q[rt] inclusive, i.e., for words known to be strictly
        # between words[lft] and words[rt+1].
        bin = binarysearcher(self._words[1:-1])
        if left is None:
            lft = 0
        else:
            i,j = bin.index(left)
            if i is True:
                lft = j+1
            else:
                lft = j
        if right is None:
            rt = len(self._words)-2
        else:
            i,j = bin.index(right)
            rt = j
        yield (self._words[lft], self._words[rt+1])
        while lft < rt:
            mid = self.root(lft,rt)
            r = self._words[mid]
            c = cmp(word, r)
            if c == 0:
                yield (True, r)
                break
            elif c < 0:
                rt = mid-1
            else:
                lft = mid
            yield (self._words[lft], self._words[rt+1])
class obstsearcher_sjtbot2(object):
    def __init__(self, words, intweights, extweights):
        n = len(words)
        p = [None] + intweights  # for 1-indexing as in Knuth
        q = extweights
        c = array(n+1)
        r = array(n+1)
        w = array(n+1)
        for i in range(0,n+1):
            c[i][i] = 0
            w[i][i] = q[i]
            r[i][i] = i
            for j in range(i+1,n+1):
                w[i][j] = w[i][j-1] + p[j] + q[j]
        for j in range(1,n+1):
            c[j-1][j] = w[j-1][j]
            r[j-1][j] = j
        for d in range(2,n+1):
            for j in range(d,n+1):
                i = j-d
                bestk = None
                bestc = None
                for k in range(r[i][j-1], r[i+1][j]+1):
                    currc = c[i][k-1] + c[k][j]
                    if bestk is None or currc < bestc:
                        bestk = k
                        bestc = currc
                c[i][j] = w[i][j] + bestc
                r[i][j] = bestk
        self._words = [None] + words + [None]
        self._c = c
        self._r = r
        self._w = w
    def cost(self,i,j):
        return self._c[i][j]
    def root(self,i,j):
        return self._r[i][j]
    def weight(self,i,j):
        return self._w[i][j]
    def __call__(self, word, left=None, right=None):
        bin = binarysearcher(self._words[1:-1])
        if left is None:
            lft = 1
        else:
            i,j = bin.index(left)
            if i is True:
                lft = j+2
            else:
                lft = j+1
        if right is None:
            rt = len(self._words)-2
        else:
            i,j = bin.index(right)
            rt = j
        yield (self._words[lft-1], self._words[rt+1])
        while lft <= rt:
            mid = self.root(lft,rt)
            r = self._words[mid]
            c = cmp(word, r)
            if c == 0:
                yield (True, r)
                break
            elif c < 0:
                rt = mid-1
            else:
                lft = mid+1
            yield (self._words[lft-1], self._words[rt+1])
class delayedobst(object):
    def __init__(self, words, intweights, extweights,
            obstfactory=obstsearcher):
        self._words = words
        self._intweights = intweights
        self._extweights = extweights
        self._left = None
        self._right = None
        self._obstfactory = obstfactory
        self._obst = None
    def __call__(self, word, left=None, right=None):
        if left != self._left or right != self._right \
                or self._obst is None:
            bin = binarysearcher(self._words)
            if left is None:
                lft = 0
            else:
                i,j = bin.index(left)
                if i is True:
                    lft = j
                else:
                    lft = j-1
            if right is None:
                rt = len(self._words)-1
            else:
                i,j = bin.index(right)
                rt = j
            self._obst = self._obstfactory(self._words[lft:rt+1],
                self._intweights[lft:rt+1],
                self._extweights[lft:rt+2])
            self._left = left
            self._right = right
        for x in self._obst(word, left, right):
            yield x

class searchseq(object):
    def __init__(self, *searchers):
        self._searchers = searchers
    def __call__(self, word, left=None, right=None):
        for search in self._searchers:
            for a,b in search(word, left, right):
                yield (a,b)
                if a is True:
                    return
            left,right = a,b

def topobst(words, weights, topwords, obstfactory=obstsearcher):
    return searchseq(
        binarysearcher(topwords),
        delayedobst(words, weights, [0]*(len(weights)+1),
            obstfactory=obstfactory)
        )

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

class cmpcount(object):
    def __init__(self, cmpable):
        self._cmpable = cmpable
        self.count = 0
    def __cmp__(self, other):
        c = cmp(self._cmpable, other)
        self.count += 1
        return c

PAHK_URL='http://www.people.fas.harvard.edu/~pahk/dictionary/guess.cgi'

def strat_sjtbot1():
    words = []
    with open('8plus') as f:
        for line in f:
            words.append(line.strip().lower().split()[0])
    return binarysearcher(words)
def strat_sjtbot2():
    topwords = []
    with open('topwords') as fp:
        for line in fp:
            word = line.rstrip().split(None,1)[0]
            topwords.append(word)
    words = []
    weights = []
    with open('twlwordweight') as fp:
        for line in fp:
            word, weight = line.rstrip().split()
            words.append(word)
            weights.append(float(weight))
    return topobst(words, weights, topwords,
        obstfactory=obstsearcher_sjtbot2)
def strat_sjtbot3():
    topwords = []
    with open('topwords') as fp:
        for line in fp:
            word = line.rstrip().split(None,1)[0]
            topwords.append(word)
    words = []
    weights = []
    with open('twlwordweight') as fp:
        for line in fp:
            word, weight = line.rstrip().split()
            words.append(word)
            weights.append(float(weight))
    return topobst(words, weights, topwords)

strategies = dict(
    ((x[6:],globals()[x]) for x in globals()
        if x.startswith('strat_'))
    )

def usage():
    import sys
    strats = strategies.keys()
    strats.sort()
    strats = '|'.join(strats)
    print >>sys.stderr, 'usage:'
    print >>sys.stderr, '    %s (%s) (joon|mike)' % (sys.argv[0], strats)
    print >>sys.stderr, '    %s (%s) test WORD [WORD ...]' % (sys.argv[0], strats)
    sys.exit(2)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        usage()
    strategy = sys.argv[1]
    by = sys.argv[2]
    if strategy not in strategies \
            or (len(sys.argv) == 3 and by not in ['joon','mike']) \
            or (len(sys.argv) >= 4 and by != 'test'):
        usage()
    search = strategies[strategy]()

    if by == 'test':
        for word in sys.argv[3:]:
            cc = cmpcount(word)
            for x in search(cc):
                print x
            print word, cc.count
    else:
        import requests
        def request(*args, **kwargs):
            config = kwargs.setdefault('config',{})
            if 'verbose' not in config:
                config['verbose'] = sys.stderr
            return requests.request(*args, **kwargs)
        gmw = gmwclient(PAHK_URL, throttledfunc(60, request),
            by=by, leaderboardname=strategy)
        print 'wordtime:', gmw.wordtime.strftime('%Y-%m-%dT%H:%M')
        for x in search(gmw):
            print x
