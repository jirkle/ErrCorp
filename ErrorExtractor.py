# coding=UTF-8
import difflib
from collections import deque

import Utils

errorBuffer = []

context = None

def appendRev(textList, oldRev, newRev):
	"""Searches the textList. If any list (within textList) ends with oldRev then appeds newRev at it's end.
	Otherwise it creates new list and inserts it in the textList"""
	
	founded = False
	for k in range(0, len(textList)):
		if(textList[k][-1]==oldRev):
			textList[k] = textList[k] + (newRev,)
			founded = True
			break
	if not founded:
		textList.append((oldRev, newRev))

def removeNestedErrors():
	global errorBuffer
	for i in range(0, len(errorBuffer)):
		sentenceVersions = errorBuffer[i]
		if(len(sentenceVersions) == 2):
			break
		errorBuffer[i] = [sentenceVersions[0], sentenceVersions[-1]]
	

def resolveEvolution():
	"""Resolves evolution - 
	Changes structure of corp buffer to list of evolution lists:
	[[[allComments, baseSentence], [comment, edit], ...], ...]"""
	
	global errorBuffer
	evolutionLinks = []
	toRemove = set()
	for i in range(0, len(errorBuffer)):
		comparement = errorBuffer[i][2]
		for j in range(i, len(errorBuffer)):
			if(comparement == errorBuffer[j][1]):
				toRemove.add(errorBuffer[i])
				toRemove.add(errorBuffer[j])
				appendRev(evolutionLinks, i, j)
				break
	evolutionDeques = []
	for ev in evolutionLinks:
		queue = []
		oldSentenceList = ["", errorBuffer[ev[0]][1]]
		queue.append(oldSentenceList) #Append first oldest sentence
		allComments = ""
		for l in ev:
			allComments += errorBuffer[l][0] + "<separator>"
			newList = [errorBuffer[l][0], errorBuffer[l][2]]
			queue.append(newList) #Append newer versions of sentence
			oldSentenceList = newList
		queue[0][0] = allComments
		evolutionDeques.append(queue)
	evolutionDeques = sorted(evolutionDeques, key=len, reverse=True)
	#Normalize errorBuffer to have the same structure as evolution deques & remove matched evolution sentences
	errorBuffer = [[[x[0], x[1]], [x[0], x[2]]] for x in errorBuffer if x not in toRemove]
	errorBuffer = evolutionDeques + errorBuffer

def processStacks(oldStack, newStack, comment):
	"""Processes sentence's stacks - old sentences are matched to sentences from new sentence's stack"""
	
	if(len(oldStack) == 0 or len(newStack) == 0):
		return
	oldStack = deque([x for x in oldStack if x not in newStack])
	while len(oldStack) > 0:
		oldSent = oldStack.popleft()
		candidates = [(x, Utils.sentenceSimilarity(oldSent, x)) for x in newStack]
		candidates = [(x, similarity) for (x, similarity) in candidates if similarity > context["sentenceTreshold"]]
		if(len(candidates) > 0):
			candidates = sorted(candidates, key=lambda candidate: candidate[1], reverse=True)
			errorBuffer.append((comment, oldSent, candidates[0][0]))

def processRevisions(oldRev, newRev):
	"""Compares two revisions and constructs old and new stacks of sentences for further processing"""

	if(oldRev == None or newRev == None or oldRev["*"] == None or newRev["*"] == None):
		return
	oldStack = deque()
	newStack = deque()
	for line in difflib.unified_diff(oldRev["*"], newRev["*"]):
		if line.startswith(' '): #Skip unnecessary output
			continue
		elif line.startswith('---'):
			continue
		elif line.startswith('+++'):
			continue
		elif line.startswith('-'): #Write diff lines from old revision to stack
			oldStack.append(line[1:])
		elif line.startswith('+'): #Write diff lines from new revision to stack
			newStack.append(line[1:])
	processStacks(oldStack, newStack, newRev["comment"])

def extract(page):
	global errorBuffer
	errorBuffer = []
	if(len(page["revisions"]) > 0):
		newRev = page["revisions"][0]
		for i in range(1, len(page["revisions"])):
			oldRev = newRev
			newRev = page["revisions"][i]
			if(newRev["comment"] != None):
				processRevisions(oldRev, newRev)
		resolveEvolution()
		if(not context["allowNesting"]):
			removeNestedErrors()
	
		if len(errorBuffer) > 0: 
			page["errors"] = errorBuffer
		else:
			page["errors"] = []
	else:
		page["errors"] = []
	return page
