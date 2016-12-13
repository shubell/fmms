#!/usr/bin/python2.5
import os
dirs = ""
for nm in os.listdir('../po/'):
	(fn, ext) = os.path.splitext(nm)
	if ext == '.po':
		dirs = "%s %s" % (dirs, fn)

print dirs
