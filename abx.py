#!/usr/bin/env python
#--------========########========--------
#	Android Binary XML decoder
#	2025-03-08	Erik Johnson - EkriirkE
#
#	Decode a binary XML (ABX) into plaintext
#	Ref. https://developer.android.com/reference/org/xmlpull/v1/XmlPullParser
#	Run:
#	python abx.py infile.xml
#	cat infile.xml | python abx.py
#
#--------========########========--------

import sys
import struct
import base64

#Newline character(s) that are produced after tags and content (leave empty "" for no newlines)
NewLines	= "\n"
#Indentation character(s) follow tag depth,  None or empty "" if none.  Best used with newlines
IndentLines	= "\t"
#Tag attributes are all enquoted.  Otherwise numbers and boolean do not get quoted
QuoteAllAttr	= True
#Each attribute gets its own line, with indent as needed
BreakAllAttr	= False
#Empty tags are <self closed />. Otherwise <empty tag=is></empty>
SelfCloseEmpty	= True
#Boolean style: 0 True, 1 true, 2 TRUE, 3 1/0
BoolStyle	= 0
#Trim leading 0s from Hex values.  0x0000001F > 0x1F
TrimHex		= True



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

if len(sys.argv)<2:
	stream=sys.stdin.buffer
	xlength=-1
else:
	stream=open(sys.argv[1],"rb")
	stream.seek(0,2)
	xlength=stream.tell()
	stream.seek(0,0)
with stream as x:

	#Let's goooo!
	if x.read(4)!=b"ABX\0":
		print("This is not an ABX file.")
		exit(2)
	InTag=False
	Content=False
	while xlength<0 or x.tell()<xlength:
		token=x.read(1)[0]
		type=token>>4
		event=token&0x0F

		#Attributes have an implied TYPE_STRING_INTERNED before the actual type
		if event==XML_ATTRIBUTE:
			if not InTag:
				raise Exception("Attribute encountered outside a tag")
			if (idx:=struct.unpack('>H',x.read(2))[0])!=0xFFFF:pval=strings[idx]
			else:strings+=[pval:=x.read(struct.unpack('>H',x.read(2))[0]).decode()]

		#Get data based on type
		if type==TYPE_NULL:
			val=None
		elif type==TYPE_STRING:
			val=x.read(struct.unpack('>H',x.read(2))[0]).decode()
		elif type==TYPE_STRING_INTERNED:
			if (idx:=struct.unpack('>H',x.read(2))[0])!=0xFFFF:val=strings[idx]
			else:strings+=[val:=x.read(struct.unpack('>H',x.read(2))[0]).decode()]
		elif type==TYPE_BYTES_HEX:
			val=x.read(struct.unpack('>H',x.read(2))[0]).hex()
		elif type==TYPE_BYTES_BASE64:
			val=base64.b64encode(x.read(struct.unpack('>H',x.read(2))[0])).decode()
		elif type==TYPE_INT:
			val=struct.unpack('>i',x.read(4))[0]
		elif type==TYPE_INT_HEX:
			val=x.read(4).hex()
			if TrimHex:val=val.lstrip("0") or "0"
			val="0x"+val
		elif type==TYPE_LONG:
			val=struct.unpack('>q',x.read(8))[0]
		elif type==TYPE_LONG_HEX:
			val=x.read(8).hex()
			if TrimHex:val=val.lstrip("0") or "0"
			val="0x"+val
		elif type==TYPE_FLOAT:
			val=struct.unpack('>f',x.read(4))[0]
		elif type==TYPE_DOUBLE:
			val=struct.unpack('>d',x.read(8))[0]
		elif type==TYPE_TRUE:
			val="True"
			if BoolStyle==1:val=val.lower()
			if BoolStyle==2:val=val.upper()
			if BoolStyle==3:val=1
		elif type==TYPE_FALSE:
			val="False"
			if BoolStyle==1:val=val.lower()
			if BoolStyle==2:val=val.upper()
			if BoolStyle==3:val=0
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
			if IndentLines:print(IndentLines*(len(tags)-1),end="")
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
			if IndentLines:print(IndentLines*(len(tags)-1),end="")
			print(f"</{val}>",end=NewLines)
			Content=True
		elif event==XML_TEXT:
			if InTag:
				print(">",end=NewLines)
				InTag=False
			Content=True
			if IndentLines:print(IndentLines*(len(tags)-1),end="")
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
			val=repr(str(val))[1:-1].replace('"',r'\"')
			if QuoteAllAttr or type not in (TYPE_INT,TYPE_INT_HEX,TYPE_LONG,TYPE_LONG_HEX,TYPE_FLOAT,TYPE_DOUBLE,TYPE_TRUE,TYPE_FALSE):val='"'+str(val)+'"'
			if BreakAllAttr and AttrC:
				print(NewLines)
				if IndentLines:print(IndentLines*(len(tags)-1),end="")
			else:print(" ",end="")
			print(f"{pval}={val}",end="")
			AttrC+=1
		else:raise Exception(f"Unknown Event {event}")
	if xlength>=0 and x.tell()<xlength:
		raise Exception("Document ended with more data remaining")

if tags:
	raise Exception("Document ended but there are unclosed tags")
