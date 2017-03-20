# coding=UTF-8
import sys
import os
import io
import xml.etree.ElementTree as ET
import difflib
import pprint
import re
import platform
from collections import deque
from multiprocessing import Pool
from UnicodeHack import hack_regexp

import WikiExtractor
import Utils

poolProcesses = 8

pool = None

context = None

def textClean(text):
	"""Cleans up the text - removes rests from wiki markup, 
	replaces special character (e.g. '…' -> '...', '„' -> '"')"""

	text = re.sub(r"&lt;.*?&gt;", r"",text) #Remove inline markup
	text = re.sub(r"<.*?>", r"", text) #Remove inline markup
	text = re.sub(r"\.\.\.", r"…", text) #Clean text
	
	text = re.sub(r"\[(.*?\|)*(.*?)\]", r"\1", text) #Remove all wiki interlinks
	text = re.sub(r"[‘’ʹ՚‛ʻʼ՝ʽʾ]", r"'", text) #Preserve only one type of single quotes
	text = re.sub(r"[„“˝”ˮ‟″‶〃＂“]", r'"', text) #Preserve only one type of double quotes
	text = re.sub(r"[‐‑‒−–⁃➖˗﹘-]", r"-", text) #Preserve only one type of hyphens
	text = re.sub(r"\*", r"<stop>", text, re.U) #Replace bullets
	
	#Mark headings to be start of sentences and preserve heading text
	text = re.sub(r"======\s*(.*?)\s*======", r"<stop>\1<stop>:", text)
	text = re.sub(r"=====\s*(.*?)\s*=====", r"<stop>\1<stop>", text)
	text = re.sub(r"====\s*(.*?)\s*====", r"<stop>\1<stop>", text) 
	text = re.sub(r"===\s*(.*?)\s*===", r"<stop>\1<stop>", text)
	text = re.sub(r"==\s*(.*?)\s*==", r"<stop>\1<stop>", text)
	#text = re.sub(r"=", r" ", text) #Remove rest equal signs	
	
	text = re.sub(r"\s*\.(\s*\.)*", r".", text) #Remove more dots
	text = re.sub(r"…", r"...", text) #Clean text
	
	text = re.sub(r"(\s+)", r"\1", text) #Remove more spaces
	return text

def sentenceClean(text, trimToSentenceStart=False, trimToSentenceEnd=True):
	"""Cleans up the sentence"""
	
	if(text == None):
		return None
	text = re.sub(r"^(\s*(\*)*\s*)", r" ", text, re.U) #Replace bullets at the start
	text = re.sub(r"\s*;(\s*;)*", r";", text, re.U) #Remove more semi-colons
	text = re.sub(r"([:;.,-])+\s*[:;.,-]+", r"\1 ", text, re.U) #Remove odd punctuation combinations
	
	text = re.sub(r"\'(\s*\')*", r"'", text, re.U) #Remove more single quotes
	text = re.sub(r"\"(\s*\")*", r'"', text, re.U) #Remove more double quotes
	text = re.sub(r",(\s*,)*", r",", text, re.U) #Remove more commas
	text = re.sub(r"\:(\s*:)*", r":", text, re.U) #Remove more colons
	text = re.sub(r"-(\s*-)*", r"-", text, re.U) #Remove more hyphens
		
	text = re.sub(r"[\[\]]", r" ", text) #Clean rest brackets
	
	text = re.sub(r"([\(\{\[])\s*", r"\1", text, re.U) #Remove spaces after starting brackets
	text = re.sub(r"\s*([\)\}\]])", r"\1", text, re.U) #Remove spaces before closing brackets
    
	if(trimToSentenceStart):
		text = re.subn(hack_regexp(r"^.*?(\\p{Lu}|[\[\{\(\"\']|[0-9])"), r"\1", text, re.U)
		if(text[1] == 0):
			text = ""
		else:
			text = text[0]
	if(trimToSentenceEnd):
		pass
	text = re.sub(r"(\s+)", r" ", text) #Remove more spaces
	
	return text.strip()	

def splitBySentences(rev, doClean=True):
	"""Splits text to sentences. Base function from 
	http://stackoverflow.com/questions/4576077/python-split-text-on-sentences"""
	config = context["errCorpConfig"]
	text = rev["*"]
	if(text == None): return None
	if(doClean): text = textClean(text)
	text = " " + text + "  "
	text = text.replace("\n", r"<stop>")
	text = text.replace("\r", r"<stop>")
	text = text.replace(r"\.*,", r"<prd>,")
	text = config.reList["abbrs"].sub(r"\1\2<prd>", text)
	text = config.reList["websites"].sub(r"<prd>\1", text)	
	text = text.replace(r"\.(" + config.puncEnders + ")", r"<prd>\1<stop>")
	text = re.sub(r"\s" + config.caps + r"[.]\s", r" \1<prd> ", text)
	text = re.sub(config.caps + r"[.]" + config.caps + r"[.]" + config.caps + r"[.]", r"\1<prd>\2<prd>\3<prd>", text)
	text = re.sub(config.caps + r"[.]" + config.caps + r"[.]", r"\1<prd>\2<prd>", text)
	text = re.sub(r"\s" + config.caps + r"[.]", r" \1<prd>", text)
	text = config.reList["digitsSentenceEndings"].sub(r"\1<stop> \2", text)
	text = re.sub(config.digits + r"[.]", r"\1<prd>", text)
	text = text.replace(r"!\"", r"\"!")
	text = text.replace(r"?\"", r"\"?")
	text = text.replace(r".", r".<stop>")
	text = text.replace(r"?", r"?<stop>")
	text = text.replace(r"!", r"!<stop>")
	text = text.replace(r"<prd>", r".")
	sentences = re.split(r"<stop>", text, flags=re.MULTILINE)
	sentences = [s.strip() for s in sentences]
	sentences = [x for x in sentences if x != ""]
	if(doClean): 
		for i in range(0, len(sentences)):
			sentences[i] = sentenceClean(sentences[i])
	rev["*"] = [x for x in sentences if x != ""]		
	return rev

def removeBadRevisions(page, preserveRobotRevisions=False):
	"""Function for removing bot or reverted revisions from page dictionary."""
	config = context["errCorpConfig"]
	page["revisions"] = [x for x in page["revisions"] if x != None and x["comment"] != None]
	if(not preserveRobotRevisions):
		page["revisions"] = [x for x in page["revisions"] if not config.botFilter.search(x["comment"])]
	
	toRevert = []
	prev = None
	for rev in page["revisions"]:
		if(config.revertFilter.search(rev["comment"])):
			toRevert.append(rev)
			toRevert.append(prev)
		prev = rev
	page["revisions"] = [x for x in page["revisions"] if x not in toRevert]
	
def renderRevision(rev, title):
	"""Renders revision dictionary in HTML/WikiMarkup into plaintext. TODO Html conversion!"""
	
	if(rev["*"] != None): 
		if(rev["format"] == "wikimarkup"):
			text = rev["*"]
			out = io.StringIO()
			extractor = WikiExtractor.Extractor(0, 0, title, text.split("\n"))
			extractor.extract(out)
			rev["*"] = out.getvalue()
			out.close()
			rev = splitBySentences(rev)
			rev["format"] = "plaintext"
			return rev
		else:
			return rev
	else:
		return rev	

def renderPageRevisions(page, poolProcesses=8):
	"""Renders all revs of page into plain text, uses multiprocessing on Linux."""
	global pool
	if(pool == None):
		pool = Pool(context["poolProcesses"])
	poolAsyncResults = []
	for rev in page["revisions"]:
		if(platform.system() == "Linux"):
			poolAsyncResults.append(pool.apply_async(renderRevision, args=(rev, page["name"])))
			#renderRevision(rev, page["name"])
		else:
			renderRevision(rev, page["name"])
	for i in range(0, len(poolAsyncResults)):
		try:
			page["revisions"][i] = poolAsyncResults[i].get()	#collect results from pool
		except:
			page["revisions"][i]["*"] = None
	page["revisions"] = [x for x in page["revisions"] if x != None]
	return page

def normalize(page):
	"""Removes reverted revisions, then renders them all of them into plaintext"""
	
	removeBadRevisions(page, context["preserveRobotRevisions"])
	renderPageRevisions(page, poolProcesses)
	return page