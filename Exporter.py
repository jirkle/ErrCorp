# coding=UTF-8
import io
import unitok

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
		output = ("<doc n=\"%s\"><latest>" % page["name"])
		latestRev = page["revisions"][-1]["*"]
		for line in latestRev:
			output += ("<s>%s</s>" % line)
		output += "</latest><errors>"
		for error in page["errors"]:
			output += ("<s>%s</s>" % error)
		output += "</errors></doc>"
		stream.write(tokenize(output))
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