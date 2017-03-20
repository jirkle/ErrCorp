# coding=UTF-8
import bz2
import re
import io
import urllib.request
import unitok
import WikiExtractor
import platform
from multiprocessing import Pool

context = None

def tokenize(text):
	"""Tokenizes given text"""

	out = io.StringIO()
	re_list = context["unitokConfig"].re_list
	tokens = unitok.tokenize_recursively(text, re_list)
	unitok.print_tokens(tokens, out, True, False)
	text = out.getvalue()
	out.close()
	return text

def exportToStream(page):
	"""Writes given errors to output stream"""
	stream = context["outputStream"]
	if context["outputFormat"] == "se":
		stream.write(tokenize("<doc n=\"%s\"><latest>" % page["name"]))
		latestRev = page["revisions"][-1]["*"]
		for line in latestRev:
			stream.write(tokenize("<s>%s</s>" % line))
		stream.write(tokenize("</latest><errors>"))
		for error in page["errors"]:
			stream.write(tokenize("<s>%s</s>" % error))
		stream.write(tokenize("</errors></doc>"))
		stream.flush()
	elif context["outputFormat"] == "txt":
		stream.write("Page: %s\n" % (page["name"]))
		latestRev = page["revisions"][-1]["*"]
		for line in latestRev:
			stream.write("%s\n" % line)
		stream.write("\nUnused errors\n")
		for error in page["errors"]:
			stream.write("%s\n" % error)			
		stream.write("\n")
		stream.flush()