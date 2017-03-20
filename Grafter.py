# coding=UTF-8
import sys
import os
import io
import difflib
import pprint
import re
from collections import deque

import Utils

class HidingString:
	fullString = ""
	hidedArray = []
	secretsRe = []
	
	def __init__(self, text):
		self.hidedArray = []
		self.secretsRe = []
		self.fullString = text
		self.secretsRe.append(re.compile(r"""<err.*?</err><corr>""", re.U | re.X))
		self.secretsRe.append(re.compile(r"""</corr>""", re.U | re.X))
		self.update()
	
	def update(self):
		self.hidedArray = []
		for regex in self.secretsRe:
			for match in regex.finditer(self.fullString):
				self.hidedArray.append((match.start(), match.end()))
		self.hidedArray.sort(key=lambda tup: tup[0])	
		
	def getString(self, full=False):
		if(full):
			return self.fullString
		else:
			if(self.hidedArray == []):
				return self.fullString	
			outputString = ""
			curIndex = 0
			for match in self.hidedArray:
				if(curIndex < match[0]):
					outputString += self.fullString[curIndex:match[0]]
				curIndex = match[1]
			outputString += self.fullString[curIndex:]
			return outputString
	
	def getPositionInFullstring(self, position):
		if(self.hidedArray == []):
			return position		
		matchesLength = 0
		fullPos = 0
		for match in self.hidedArray:
			if(match[1] - matchesLength - (match[1] - match[0]) < position):
				matchesLength += (match[1] - match[0])
				fullPos = match[1]
			else: break
		fullPos += position - (fullPos - matchesLength)
		return fullPos
	
	def wrap(self, start, end, startString, endString):
		if(start > end):
			t = start
			start = end
			end = t
		
		start = self.getPositionInFullstring(start)
		end = self.getPositionInFullstring(end)
		
		wrappedString = self.fullString[start:end]
		if(wrappedString == ""): #We are not interested just in text removal
			return
		openers = self.secretsRe[0].findall(wrappedString)
		closers = self.secretsRe[1].findall(wrappedString)
		canWrap = True
		if(len(openers) != len(closers)):
			canWrap = False
		if(canWrap and len(openers) > 0):
			if(openers[0][0] > closers[0][0]):
				canWrap = False
			if(openers[-1][1] > closers[-1][1]):
				canWrap = False
		if(canWrap):
			self.fullString = self.fullString[0:start] + startString + self.fullString[start:end] + endString + 			self.fullString[end:]
		self.update()

def removeAndExpandDifferences(old, new, differences, expand=True):
	differences = [diff for diff in differences if diff[0] != diff[1] or diff[2] != diff[3]]
	if expand:
		for diff in differences: #Trim to whole words
			#if(not diff[0] == diff[2]):
				while diff[0] > 0 and (not old[diff[0] - 1].isspace() and not Utils.ispunct(old[diff[0] - 1])):
					diff[0] -= 1
				while diff[2] > 0 and (not new[diff[2] - 1].isspace() and not Utils.ispunct(new[diff[2] - 1])):
					diff[2] -= 1
			#if(not diff[1] == diff[3]):
				while diff[1] < len(old) and not (old[diff[1]].isspace() or Utils.ispunct(old[diff[1]])):
					diff[1] += 1
				while diff[3] < len(new) and not (new[diff[3]].isspace() or Utils.ispunct(new[diff[3]])):
					diff[3] += 1
	return differences
	
def getDifferences(base, new, errorType):
	sequenceMatcher = difflib.SequenceMatcher(a=base.getString(), b=new, autojunk=False)
	matchingBlocks = sequenceMatcher.get_matching_blocks()
	edits = []
	startOldSent = 0
	startNewSent = 0
	for match in matchingBlocks:
		if(match[2] == 0): #End of matches
			edits.append(list((startOldSent, len(sequenceMatcher.a), startNewSent, len(sequenceMatcher.b))))
			return removeAndExpandDifferences(sequenceMatcher.a, sequenceMatcher.b, edits, not "punct" == errorType)
		edits.append(list((startOldSent, match[0], startNewSent, match[1])))
		startOldSent = match[0] + match[2]
		startNewSent = match[1] + match[2]
	return removeAndExpandDifferences(sequenceMatcher.a, sequenceMatcher.b, edits, not "punct" == errorType)

def expandError(error):
	error.reverse()
	base = error.pop(0)
	errorType = base[0]
	base = HidingString(base[1])
	#currTokens = tokenize(currSent[1])
	for sentence in error:
		differences = getDifferences(base, sentence[1], errorType)
		for diff in differences:
			injectedText = sentence[1][diff[2]:diff[3]]
			base.wrap(diff[0], diff[1], "<err type=\""+ errorType + "\">" + injectedText + "</err><corr>", "</corr>")
		errorType = sentence[0]
	return base

def errorStringRecursively(errors):
	"""Recursion for constructing error string in sketch engine fromat"""
	
	if(len(errors) <= 1):
		return tokenize(errors[0][1])
	
	last = errors[-1]
	errContent = last[1]
	errType = last[0]
	
	return ("<err type=\"%s\">\n" % errType) + errorStringRecursively(errors[:-1]) + ("\n</err>\n<corr type=\"%s\">\n%s\n</corr>" % (errType, tokenize(errContent)))

def graft(page):
	expanded = []
	for error in page["errors"]:
		expanded.append(expandError(error))
	latestPageContent = page["revisions"][-1]["*"]
	for i in range(0, len(latestPageContent)):
		for error in expanded:
			if(latestPageContent[i] == error.getString()):
				latestPageContent[i] = error.getString(full=True)
				expanded.remove(error)
				break
	page["errors"] = [e.getString(True) for e in expanded]
	return page