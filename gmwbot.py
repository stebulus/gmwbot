from __future__ import division

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
