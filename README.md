gmwbot
======

A bot to play [Guess My Word!][1]

The game is binary search in a word list for a word chosen daily by
Joon Pahk and his comrade Mike.  The main challenge for a computer
player is to model Joon's and Mike's preferences for words.  My current
bot, [`sjtbot3`](./sjtbot3), uses an ad hoc model combining
frequency data from Google Ngrams (as a proxy for commonness/obscurity)
and some manual tweaks to avoid plurals and other derived forms.
(A better model is in progress.)

[1]: http://www.people.fas.harvard.edu/~pahk/dictionary/guess.cgi
