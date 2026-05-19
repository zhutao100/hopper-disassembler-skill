# Scripts

<span id="API"></span>

- [Class CallReference](#class_anchor_CallReference)
  - [fromAddress](#meth7)
  - [toAddress](#meth8)
  - [type](#meth6)
- [Class LocalVariable](#class_anchor_LocalVariable)
  - [displacement](#meth11)
  - [name](#meth10)
- [Class Tag](#class_anchor_Tag)
  - [getName](#meth15)
- [Class Procedure](#class_anchor_Procedure)
  - [addTag](#meth28)
  - [addressOfLocalLabel](#meth44)
  - [basicBlockIterator](#meth25)
  - [clearRegisterNameOverride](#meth49)
  - [declareLocalLabelAt](#meth42)
  - [decompile](#meth45)
  - [getAllCalleeProcedures](#meth38)
  - [getAllCallees](#meth36)
  - [getAllCallerProcedures](#meth37)
  - [getAllCallers](#meth35)
  - [getBasicBlock](#meth23)
  - [getBasicBlockAtAddress](#meth24)
  - [getBasicBlockCount](#meth22)
  - [getEntryPoint](#meth21)
  - [getHeapSize](#meth26)
  - [getLocalVariableList](#meth27)
  - [getSection](#meth20)
  - [getSegment](#meth19)
  - [getTagAtIndex](#meth32)
  - [getTagCount](#meth31)
  - [getTagList](#meth34)
  - [hasLocalLabelAtAddress](#meth39)
  - [hasTag](#meth30)
  - [localLabelAtAddress](#meth40)
  - [registerNameOverride](#meth48)
  - [removeLocalLabelAtAddress](#meth43)
  - [removeTag](#meth29)
  - [renameRegister](#meth47)
  - [setLocalLabelAtAddress](#meth41)
  - [signatureString](#meth46)
  - [tagIterator](#meth33)
- [Class BasicBlock](#class_anchor_BasicBlock)
  - [addTag](#meth59)
  - [getEndingAddress](#meth55)
  - [getProcedure](#meth53)
  - [getStartingAddress](#meth54)
  - [getSuccessorAddressAtIndex](#meth58)
  - [getSuccessorCount](#meth56)
  - [getSuccessorIndexAtIndex](#meth57)
  - [getTagAtIndex](#meth63)
  - [getTagCount](#meth62)
  - [getTagList](#meth65)
  - [hasTag](#meth61)
  - [removeTag](#meth60)
  - [tagIterator](#meth64)
- [Class Instruction](#class_anchor_Instruction)
  - [getArchitecture](#meth68)
  - [getArgumentCount](#meth70)
  - [getFormattedArgument](#meth72)
  - [getInstructionLength](#meth75)
  - [getInstructionString](#meth69)
  - [getRawArgument](#meth71)
  - [isAConditionalJump](#meth74)
  - [isAnInconditionalJump](#meth73)
  - [stringForArchitecture](#meth67)
- [Class Section](#class_anchor_Section)
  - [getFlags](#meth82)
  - [getLength](#meth81)
  - [getName](#meth79)
  - [getStartingAddress](#meth80)
- [Class Segment](#class_anchor_Segment)
  - [addReference](#meth138)
  - [disassembleWholeSegment](#meth127)
  - [getArrayElementAddress](#meth153)
  - [getArrayElementCount](#meth152)
  - [getArrayElementSize](#meth154)
  - [getArrayStartAddress](#meth151)
  - [getCommentAtAddress](#meth131)
  - [getDemangledNameAtAddress](#meth130)
  - [getFileOffset](#meth90)
  - [getFileOffsetForAddress](#meth91)
  - [getInlineCommentAtAddress](#meth133)
  - [getInstructionAtAddress](#meth135)
  - [getInstructionStart](#meth148)
  - [getLabelCount](#meth140)
  - [getLabelsList](#meth142)
  - [getLength](#meth89)
  - [getName](#meth87)
  - [getNameAtAddress](#meth129)
  - [getNamedAddresses](#meth143)
  - [getNextAddressWithType](#meth126)
  - [getObjectLength](#meth149)
  - [getProcedureAtAddress](#meth147)
  - [getProcedureAtIndex](#meth145)
  - [getProcedureCount](#meth144)
  - [getProcedureIndexAtAddress](#meth146)
  - [getReferencesFromAddress](#meth137)
  - [getReferencesOfAddress](#meth136)
  - [getSection](#meth93)
  - [getSectionAtAddress](#meth96)
  - [getSectionCount](#meth92)
  - [getSectionIndexAtAddress](#meth95)
  - [getSectionsList](#meth94)
  - [getStartingAddress](#meth88)
  - [getStringAddressAtIndex](#meth157)
  - [getStringAtIndex](#meth156)
  - [getStringCount](#meth155)
  - [getStringsList](#meth158)
  - [getTypeAtAddress](#meth123)
  - [isPartOfAnArray](#meth150)
  - [isThumbAtAddress](#meth120)
  - [labelIterator](#meth141)
  - [makeAlignment](#meth125)
  - [markAsCode](#meth115)
  - [markAsDataByteArray](#meth117)
  - [markAsDataIntArray](#meth119)
  - [markAsDataShortArray](#meth118)
  - [markAsProcedure](#meth116)
  - [markAsUndefined](#meth113)
  - [markRangeAsUndefined](#meth114)
  - [readByte](#meth98)
  - [readBytes](#meth97)
  - [readUInt16BE](#meth102)
  - [readUInt16LE](#meth99)
  - [readUInt32BE](#meth103)
  - [readUInt32LE](#meth100)
  - [readUInt64BE](#meth104)
  - [readUInt64LE](#meth101)
  - [removeReference](#meth139)
  - [setARMModeAtAddress](#meth122)
  - [setCommentAtAddress](#meth132)
  - [setInlineCommentAtAddress](#meth134)
  - [setNameAtAddress](#meth128)
  - [setThumbModeAtAddress](#meth121)
  - [setTypeAtAddress](#meth124)
  - [stringForType](#meth83)
  - [writeByte](#meth106)
  - [writeBytes](#meth105)
  - [writeUInt16BE](#meth110)
  - [writeUInt16LE](#meth107)
  - [writeUInt32BE](#meth111)
  - [writeUInt32LE](#meth108)
  - [writeUInt64BE](#meth112)
  - [writeUInt64LE](#meth109)
- [Class Document](#class_anchor_Document)
  - [addTagAtAddress](#meth217)
  - [ask](#meth165)
  - [askDirectory](#meth167)
  - [askFile](#meth166)
  - [assemble](#meth178)
  - [backgroundProcessActive](#meth175)
  - [buildTag](#meth228)
  - [closeDocument](#meth169)
  - [deleteSegment](#meth185)
  - [destroyTag](#meth230)
  - [findBookmarkWithName](#meth263)
  - [generateObjectiveCHeader](#meth257)
  - [getAddressForName](#meth212)
  - [getAddressFromFileOffset](#meth205)
  - [getAllDocuments](#meth164)
  - [getBookmarkName](#meth264)
  - [getBookmarks](#meth265)
  - [getColorAtAddress](#meth233)
  - [getCurrentAddress](#meth199)
  - [getCurrentDocument](#meth163)
  - [getCurrentProcedure](#meth198)
  - [getCurrentSection](#meth197)
  - [getCurrentSegment](#meth196)
  - [getCurrentSegmentIndex](#meth195)
  - [getDatabaseFilePath](#meth179)
  - [getDocumentName](#meth173)
  - [getEntryPoint](#meth207)
  - [getExecutableFilePath](#meth180)
  - [getFileOffsetFromAddress](#meth204)
  - [getHighlightedWord](#meth209)
  - [getInstructionStart](#meth255)
  - [getNameAtAddress](#meth211)
  - [getObjectLength](#meth256)
  - [getOperandFormat](#meth251)
  - [getOperandFormatRelativeTo](#meth252)
  - [getRawSelectedLines](#meth216)
  - [getSectionAtAddress](#meth194)
  - [getSectionByName](#meth190)
  - [getSegment](#meth188)
  - [getSegmentAtAddress](#meth193)
  - [getSegmentByName](#meth189)
  - [getSegmentCount](#meth187)
  - [getSegmentIndexAtAddress](#meth192)
  - [getSegmentsList](#meth191)
  - [getSelectionAddressRange](#meth201)
  - [getTagAtAddressByIndex](#meth221)
  - [getTagAtIndex](#meth225)
  - [getTagCount](#meth224)
  - [getTagCountAtAddress](#meth220)
  - [getTagList](#meth227)
  - [getTagListAtAddress](#meth223)
  - [getTagWithName](#meth229)
  - [hasBookmarkAtAddress](#meth261)
  - [hasColorAtAddress](#meth231)
  - [hasTagAtAddress](#meth219)
  - [is64Bits](#meth206)
  - [loadDocumentAt](#meth170)
  - [log](#meth182)
  - [message](#meth168)
  - [moveCursorAtAddress](#meth202)
  - [moveCursorAtEntryPoint](#meth208)
  - [moveCursorOneLineDown](#meth214)
  - [moveCursorOneLineUp](#meth215)
  - [newDocument](#meth162)
  - [newSegment](#meth184)
  - [produceNewExecutable](#meth258)
  - [readByte](#meth236)
  - [readBytes](#meth235)
  - [readUInt16BE](#meth240)
  - [readUInt16LE](#meth237)
  - [readUInt32BE](#meth241)
  - [readUInt32LE](#meth238)
  - [readUInt64BE](#meth242)
  - [readUInt64LE](#meth239)
  - [rebase](#meth183)
  - [refreshView](#meth213)
  - [removeBookmarkAtAddress](#meth260)
  - [removeColorAtAddress](#meth234)
  - [removeTagAtAddress](#meth218)
  - [renameBookmarkAtAddress](#meth262)
  - [renameSegment](#meth186)
  - [requestBackgroundProcessStop](#meth176)
  - [saveDocument](#meth171)
  - [saveDocumentAt](#meth172)
  - [selectAddressRange](#meth203)
  - [setBookmarkAtAddress](#meth259)
  - [setColorAtAddress](#meth232)
  - [setCurrentAddress](#meth200)
  - [setDocumentName](#meth174)
  - [setExecutableFilePath](#meth181)
  - [setNameAtAddress](#meth210)
  - [setOperandFormat](#meth253)
  - [setOperandRelativeFormat](#meth254)
  - [tagIterator](#meth226)
  - [tagIteratorAtAddress](#meth222)
  - [waitForBackgroundProcessToEnd](#meth177)
  - [writeByte](#meth244)
  - [writeBytes](#meth243)
  - [writeUInt16BE](#meth248)
  - [writeUInt16LE](#meth245)
  - [writeUInt32BE](#meth249)
  - [writeUInt32LE](#meth246)
  - [writeUInt64BE](#meth250)
  - [writeUInt64LE](#meth247)
- [Class GlobalInformation](#class_anchor_GlobalInformation)
  - [getHopperMajorVersion](#meth266)
  - [getHopperMinorVersion](#meth267)
  - [getHopperRevisionNumber](#meth268)
  - [getHopperVersion](#meth269)

Here are all the public classes, and methods that you can use to script Hopper using Python.

Before using the scripting capabilities of Hopper, you need to understand the nature of a Hopper document. The basic concept is that it is a document constructed from Segments, each containing Sections of typed bytes. Let's consider a standard Mach-O file. It contains at least one segment of code (usually named TEXT) containing many bytes. Hopper attaches information to each bytes of each segments. At load time, all bytes are set to the type **TYPE_UNDEFINED**. Then, starting from the entry point, as Hopper follows the program flow it will set instructions to the type **TYPE_CODE**; if an instruction needs more than one byte, the following are set to **TYPE_NEXT**.

Using Python, you'll can manipulate the segments of disassembled files, retrieve information on bytes types, read or write data, create or modify label names, etc... You'll usually start by retrieving the current document, using the static method **Document.getCurrentDocument()**.\

------------------------------------------------------------------------

<span id="class_anchor_CallReference"></span>

Class CallReference

An object representing a call inside from / to a procedure.

<span id="meth6"></span>

type()

Returns the type of call. This is one of the value CALL_NONE, CALL_UNKNOWN, CALL_DIRECT, or CALL_OBJC.

<span id="meth7"></span>

fromAddress()

Source of the reference

<span id="meth8"></span>

toAddress()

Referenced address

<span id="class_anchor_LocalVariable"></span>

Class LocalVariable

A procedure's local variable.

<span id="meth10"></span>

name()

Name of the local variable

<span id="meth11"></span>

displacement()

Displacement on the stack

<span id="class_anchor_Tag"></span>

Class Tag

A Tag that could be applied to a specific address, a BasicBlock or a Procedure. Tags are built using the document.

<span id="meth15"></span>

getName()

Returns a string with the tag name.

<span id="class_anchor_Procedure"></span>

Class Procedure

This class represents a procedure, which is a collection of BasicBlocks. Please note that modifying the document (creating new procedure, or deleting an existing one), will result in a possible inconsistancy of the Python's Procedure object representation.\
Procedure class defines some constants:\
    **REGCLS_GENERAL_PURPOSE_REGISTER** = 2\
\
    **REGCLS_X86_FPU** = 3\
    **REGCLS_X86_MMX** = 4\
    **REGCLS_X86_SSE** = 5\
    **REGCLS_X86_AVX** = 6\
    **REGCLS_X86_CR** = 7\
    **REGCLS_X86_DR** = 8\
    **REGCLS_X86_SPECIAL** = 9\
    **REGCLS_X86_MEMMGMT** = 10\
    **REGCLS_X86_SEG** = 11\
\
    **REGCLS_ARM_VFP_SINGLE** = 3\
    **REGCLS_ARM_VFP_DOUBLE** = 4\
    **REGCLS_ARM_VFP_QUAD** = 5\
    **REGCLS_ARM_MEDIA** = 6\
    **REGCLS_ARM_SPECIAL** = 7\
\
    **REGIDX_X86_RAX** = 0\
    **REGIDX_X86_RCX** = 1\
    **REGIDX_X86_RDX** = 2\
    **REGIDX_X86_RBX** = 3\
    **REGIDX_X86_RSP** = 4\
    **REGIDX_X86_RBP** = 5\
    **REGIDX_X86_RSI** = 6\
    **REGIDX_X86_RDI** = 7\
    **REGIDX_X86_R8** = 8\
    **REGIDX_X86_R9** = 9\
    **REGIDX_X86_R10** = 10\
    **REGIDX_X86_R11** = 11\
    **REGIDX_X86_R12** = 12\
    **REGIDX_X86_R13** = 13\
    **REGIDX_X86_R14** = 14\
    **REGIDX_X86_R15** = 15\
    **REGIDX_X86_RIP** = 16\

<span id="meth19"></span>

getSegment()

Returns the segment this procedure belongs to.

<span id="meth20"></span>

getSection()

Returns the section this procedure belongs to.

<span id="meth21"></span>

getEntryPoint()

Returns the address of the entry point.

<span id="meth22"></span>

getBasicBlockCount()

Returns the total number of basic blocks.

<span id="meth23"></span>

getBasicBlock(index)

Get a BasicBlock object by index.

<span id="meth24"></span>

getBasicBlockAtAddress(addr)

Returns the basic block which contains an instruction starting at the given address, or None.

<span id="meth25"></span>

basicBlockIterator()

Iterate over all basic blocks of the procedure

<span id="meth26"></span>

getHeapSize()

Returns the heap size of the procedure in bytes.

<span id="meth27"></span>

getLocalVariableList()

Returns the list of all local variables.

<span id="meth28"></span>

addTag(tag)

Add a tag to the procedure.

<span id="meth29"></span>

removeTag(tag)

Remove the tag from the procedure.

<span id="meth30"></span>

hasTag(tag)

Returns True if the procedure has this tag.

<span id="meth31"></span>

getTagCount()

Returns the number of tags for this procedure.

<span id="meth32"></span>

getTagAtIndex(index)

Returns the Nth tag of the procedure.

<span id="meth33"></span>

tagIterator()

Iterate over all tags of the procedure

<span id="meth34"></span>

getTagList()

Returns a list a all tags for this procedure.

<span id="meth35"></span>

getAllCallers()

Returns a list of CallReference objects representing callers of this procedure.

<span id="meth36"></span>

getAllCallees()

Returns a list of CallReference objects representing all the places called by this procedure.

<span id="meth37"></span>

getAllCallerProcedures()

Returns a list of Procedure objects representing callers of this procedure.

<span id="meth38"></span>

getAllCalleeProcedures()

Returns a list of CallReference objects representing all the procedures called by this procedure.

<span id="meth39"></span>

hasLocalLabelAtAddress(addr)

Return True if there is a local label at a given address.

<span id="meth40"></span>

localLabelAtAddress(addr)

Return the local label name at a given address, or None if there is no label at this address.

<span id="meth41"></span>

setLocalLabelAtAddress(label,addr)

Set the local label for a given address.

<span id="meth42"></span>

declareLocalLabelAt(addr)

Create a local label at a given address, and return its name.

<span id="meth43"></span>

removeLocalLabelAtAddress(addr)

Remove a local label.

<span id="meth44"></span>

addressOfLocalLabel(label)

Return the address of the local label.

<span id="meth45"></span>

decompile()

Returns a string containing the pseudo-code of the procedure, or None if the decompilation is not possible.

<span id="meth46"></span>

signatureString()

Returns a string containing the signature of the procedure.

<span id="meth47"></span>

renameRegister(reg_cls,reg_idx,name)

Rename the register reg_idx, of class reg_cls to the provided name. The reg_cls argument is one of the REGCLS\_\* constants.

<span id="meth48"></span>

registerNameOverride(reg_cls,reg_idx)

Returns the name given to the register, if it has been previously renamed. Otherwise, returns None. The reg_cls argument is one of the REGCLS\_\* constants.

<span id="meth49"></span>

clearRegisterNameOverride(reg_cls,reg_idx)

Clear register renaming. The reg_cls argument is one of the REGCLS\_\* constants.

<span id="class_anchor_BasicBlock"></span>

Class BasicBlock

A BasicBlock is a set of instructions that is guaranteed to be executed in a whole, if the control flow reach the first instruction.

<span id="meth53"></span>

getProcedure()

Returns the Procedure object this BasicBlock belongs to.

<span id="meth54"></span>

getStartingAddress()

Returns the address of the first instruction of the BasicBlock.

<span id="meth55"></span>

getEndingAddress()

Returns the address following the last instruction of the BasicBlock.

<span id="meth56"></span>

getSuccessorCount()

Returns the number of successors for this BasicBlock.

<span id="meth57"></span>

getSuccessorIndexAtIndex(index)

Returns the BasicBlock index of the Nth successors.

<span id="meth58"></span>

getSuccessorAddressAtIndex(index)

Returns the BasicBlock address of the Nth successors.

<span id="meth59"></span>

addTag(tag)

Add a tag to the basic block.

<span id="meth60"></span>

removeTag(tag)

Remove the tag from the basic block.

<span id="meth61"></span>

hasTag(tag)

Returns True if the basic block has this tag.

<span id="meth62"></span>

getTagCount()

Return the number of tags for this basic block.

<span id="meth63"></span>

getTagAtIndex(index)

Return the Nth tag of the basic block.

<span id="meth64"></span>

tagIterator()

Iterate over all tags of the basic block

<span id="meth65"></span>

getTagList()

Return a list a all tags for this basic block.

<span id="class_anchor_Instruction"></span>

Class Instruction

This class represents a disassembled instruction. The class defines some constants, like **ARCHITECTURE_i386**, and **ARCHITECTURE_X86_64**

<span id="meth67"></span>

stringForArchitecture(t)

\[static\]

Helper method which converts one of the architecture value (**ARCHITECTURE_UNKNOWN**, **ARCHITECTURE_i386**, **ARCHITECTURE_X86_64**, **ARCHITECTURE_ARM**, **ARCHITECTURE_ARM_THUMB**, or **ARCHITECTURE_AARCH64**) to a string value.

<span id="meth68"></span>

getArchitecture()

Returns the architecture.

<span id="meth69"></span>

getInstructionString()

Return a strings representing the instruction.

<span id="meth70"></span>

getArgumentCount()

Returns the number of argument.

<span id="meth71"></span>

getRawArgument(index)

Returns the instruction argument, identified by an index. The argument is not modified by Hopper, and represents the raw ASM argument.

<span id="meth72"></span>

getFormattedArgument(index)

Returns the instruction argument, identified by an index. The argument may have been modified according to the user, or by Hopper if a specific pattern has been detected.

<span id="meth73"></span>

isAnInconditionalJump()

Returns True if the instruction represents an inconditional jump.

<span id="meth74"></span>

isAConditionalJump()

Returns True if the instruction represents a conditional jump.

<span id="meth75"></span>

getInstructionLength()

Returns the instruction length in byte.

<span id="class_anchor_Section"></span>

Class Section

This class represents a section of a segment.

<span id="meth79"></span>

getName()

Returns the name of the section.

<span id="meth80"></span>

getStartingAddress()

Returns the starting address of the section.

<span id="meth81"></span>

getLength()

Returns the length, in bytes, of the section.

<span id="meth82"></span>

getFlags()

Returns the flags of the section.

<span id="class_anchor_Segment"></span>

Class Segment

This class represents a segment of a disassembled file. The class defines some values that are used as the type of bytes of the disassembled file.\
    **TYPE_UNDEFINED** : an undefined byte\
    **TYPE_OUTSIDE** : the byte is not in a mapped section\
    **TYPE_NEXT** : a byte that is part of a larger data type (ex, the second byte of a 4 bytes integer...)\
    **TYPE_INT8** : an integer of a single byte\
    **TYPE_INT16** : an integer of 2 bytes\
    **TYPE_INT32** : an integer of 4 bytes\
    **TYPE_INT64** : an integer of 8 bytes\
    **TYPE_ASCII** : an ASCII string\
    **TYPE_ALIGN** : an alignment\
    **TYPE_UNICODE** : an UNICODE string\
    **TYPE_CODE** : an instruction\
    **TYPE_PROCEDURE** : a procedure\
\
The class defines the constant **BAD_ADDRESS** which is returned by some methods when the requested information is incorrect.

<span id="meth83"></span>

stringForType(t)

\[static\]

Helper method that converts one of the type value (**TYPE_UNDEFINED**, **TYPE_NEXT**, ...) to a string value.

<span id="meth87"></span>

getName()

Returns the name of the segment.

<span id="meth88"></span>

getStartingAddress()

Returns the starting address of the segment.

<span id="meth89"></span>

getLength()

Returns the length, in bytes, of the segment.

<span id="meth90"></span>

getFileOffset()

Returns the file offset of the beginning of the segment.

<span id="meth91"></span>

getFileOffsetForAddress(addr)

Returns the file offset of a particular address.

<span id="meth92"></span>

getSectionCount()

Returns the number of section this segment contains.

<span id="meth93"></span>

getSection(index)

Returns a section by index. The returned object is an instance of the Section class. If the index of not in the range \[0;count\[, the function returns None.

<span id="meth94"></span>

getSectionsList()

Returns a list containing all the sections.

<span id="meth95"></span>

getSectionIndexAtAddress(addr)

Returns the section index for a particular address.

<span id="meth96"></span>

getSectionAtAddress(addr)

Returns the section for a particular address.

<span id="meth97"></span>

readBytes(addr,length)

Read bytes at a given address range. Returns False if the byte is read outside of the segment.

<span id="meth98"></span>

readByte(addr)

Read a byte (between 0..255), read at a given address. Returns False if the byte is read outside of the segment.

<span id="meth99"></span>

readUInt16LE(addr)

Read a 16 bits little endian integer.

<span id="meth100"></span>

readUInt32LE(addr)

Read a 32 bits little endian integer.

<span id="meth101"></span>

readUInt64LE(addr)

Read a 64 bits little endian integer.

<span id="meth102"></span>

readUInt16BE(addr)

Read a 16 bits big endian integer.

<span id="meth103"></span>

readUInt32BE(addr)

Read a 32 bits big endian integer.

<span id="meth104"></span>

readUInt64BE(addr)

Read a 64 bits big endian integer.

<span id="meth105"></span>

writeBytes(addr,bytesStr)

Write bytes at a given address. Bytes are given as 'bytes'. Returns True if the writting has succeed.

<span id="meth106"></span>

writeByte(addr,value)

Write a byte at a given address. Returns True if the writting has succeed.

<span id="meth107"></span>

writeUInt16LE(addr,value)

Write a 16 bits little endian integer. Returns True if succeeded.

<span id="meth108"></span>

writeUInt32LE(addr,value)

Write a 32 bits little endian integer. Returns True if succeeded.

<span id="meth109"></span>

writeUInt64LE(addr,value)

Write a 64 bits little endian integer. Returns True if succeeded.

<span id="meth110"></span>

writeUInt16BE(addr,value)

Write a 16 bits big endian integer. Returns True if succeeded.

<span id="meth111"></span>

writeUInt32BE(addr,value)

Write a 32 bits big endian integer. Returns True if succeeded.

<span id="meth112"></span>

writeUInt64BE(addr,value)

Write a 64 bits big endian integer. Returns True if succeeded.

<span id="meth113"></span>

markAsUndefined(addr)

Mark the address as being undefined.

<span id="meth114"></span>

markRangeAsUndefined(addr,length)

Mark the address range as being undefined.

<span id="meth115"></span>

markAsCode(addr)

Mark the address as being code.

<span id="meth116"></span>

markAsProcedure(addr)

Mark the address as being a procedure.

<span id="meth117"></span>

markAsDataByteArray(addr,count)

Mark the address as being byte array.

<span id="meth118"></span>

markAsDataShortArray(addr,count)

Mark the address as being a short array.

<span id="meth119"></span>

markAsDataIntArray(addr,count)

Mark the address as being an int array.

<span id="meth120"></span>

isThumbAtAddress(addr)

Returns True is instruction at address addr is ARM Thumb mode.

<span id="meth121"></span>

setThumbModeAtAddress(addr)

Set the Thumb mode at the given address.

<span id="meth122"></span>

setARMModeAtAddress(addr)

Set the ARM mode at the given address.

<span id="meth123"></span>

getTypeAtAddress(addr)

Returns the type of the byte at a given address. The type can be **TYPE_UNDEFINED**, **TYPE_NEXT**, **TYPE_INT8**, ... The method will returns None if the address is outside the segment.

<span id="meth124"></span>

setTypeAtAddress(addr,length,typeValue)

Set the type of a byte range. The type must be **TYPE_UNDEFINED**, **TYPE_INT8**, ... You cannot use this method for alignments. Please use **makeAlignment** instead.

<span id="meth125"></span>

makeAlignment(addr,size)

Create an alignment at a given address so that the next address is a multiple of size. Size can only be 2, 4, 8, 16, 32 or 64.

<span id="meth126"></span>

getNextAddressWithType(addr,typeValue)

Returns the next address of a given type. The search begins at the given address, so the returned value can be the given address itself. If no address are found, the returned value is **BAD_ADDRESS**.

<span id="meth127"></span>

disassembleWholeSegment()

Disassemble the whole segment.

<span id="meth128"></span>

setNameAtAddress(addr,name)

Set the label name at a given address.

<span id="meth129"></span>

getNameAtAddress(addr)

Get the label name at a given address.

<span id="meth130"></span>

getDemangledNameAtAddress(addr)

Get the demangled label name at a given address.

<span id="meth131"></span>

getCommentAtAddress(addr)

Get the prefix comment at a given address.

<span id="meth132"></span>

setCommentAtAddress(addr,comment)

Set the prefix comment at a given address.

<span id="meth133"></span>

getInlineCommentAtAddress(addr)

Get the inline comment at a given address.

<span id="meth134"></span>

setInlineCommentAtAddress(addr,comment)

Set the inline comment at a given address.

<span id="meth135"></span>

getInstructionAtAddress(addr)

Get the disassembled instruction at a given address.

<span id="meth136"></span>

getReferencesOfAddress(addr)

Get the list of addresses that reference a given address.

<span id="meth137"></span>

getReferencesFromAddress(addr)

Get the list of addresses referenced by a given address.

<span id="meth138"></span>

addReference(addr,referenced)

Add a cross reference to the 'referenced' address from 'addr' address.

<span id="meth139"></span>

removeReference(addr,referenced)

Remove the cross reference to the 'referenced' address from 'addr' address.

<span id="meth140"></span>

getLabelCount()

Get the number of named addresses.

<span id="meth141"></span>

labelIterator()

Iterate over all the labels of a segment.

<span id="meth142"></span>

getLabelsList()

Returns a list with all the label of a segment.

<span id="meth143"></span>

getNamedAddresses()

Returns a list of all addresses with a label name. The list has the same order as the list returned by getLabelsList.

<span id="meth144"></span>

getProcedureCount()

Returns the number of procedures that has been defined in this segment.

<span id="meth145"></span>

getProcedureAtIndex(index)

Returns the Nth Procedure object of the segment.

<span id="meth146"></span>

getProcedureIndexAtAddress(address)

Returns the index of the procedure at a given address of the segment, or -1 if there is no procedure defined there.

<span id="meth147"></span>

getProcedureAtAddress(address)

Returns the Procedure object at a given address of the segment, or None if there is no procedure defined at there.

<span id="meth148"></span>

getInstructionStart(address)

Returns the lowest address value of the instruction found at a particular address. If the given address is in the middle of an instruction, Hopper will look back to find the first byte of this instruction.

<span id="meth149"></span>

getObjectLength(address)

Returns the length in bytes of the object at this address. The object can be an instruction, a data, etc.

<span id="meth150"></span>

isPartOfAnArray(address)

Returns True if the address is part of an array.

<span id="meth151"></span>

getArrayStartAddress(address)

Returns the array start address, or BAD_ADDRESS if not inside an array.

<span id="meth152"></span>

getArrayElementCount(address)

Returns the number of element in the array, or 0 if not inside an array.

<span id="meth153"></span>

getArrayElementAddress(address,index)

Returns the address of the element at the given index, or BAD_ADDRESS if not inside an array.

<span id="meth154"></span>

getArrayElementSize(address)

Returns the size in bytes of a single element of the array, or 0 if not inside an array.

<span id="meth155"></span>

getStringCount()

Returns the number of strings in the segment.

<span id="meth156"></span>

getStringAtIndex(index)

Return the nth string of the segment.

<span id="meth157"></span>

getStringAddressAtIndex(index)

Return the address of the nth string of the segment.

<span id="meth158"></span>

getStringsList()

Returns a list containing all the strings and there address as a tuple.

<span id="class_anchor_Document"></span>

Class Document

This class represents the disassembled document. A document is a set of segments.

<span id="meth162"></span>

newDocument()

\[static\]

Creates and returns a new empty document.

<span id="meth163"></span>

getCurrentDocument()

\[static\]

Returns the current document.

<span id="meth164"></span>

getAllDocuments()

\[static\]

Returns a list of all currently opened documents.

<span id="meth165"></span>

ask(msg)

\[static\]

Open a window containing a text field, and wait for the user to give a string value. Returns the string, or returns None if the Cancel button is hit.

<span id="meth166"></span>

askFile(msg,path,save)

\[static\]

Open a file dialog with a specified title, in order to select a file. The 'save' parameter allows you to choose between on 'open' or a 'save' dialog.

<span id="meth167"></span>

askDirectory(msg,path)

\[static\]

Open a file dialog with a specified title, in order to select a directory.

<span id="meth168"></span>

message(msg,buttons)

\[static\]

Open a window containing a text field and a set of buttons. The 'Buttons' parameter is a list of strings. The function returns the index of the clicked button.

<span id="meth169"></span>

closeDocument()

Close the document.

<span id="meth170"></span>

loadDocumentAt(path)

Load a document at a given path.

<span id="meth171"></span>

saveDocument()

Save the document.

<span id="meth172"></span>

saveDocumentAt(path)

Save the document at a given path.

<span id="meth173"></span>

getDocumentName()

Returns the document display name.

<span id="meth174"></span>

setDocumentName(name)

Set the document display name.

<span id="meth175"></span>

backgroundProcessActive()

Returns True if the background analysis is still running.

<span id="meth176"></span>

requestBackgroundProcessStop()

Request the background analysis to stop as soon as possible, and wait for its termination.

<span id="meth177"></span>

waitForBackgroundProcessToEnd()

Wait until the background analysis is ended.

<span id="meth178"></span>

assemble(instr,address,syntax)

Assemble an instruction, and returns the bytes as an array. The instruction is NOT injected in the document: the address given to the function is used to encode the instruction. You wan use the writeByte method to inject an assembled instruction. The first argument is the instruction to be assembled. The second is the address of the instruction. The last parameter is the syntax variant index. For the Intel processor, syntax = 0 for Intel syntax, and 1 for AT&T syntax.

<span id="meth179"></span>

getDatabaseFilePath()

Returns the path of the current Hopper database for this document (the HOP file).

<span id="meth180"></span>

getExecutableFilePath()

Returns the path of the executable being analyzed.

<span id="meth181"></span>

setExecutableFilePath(path)

Set the path of the executable being analyzed.

<span id="meth182"></span>

log(msg)

Display a string message into the log window of the document.

<span id="meth183"></span>

rebase(new_base_address)

Change the file base address.

<span id="meth184"></span>

newSegment(start_address,length)

Create a new segment of 'length' bytes starting at 'start_address'.

<span id="meth185"></span>

deleteSegment(seg_index)

Delete the segment at a given index. Return True if succeeded.

<span id="meth186"></span>

renameSegment(seg_index,name)

Rename the segment at a given index. Return True if succeeded.

<span id="meth187"></span>

getSegmentCount()

Returns the number of segment the document contains.

<span id="meth188"></span>

getSegment(index)

Returns a segment by index. The returned object is an instance of the Segment class. If the index of not in the range \[0;count\[, the function returns None.

<span id="meth189"></span>

getSegmentByName(name)

Returns a segment by name. Return None if no segment with this name was found. If multiple segments have this name, the first one is returned.

<span id="meth190"></span>

getSectionByName(name)

Returns a section by name. Return None if no segment with this name was found. If multiple sections have this name, the first one is returned.

<span id="meth191"></span>

getSegmentsList()

Returns a list containing all the segments.

<span id="meth192"></span>

getSegmentIndexAtAddress(addr)

Returns the segment index for a particular address.

<span id="meth193"></span>

getSegmentAtAddress(addr)

Returns the segment for a particular address.

<span id="meth194"></span>

getSectionAtAddress(addr)

Returns the section for a particular address.

<span id="meth195"></span>

getCurrentSegmentIndex()

Returns the segment index where the cursor is. Returns -1 if the current segment cannot be located.

<span id="meth196"></span>

getCurrentSegment()

Returns the segment where the cursor is. Returns None if the current segment cannot be located.

<span id="meth197"></span>

getCurrentSection()

Returns the section where the cursor is. Returns None if the current section cannot be located.

<span id="meth198"></span>

getCurrentProcedure()

Returns the Procedure object where the cursor is. Returns None if there is no procedure there.

<span id="meth199"></span>

getCurrentAddress()

Returns the address where the cursor currently is.

<span id="meth200"></span>

setCurrentAddress(addr)

Set the address where the cursor currently is.

<span id="meth201"></span>

getSelectionAddressRange()

Returns a list, containing two addresses. Those address represents the range of bytes covered by the selection.

<span id="meth202"></span>

moveCursorAtAddress(addr)

Move the cursor at a given address.

<span id="meth203"></span>

selectAddressRange(addrRange)

Select a range of byte. The awaited argument is a list containing exactly two address.

<span id="meth204"></span>

getFileOffsetFromAddress(addr)

Returns the file offset corresponding to the given address.

<span id="meth205"></span>

getAddressFromFileOffset(offset)

Returns the address corresponding to the given file offset.

<span id="meth206"></span>

is64Bits()

Returns True if the disassembled document is interpreted as a 64 bits binary.

<span id="meth207"></span>

getEntryPoint()

Returns the entry point of the document.

<span id="meth208"></span>

moveCursorAtEntryPoint()

Move the cursor at the entry point.

<span id="meth209"></span>

getHighlightedWord()

Returns the word that is currently highlighted in the assembly view.

<span id="meth210"></span>

setNameAtAddress(addr,name)

Set the label name at a given address.

<span id="meth211"></span>

getNameAtAddress(addr)

Get the label name at a given address.

<span id="meth212"></span>

getAddressForName(name)

Get the address associated to a given name.

<span id="meth213"></span>

refreshView()

Force the assembly view to be refresh.

<span id="meth214"></span>

moveCursorOneLineDown()

Move the current line down, and remove the multiselection if needed. Returns True if cursor moved.

<span id="meth215"></span>

moveCursorOneLineUp()

Move the current line up, and remove the multiselection if needed. Returns True if cursor moved.

<span id="meth216"></span>

getRawSelectedLines()

Returns a list of strings corresponding to the current selection.

<span id="meth217"></span>

addTagAtAddress(tag,addr)

Add a tag at a particular address.

<span id="meth218"></span>

removeTagAtAddress(tag,addr)

Remove the tag at a particular address.

<span id="meth219"></span>

hasTagAtAddress(tag,addr)

Returns True if the tag is present at this address.

<span id="meth220"></span>

getTagCountAtAddress(addr)

Returns the number of tags at a given address.

<span id="meth221"></span>

getTagAtAddressByIndex(addr,index)

Returns the Nth tag present at a given address.

<span id="meth222"></span>

tagIteratorAtAddress(addr)

Iterates over all tags present at a given address.

<span id="meth223"></span>

getTagListAtAddress(addr)

Returns the list of all tags present at a given address

<span id="meth224"></span>

getTagCount()

Returns the total number of tags available.

<span id="meth225"></span>

getTagAtIndex(index)

Returns a Tag object, or None if the index does not exists.

<span id="meth226"></span>

tagIterator()

Iterate over all the tags.

<span id="meth227"></span>

getTagList()

Returns a list of all tags.

<span id="meth228"></span>

buildTag(name)

Build a tag with a given name. If a tag with the same name already exists, it return the existing tag.

<span id="meth229"></span>

getTagWithName(name)

Returns a Tag object if a tag with this name already exists, or None.

<span id="meth230"></span>

destroyTag(tag)

Remove the tag from every location, and delete it.

<span id="meth231"></span>

hasColorAtAddress(addr)

Returns True if a color has been defined at the given address.

<span id="meth232"></span>

setColorAtAddress(color,addr)

Sets the color at a given address. The color is a 32bits integer representing the hexadecimal color in the form \#AARRGGBB.

<span id="meth233"></span>

getColorAtAddress(addr)

Returns the color at a given address. The color is a 32bits integer representing the hexadecimal color in the form \#AARRGGBB.

<span id="meth234"></span>

removeColorAtAddress(addr)

Remove the color at a given address.

<span id="meth235"></span>

readBytes(addr,length)

Read bytes from a mapped segment, and return a string. Returns False if no segments was found for this range.

<span id="meth236"></span>

readByte(addr)

Read a byte from a mapped segment. Returns False if no segments was found for this address.

<span id="meth237"></span>

readUInt16LE(addr)

Read a 16 bits little endian integer from a mapped segment. Returns False if no segments was found for this address.

<span id="meth238"></span>

readUInt32LE(addr)

Read a 32 bits little endian integer from a mapped segment. Returns False if no segments was found for this address.

<span id="meth239"></span>

readUInt64LE(addr)

Read a 64 bits little endian integer from a mapped segment. Returns False if no segments was found for this address.

<span id="meth240"></span>

readUInt16BE(addr)

Read a 16 bits big endian integer from a mapped segment. Returns False if no segments was found for this address.

<span id="meth241"></span>

readUInt32BE(addr)

Read a 32 bits big endian integer from a mapped segment. Returns False if no segments was found for this address.

<span id="meth242"></span>

readUInt64BE(addr)

Read a 64 bits bif endian integer from a mapped segment. Returns False if no segments was found for this address.

<span id="meth243"></span>

writeBytes(addr,byteStr)

Write bytes to a mapped segment. Bytes are given as a string. Returns False if no segments was found for this range.

<span id="meth244"></span>

writeByte(addr,value)

Write a byte to a mapped segment. Returns True if succeeded.

<span id="meth245"></span>

writeUInt16LE(addr,value)

Write a 16 bits little endian integer to a mapped segment. Returns True if succeeded.

<span id="meth246"></span>

writeUInt32LE(addr,value)

Write a 32 bits little endian integer to a mapped segment. Returns True if succeeded.

<span id="meth247"></span>

writeUInt64LE(addr,value)

Write a 64 bits little endian integer to a mapped segment. Returns True if succeeded.

<span id="meth248"></span>

writeUInt16BE(addr,value)

Write a 16 bits big endian integer to a mapped segment. Returns True if succeeded.

<span id="meth249"></span>

writeUInt32BE(addr,value)

Write a 32 bits big endian integer to a mapped segment. Returns True if succeeded.

<span id="meth250"></span>

writeUInt64BE(addr,value)

Write a 64 bits big endian integer to a mapped segment. Returns True if succeeded.

<span id="meth251"></span>

getOperandFormat(addr,index)

Returns the format requested by the user for a given intruction operand.

<span id="meth252"></span>

getOperandFormatRelativeTo(addr,index)

Returns the address to which the format is relative. Usually used for FORMAT_ADDRESS_DIFF format.

<span id="meth253"></span>

setOperandFormat(addr,index,fmt)

Set the format of a given intruction operand.

<span id="meth254"></span>

setOperandRelativeFormat(addr,relto,index,fmt)

Set the relative format of a given intruction operand. This version allows one to provide an address used for the relative formats, like FORMAT_ADDRESS_DIFF.

<span id="meth255"></span>

getInstructionStart(address)

Returns the lowest address value of the instruction found at a particular address. If the given address is in the middle of an instruction, Hopper will look back to find the first byte of this instruction.

<span id="meth256"></span>

getObjectLength(address)

Returns the length in bytes of the object at this address. The object can be an instruction, a data, etc.

<span id="meth257"></span>

generateObjectiveCHeader()

Returns a bytearray object containing the generated Objective-C header extracted from the file's metadata.

<span id="meth258"></span>

produceNewExecutable(remove_sig=False)

Produces a new executable including all the modifications. The optional argument is a boolean indicating if the signature is to be removed in the case of a Mach-O file. Returns a string containing the produced executable.

<span id="meth259"></span>

setBookmarkAtAddress(address,name=None)

Set a bookmark at a given address, with an optional name.

<span id="meth260"></span>

removeBookmarkAtAddress(address)

Removes a bookmark at a given address.

<span id="meth261"></span>

hasBookmarkAtAddress(address)

Returns True if a bookmark is present at a given address.

<span id="meth262"></span>

renameBookmarkAtAddress(address,name)

Changes the name of an existing bookmark.

<span id="meth263"></span>

findBookmarkWithName(name)

Returns a list of all bookmarks of a given name.

<span id="meth264"></span>

getBookmarkName(address)

Returns the name of a bookmark at a given address.

<span id="meth265"></span>

getBookmarks()

Returns a list of all the addresses with a bookmark.

<span id="class_anchor_GlobalInformation"></span>

Class GlobalInformation

An object containing various information about the current version of Hopper.

<span id="meth266"></span>

getHopperMajorVersion()

\[static\]

Returns the major version number. If Hopper is at version 4.1.2, it'll return "4".

<span id="meth267"></span>

getHopperMinorVersion()

\[static\]

Returns the minor version number. If Hopper is at version 4.1.2, it'll return "1".

<span id="meth268"></span>

getHopperRevisionNumber()

\[static\]

Returns the revision version number. If Hopper is at version 4.1.2, it'll return "2".

<span id="meth269"></span>

getHopperVersion()

\[static\]

Returns a string with the complete Hopper's version number (ie, something like "4.1.2")
