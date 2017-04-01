# coding=UTF-8
import difflib
import re
import pprint
from intervaltree import IntervalTree
from intervaltree import Interval

import Utils

context = None

#Stats
stats = { "all": 0, "punct": 0, "order": 0, "typos": 0, "edits": 0, "other": 0 }

class HidingString(object):
	fullString = ""
	visibleString = ""
	hidedIntervals = []
	secretsRe = []
	mode = "oldest"
	
	def __init__(self, text, update=False):
		self.hidedIntervals = IntervalTree()
		self.secretsRe = []
		self.fullString = text
		self.secretsRe.append(re.compile(r"""(<err.*?>)""", re.U | re.X))
		self.secretsRe.append(re.compile(r"""(</err><corr>)""", re.U | re.X))
		self.secretsRe.append(re.compile(r"""(</corr>)""", re.U | re.X))
		if(update):
			self.update()
		else:
			self.visibleString = text
	
	def update(self):
		tokenIntervals = IntervalTree()
		intervals = IntervalTree()
		stack = []
		for match in self.secretsRe[0].finditer(self.fullString):
			intervals.addi(match.start(), match.end(), "begin") #<err.*?>
		for match in self.secretsRe[1].finditer(self.fullString):
			intervals.addi(match.start(), match.end(), "center") #</err><corr>
		for match in self.secretsRe[2].finditer(self.fullString):
			intervals.addi(match.start(), match.end(), "end") #</corr>
		intervals = sorted(intervals)
		hidedIntervals = IntervalTree()
		if(self.mode == "latest"):
			for i in intervals:
				if(i.data == "begin"):
					stack.append(i)
				elif(i.data == "center"):
					token = stack.pop()
					if(len(stack) == 0):
						hidedIntervals.addi(token.begin, i.end, None)
				elif(i.data == "end"):
					hidedIntervals.addi(i.begin, i.end, None)
		else:
			for i in intervals:
				if(i.data == "begin"):
					hidedIntervals.addi(i.begin, i.end, None)
				elif(i.data == "center"):
					stack.append(i)
				elif(i.data == "end"):
					token = stack.pop()
					if(len(stack) == 0):
						hidedIntervals.addi(token.begin, i.end, None)
		hidedIntervals.merge_overlaps()
		if(hidedIntervals != None):
			self.hidedIntervals = sorted(hidedIntervals)
		else:
			self.hidedIntervals = []
		if(len(self.hidedIntervals) == 0):
			self.visibleString = self.fullString
		else:
			self.visibleString = ""
			curIndex = 0
			for match in self.hidedIntervals:
				if(curIndex < match[0]):
					self.visibleString += self.fullString[curIndex:match[0]]
				curIndex = match[1]
			self.visibleString += self.fullString[curIndex:]
	
	def setMode(self, mode):
		self.mode = mode
		self.update()
		return self
		
	def getString(self, full=False):
		if(full):
			return self.fullString
		else:
			return self.visibleString
	
	def getStartPositionInFullstring(self, position):
		if(self.hidedIntervals == []):
			return position		
		matchesLength = 0
		fullPos = 0
		for match in self.hidedIntervals:
			if(match[1] - matchesLength - (match[1] - match[0]) < position):
				matchesLength += (match[1] - match[0])
				fullPos = match[1]
			else: break
		fullPos += position - (fullPos - matchesLength)
		return fullPos
	
	def getEndPositionInFullstring(self, position):
		fullPos = self.getStartPositionInFullstring(position)
		for match in self.hidedIntervals:
			if(match[0]==fullPos):
				fullPos += (match[1] - match[0])
		return fullPos
	
	def wrap(self, start, end, startString, endString):
		if(start > end):
			t = start
			start = end
			end = t
		
		start = self.getEndPositionInFullstring(start)
		end = self.getStartPositionInFullstring(end)
		
		wrappedString = self.fullString[start:end]
		if(wrappedString == ""): #We are not interested just in text removal
			return
		openers = self.secretsRe[0].search(wrappedString)
		closers = self.secretsRe[2].search(wrappedString)
		canWrap = True
		if(openers == None and closers == None):
			self.fullString = self.fullString[0:start] + startString + self.fullString[start:end] + endString + 			self.fullString[end:]
			self.update()
			return True
		if(openers == None or closers == None):
			canWrap = False
		if(canWrap and len(openers.groups()) != len(closers.groups())):
			canWrap = False
		if(canWrap):
			if(openers.start(0) > closers.start(0)):
				canWrap = False
			
			if(openers.end(len(openers.groups()) - 1) > closers.end(len(openers.groups()) - 1)):
				canWrap = False
		if(canWrap):
			self.fullString = self.fullString[0:start] + startString + self.fullString[start:end] + endString + 			self.fullString[end:]
			self.update()
			return True
		return False

def expandDifferences(old, new, differences, expand=True):
	differences = [diff for diff in differences if diff[0] != diff[1] and diff[2] != diff[3]]
	if expand:
		for diff in differences: #Trim to whole words
			oldS = old[diff[0]:diff[1]]
			newS = new[diff[2]:diff[3]]
			#if diff[0] != diff[1]:
			while diff[0] > 0 and (not old[diff[0]-1].isspace() and not Utils.ispunct(old[diff[0]-1])):
				diff[0] -= 1
			while diff[1] < len(old) and (not old[diff[1]].isspace() and not Utils.ispunct(old[diff[1]])):
				diff[1] += 1
			#if diff[2] != diff[3]:	
			while diff[2] > 0 and (not new[diff[2]-1].isspace() and not Utils.ispunct(new[diff[2]-1])):
				diff[2] -= 1
			while diff[3] < len(new) and (not new[diff[3]].isspace() and not Utils.ispunct(new[diff[3]])):
				diff[3] += 1
			oldS = old[diff[0]:diff[1]]
			newS = new[diff[2]:diff[3]]			
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
			return expandDifferences(sequenceMatcher.a, sequenceMatcher.b, edits, not "punct" == errorType)
		edits.append(list((startOldSent, match[0], startNewSent, match[1])))
		startOldSent = match[0] + match[2]
		startNewSent = match[1] + match[2]
	return expandDifferences(sequenceMatcher.a, sequenceMatcher.b, edits, not "punct" == errorType)

def expandError(error):
	error.reverse()
	base = error.pop(0)
	errorType = base[0]
	base = HidingString(base[1])
	#currTokens = tokenize(currSent[1])
	for sentence in error:
		differences = sorted(getDifferences(base, sentence[1], errorType), reverse=True)
		for diff in differences:
			injectedText = sentence[1][diff[2]:diff[3]]
			wrapped = base.wrap(diff[0], diff[1], "<err type=\""+ errorType + "\">" + injectedText + "</err><corr>", "</corr>")
			if(wrapped):
				stats["all"] += 1
				stats[errorType] += 1
		errorType = sentence[0]
	return base

def graft(page):
	expanded = []
	for error in page["errors"]:
		expanded.append(expandError(error))
	latestPageContent = page["revisions"][-1]["*"]
	for error in expanded:
		error.setMode("latest")
	for i in range(0, len(latestPageContent)):
		for error in expanded:
			if(latestPageContent[i] == error.getString()):
				latestPageContent[i] = error.getString(full=True)
				expanded.remove(error)
				break
	page["errors"] = [e.getString(True) for e in expanded]
	pprint.pprint(stats)
	return page