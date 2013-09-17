#!/bin/sh
(find ${1:-tests} -name script |sed 's,/script$,,' |sort |xargs ./runtest || echo fail) 2>/dev/null
