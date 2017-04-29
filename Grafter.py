# coding=UTF-8
import difflib
import re
import pprint
from intervaltree import IntervalTree

import ErrorClassifier
import Utils

context = None

#Stats
stats = { "all": 0 }

def __init__(con):
	global context
	context = con
	ErrorClassifier.context = con

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
	
	def wrap(self, start, end, startString, endString, update=True):
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
			if(update):
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
			if(update):
				self.update()
			return True
		return False

def tupleReducer(oldTuple, newTuple):
	return (min(oldTuple[0], newTuple[0]), max(oldTuple[1], newTuple[1]))
		

def concatDifferences(diffs):
	if(len(diffs) > 1):
		points = list()
		tree = IntervalTree()
		for diff in diffs:
			if(diff[0] == diff[1]):
				points.append(diff)
			else:
				tree[diff[0]:diff[1]] = (diff[2], diff[3])
		tree.merge_overlaps(tupleReducer)
		items = tree.items()
		for point in points:
			if(len(tree[point[0]]) == 0):
				items.add((point[0], point[1], (point[2], point[3])))
		
		points = list()
		tree = IntervalTree()
		for item in items:
			if(item[2][0] == item[2][1]):
				points.append([item[2][0], item[2][1], item[0], item[1]])
			else:
				tree[item[2][0]:item[2][1]] = (item[0], item[1])
		tree.merge_overlaps(tupleReducer)
		items = tree.items()
		for point in points:
			if(len(tree[point[0]]) == 0):
				items.add((point[0], point[1], (point[2], point[3])))		
		diffs = list()
		for item in items:
			diffs.append([item[2][0], item[2][1], item[0], item[1]])
	return diffs
		
	

def expandDifferences(old, new, differences):
	differences = [diff for diff in differences if diff[0] != diff[1] or diff[2] != diff[3]]
	punctRe = context["errCorpConfig"].reList["allpunctuation"]
	punctSpaceRe = context["errCorpConfig"].reList["punctSpace"]	
	for diff in differences: #Trim to whole words
		if (not punctRe.match(new[diff[2]:diff[3]]) and not punctRe.match(old[diff[0]:diff[1]])):
			oldTrimmed = False
			newTrimmed = False
			while diff[0] > 0 and not punctSpaceRe.search(old[diff[0] - 1]):
				diff[0] -= 1
			while diff[1] < len(old) and not punctSpaceRe.search(old[diff[1]]):
				diff[1] += 1
			while diff[2] > 0 and not punctSpaceRe.search(new[diff[2] - 1]):
				diff[2] -= 1
			while diff[3] < len(new) and not punctSpaceRe.search(new[diff[3]]):
				diff[3] += 1			
		o = old[diff[0]:diff[1]]
		n = new[diff[2]:diff[3]]
	differences = concatDifferences(differences)
	return differences
	
def getDifferences(base, new):
	sequenceMatcher = difflib.SequenceMatcher(a=base.getString(), b=new, autojunk=False)
	matchingBlocks = sequenceMatcher.get_matching_blocks()
	edits = []
	startOldSent = 0
	startNewSent = 0
	for match in matchingBlocks:
		if(match[2] == 0): #End of matches
			edits.append(list((startOldSent, len(sequenceMatcher.a), startNewSent, len(sequenceMatcher.b))))
			return expandDifferences(sequenceMatcher.a, sequenceMatcher.b, edits)
		edits.append(list((startOldSent, match[0], startNewSent, match[1])))
		startOldSent = match[0] + match[2]
		startNewSent = match[1] + match[2]
	return expandDifferences(sequenceMatcher.a, sequenceMatcher.b, edits)

def expandError(error):
	error.reverse()
	base = error.pop(0)
	base = HidingString(base[1])
	#currTokens = tokenize(currSent[1])
	for sentence in error:
		differences = getDifferences(base, sentence[1])
		differences = sorted(differences, key=lambda diff: diff[0], reverse=True)
		for diff in differences:
			error = ErrorClassifier.ErrorClassifier(base.getString(), sentence[1], diff)
			wrapped = base.wrap(error.getStart(), error.getEnd(), error.getStartString(), error.getEndString())
			if(wrapped):
				stats["all"] += 1
				if(error.getErrorType() in stats):
					stats[error.getErrorType()] += 1
				else:
					stats[error.getErrorType()] = 1
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
	if(not context["mute"]):
		pprint.pprint(stats)
	return page