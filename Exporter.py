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
	outputStreamFull = context["outputStreamFull"]
	outputStreamOrphans = context["outputStreamOrphans"]
	if context["outputFormat"] == "se":
		output = ("<doc n=\"%s\">" % page["name"])
		latestRev = page["revisions"][-1]["*"]
		for line in latestRev:
			if line != "":
				output += ("<s>%s</s>" % line)
		output += "</doc>"
		outputStreamFull.write(tokenize(output))
		output = ("<doc n=\"%s\">" % page["name"])
		for error in page["errors"]:
			if error != "":
				output += ("<s>%s</s>" % error)
		output += "</errors></doc>"
		outputStreamOrphans.write(tokenize(output))
		outputStreamFull.flush()
		outputStreamOrphans.flush()
	elif context["outputFormat"] == "txt":
		outputStreamFull.write("Page: %s\n" % (page["name"]))
		outputStreamOrphans.write("Page: %s\n" % (page["name"]))
		latestRev = page["revisions"][-1]["*"]
		for line in latestRev:
			outputStreamFull.write("%s\n" % line)
		for error in page["errors"]:
			outputStreamOrphans.write("%s\n" % error)			
		outputStreamFull.write("\n")
		outputStreamOrphans.write("\n")
		outputStreamFull.flush()
		outputStreamOrphans.flush()