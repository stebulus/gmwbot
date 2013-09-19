from __future__ import division
from HTMLParser import HTMLParser

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

def p(x):
    print x
class cmpword(object):
    def __init__(self, word, callback=p):
        self._word = word
        self._callback = callback
    def __cmp__(self, other):
        self._callback(other)
        return cmp(self._word, other)

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
