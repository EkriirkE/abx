#!/usr/bin/env python
#--------========########========--------
#	Android Binary XML decoder
#	2025-03-08	Erik Johnson - EkriirkE
#
#	Decode a binary XML (ABX) into plaintext
#	Ref. https://developer.android.com/reference/org/xmlpull/v1/XmlPullParser
#	Run:
#	python abx.py infile.xml
#
#--------========########========--------

import sys
import struct
import base64

#Newline character(s) that are produced after tags and content (leave empty "" for no newlines)
NewLines	= "\n"
#Tag attributes are all enquoted.  Otherwise numbers and boolean do not get quoted
QuoteAllAttr	= True
#Each attribute gets its own line
BreakAllAttr	= False
#Empty tags are <self closed />. Otherwise <empty tag=is></empty>
SelfCloseEmpty	= True
#Indentation character(s),  None if none.  Best used with newlines
Indent		= "\t"

if len(sys.argv)<2:
	print("Please pass an input file.")
	exit(1)

#Event types
XML_START_DOCUMENT	= 0
XML_END_DOCUMENT	= 1
XML_START_TAG		= 2
XML_END_TAG		= 3
XML_TEXT		= 4
XML_CDSECT		= 5
XML_ENTITY_REF		= 6
XML_WHITESPACE		= 7
XML_INSTRUCTION		= 8
XML_COMMENT		= 9
XML_DOCDECL		= 10
XML_ATTRIBUTE		= 15

#Type types
TYPE_NULL		= 1
TYPE_STRING		= 2
TYPE_STRING_INTERNED	= 3
TYPE_BYTES_HEX		= 4
TYPE_BYTES_BASE64	= 5
TYPE_INT		= 6
TYPE_INT_HEX		= 7
TYPE_LONG		= 8
TYPE_LONG_HEX		= 9
TYPE_FLOAT		= 10
TYPE_DOUBLE		= 11
TYPE_TRUE		= 12
TYPE_FALSE		= 13

#stacks
strings=[]
tags=[]
with open(sys.argv[1],"rb") as x:
	#Get filesize
	x.seek(0,2)
	xlength=x.tell()
	x.seek(0,0)

	#Let's goooo!
	if x.read(4)!=b"ABX\0":
		print("This is not an ABX file.")
		exit(2)
	InTag=False
	Content=False
	while x.tell()<xlength:
		token=x.read(1)[0]
		type=token>>4
		event=token&0x0F

		#Attributes have an implied TYPE_STRING_INTERNED before the actual type
		if event==XML_ATTRIBUTE:
			if not InTag:
				raise Exception("Attribute encountered outside a tag")
			if (slen:=struct.unpack('>H',x.read(2))[0])!=0xFFFF:pval=strings[slen]
			else:strings+=[pval:=x.read(struct.unpack('>H',x.read(2))[0]).decode()]

		#Get data based on type
		if type==TYPE_NULL:
			val=None
		elif type==TYPE_STRING:
			slen=struct.unpack('>H',x.read(2))[0]
			val=x.read(slen).decode()
		elif type==TYPE_STRING_INTERNED:
			if (slen:=struct.unpack('>H',x.read(2))[0])!=0xFFFF:val=strings[slen]
			else:strings+=[val:=x.read(struct.unpack('>H',x.read(2))[0]).decode()]
		elif type==TYPE_BYTES_HEX:
			slen=struct.unpack('>H',x.read(2))[0]
			val=x.read(slen).hex()
		elif type==TYPE_BYTES_BASE64:
			slen=struct.unpack('>H',x.read(2))[0]
			val=base64.b64encode(x.read(slen)).decode()
		elif type==TYPE_INT:
			val=struct.unpack('>i',x.read(4))[0]
		elif type==TYPE_INT_HEX:
			val="0x"+x.read(4).hex()
		elif type==TYPE_LONG:
			val=struct.unpack('>q',x.read(8))[0]
		elif type==TYPE_LONG_HEX:
			val="0x"+x.read(8).hex()
		elif type==TYPE_FLOAT:
			val=struct.unpack('>f',x.read(4))[0]
		elif type==TYPE_DOUBLE:
			val=struct.unpack('>d',x.read(8))[0]
		elif type==TYPE_TRUE:
			val=True
		elif type==TYPE_FALSE:
			val=False
		else:raise Exception(f"Unknown Type {type}")

		#Use data accordingly....
		if event==XML_START_DOCUMENT:
			#print("<xml>",end=NewLines)
			tags+=["xml"]
			continue
		elif event==XML_END_DOCUMENT:
			val=tags.pop()
			#print(f"</{val}>",end=NewLines)
			break
		elif event==XML_START_TAG:
			if InTag:print(">",end=NewLines)
			if Indent:print(Indent*(len(tags)-1),end="")
			InTag=True
			Content=False
			AttrC=0
			tags+=[val]
			print(f"<{val}",end="")
		elif event==XML_END_TAG:
			val=tags.pop()
			if InTag:
				InTag=False
				if SelfCloseEmpty and not Content:
					print(" />",end=NewLines)
					Content=True
					continue
				print(">",end=NewLines)
			if Indent:print(Indent*(len(tags)-1),end="")
			print(f"</{val}>",end=NewLines)
			Content=True
		elif event==XML_TEXT:
			if InTag:
				print(">",end=NewLines)
				InTag=False
			Content=True
			if Indent:print(Indent*(len(tags)-1),end="")
			print(val,end=NewLines)
		#elif event==XML_CDSECT:
		#elif event==XML_ENTITY_REF:
		elif event==XML_WHITESPACE:
			print(val,end="")
		#elif event==XML_INSTRUCTION:
		elif event==XML_COMMENT:
			if InTag:
				print(">",end=NewLines)
				InTag=False
			Content=True
			print(f"<!-- {val} -->",end=NewLines)
		#elif event==XML_DOCDECL:
		elif event==XML_ATTRIBUTE:
			if QuoteAllAttr or type not in (TYPE_INT,TYPE_LONG,TYPE_FLOAT,TYPE_DOUBLE,TYPE_TRUE,TYPE_FALSE):val='"'+str(val)+'"'
			if BreakAllAttr and AttrC:
				print(NewLines)
				if Indent:print(Indent*(len(tags)-1),end="")
			else:print(" ",end="")
			print(f"{pval}={val}",end="")
			AttrC+=1
		else:raise Exception(f"Unknown Event {event}")
	if x.tell()<xlength:
		raise Exception("Document ended with more data remaining")

if tags:
	raise Exception("Document ended but there are unclosed tags")
