from __future__ import annotations
import sys
import struct
from typing import TypeVar, Generic, NewType, Callable, Iterable, Any, Tuple
from logging import Logger
from enum import Enum

from constants import SizeOf, const, uint16, int16, uint32, int32, uint64, int64

import string
printable = string.ascii_letters + string.digits + string.punctuation + ' '
def hex_escape(s):
  return ''.join(chr(c) if chr(c) in printable else r'\x{0:02x}'.format(c) for c in s)

# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Copyright (c) 2020 Rene Sugar. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE.chromium file.

# Aligns 'i' by rounding it up to the next multiple of 'alignment'
def AlignInt(i : int, alignment : int) -> int:
  return i + (alignment - (i % alignment)) % alignment

# PickleIterator reads data from a Pickle. The Pickle object must remain valid
# while the PickleIterator object is in use.
class PickleIterator:
  def __init__(self, pickle):
    # Pointers to the Pickle data.
    v = memoryview(pickle.data())
    self.bytes_ = v[pickle.payload():]
    self.read_ptr_ = 0
    self.read_end_ptr_ = len(self.bytes_)
    self.byteorder_ = '>' if sys.byteorder == "big" else '<'

  def GetReadPointerAndAdvance(self, num_bytes : int, size_element : int = 0) -> int:
    if size_element != 0:
      num_bytes *= size_element
    if (num_bytes < 0) or ((self.read_end_ptr_ - self.read_ptr_) < num_bytes):
      return None
    current_read_ptr = self.read_ptr_
    self.read_ptr_ += AlignInt(num_bytes, SizeOf.UINT32)
    return current_read_ptr

  # Skips bytes in the read buffer and returns true if there are at least
  # num_bytes available. Otherwise, does nothing and returns false.
  def SkipBytes(self, num_bytes : int) -> bool:
    # In Python, returning offset instead of a pointer
    if self.GetReadPointerAndAdvance(num_bytes) is None:
      return False
    else:
      return True

  # Methods for reading the payload of the Pickle. To read from the start of
  # the Pickle, create a PickleIterator from a Pickle. If successful, these
  # methods return true. Otherwise, false is returned to indicate that the
  # result could not be extracted.
  def ReadBool(self) -> Tuple[bool, bool]:
    read_from : int = self.GetReadPointerAndAdvance(SizeOf.BOOL)
    if read_from is None:
      return (False, False)
    result : bool = struct.unpack_from(self.byteorder_ + '?', self.bytes_, read_from)
    return (True, result[0])

  def ReadInt(self) -> Tuple[bool, int]:
    read_from : int = self.GetReadPointerAndAdvance(SizeOf.INT)
    if read_from is None:
      return (False, False)
    result : int = struct.unpack_from(self.byteorder_ + 'i', self.bytes_, read_from)
    return (True, result[0])

  def ReadLong(self) -> Tuple[bool, int]:
    read_from : int = self.GetReadPointerAndAdvance(SizeOf.LONG)
    if read_from is None:
      return (False, False)
    result : int = struct.unpack_from(self.byteorder_ + 'l', self.bytes_, read_from)
    return (True, result[0])

  def ReadUInt16(self) -> Tuple[bool, int]:
    read_from : int = self.GetReadPointerAndAdvance(SizeOf.UINT16)
    if read_from is None:
      return (False, False)
    result : int = struct.unpack_from(self.byteorder_ + 'h', self.bytes_, read_from)
    return (True, result[0])

  def ReadUInt32(self) -> Tuple[bool, int]:
    read_from : int = self.GetReadPointerAndAdvance(SizeOf.UINT32)
    if read_from is None:
      return (False, False)
    result : int = struct.unpack_from(self.byteorder_ + 'I', self.bytes_, read_from)
    return (True, result[0])

  def ReadInt64(self) -> Tuple[bool, int]:
    read_from : int = self.GetReadPointerAndAdvance(SizeOf.INT64)
    if read_from is None:
      return (False, False)
    result : int = struct.unpack_from(self.byteorder_ + 'q', self.bytes_, read_from)
    return (True, result[0])

  def ReadUInt64(self) -> Tuple[bool, int]:
    read_from : int = self.GetReadPointerAndAdvance(SizeOf.UINT64)
    if read_from is None:
      return (False, False)
    result : int = struct.unpack_from(self.byteorder_ + 'Q', self.bytes_, read_from)
    return (True, result[0])

  # Chromium uses a C string for binary data
  def ReadBinaryString(self) -> Tuple[bool, bytes]:
    status, length = self.ReadInt()
    if status == False:
      return False
    read_from : int = self.GetReadPointerAndAdvance(length)
    if read_from is None:
      return False
    
    if length != 0:
      return (True, self.bytes_[read_from : read_from + length].tobytes())
    else:
      return (True, bytes())

  def ReadString(self) -> Tuple[bool, str]:
    status, length = self.ReadInt()
    if status == False:
      return False
    read_from : int = self.GetReadPointerAndAdvance(length)
    if read_from is None:
      return False
    
    if length != 0:
      return (True, self.bytes_[read_from : read_from + length].tobytes().decode('utf-8'))
    else:
      return (True, '')

  def ReadWString(self) -> Tuple[bool, str]:
    status, length = self.ReadInt()
    if status == False:
      return False
    read_from : int = self.GetReadPointerAndAdvance(length, SizeOf.UINT32)
    if read_from is None:
      return False
    
    if length != 0:
      if self.byteorder_ == '<':
        codec_name = 'utf-32-le'
      else:
        codec_name = 'utf-32-be'
      return (True, self.bytes_[read_from : read_from + length*SizeOf.UINT32].tobytes().decode(codec_name))
    else:
      return (True, '')

  def ReadString16(self) -> Tuple[bool, str]:
    status, length = self.ReadInt()
    if status == False:
      return False
    read_from : int = self.GetReadPointerAndAdvance(length, SizeOf.UINT16)
    if read_from is None:
      return False
    
    if length != 0:
      if self.byteorder_ == '<':
        codec_name = 'utf-16-le'
      else:
        codec_name = 'utf-16-be'
      return (True, self.bytes_[read_from : read_from + length*SizeOf.UINT16].tobytes().decode(codec_name))
    else:
      return (True, '')

  # Safer version of ReadInt() checks for the result not being negative.
  # Use it for reading the object sizes.
  def ReadLength(self) -> Tuple[bool, int]:
    status, result = self.ReadInt()
    return ((status and result >= 0), result)

  def ReadBytes(self, length : int) -> Tuple[bool, bytes]:
    if length < 0:
      raise ValueError('ReadBytes negative length')
    if length == 0:
      return (True, bytearray())

    read_from : int = self.GetReadPointerAndAdvance(length)
    if read_from is None:
      return (False, False)

    return (True, self.bytes_[read_from : read_from + length].tobytes())

  def ReadData(self) -> Tuple[bool, bytearray]:
    status, length = self.ReadLength()
    if status == False:
      return (False, bytearray())

    return self.ReadBytes(length)

# Payload follows after allocation of Header (header size is customizable).
# struct Header {
#   uint32 payload_size;  # Specifies the size of the payload.
# };

# This class provides facilities for basic binary value packing and unpacking.
#
# The Pickle class supports appending primitive values (ints, strings, etc.)
# to a pickle instance.  The Pickle instance grows its internal memory buffer
# dynamically to hold the sequence of primitive values.   The internal memory
# buffer is exposed as the "data" of the Pickle.  This "data" can be passed
# to a Pickle object to initialize it for reading.
#
# When reading from a Pickle object, it is important for the consumer to know
# what value types to read and in what order to read them as the Pickle does
# not keep track of the type of data written to it.
#
# The Pickle's data has a header which contains the size of the Pickle's
# payload.  It can optionally support additional space in the header.  That
# space is controlled by the header_size parameter passed to the Pickle
# constructor.
#
class Pickle:
  def __init__(self,a=None,b=None):
    self.byteorder_ = '>' if sys.byteorder == "big" else '<'
    if a==None and b==None:
       # Initialize a Pickle object using the default header size.
      self.header_ = bytearray(SizeOf.HEADER)
      self.header_size_ = SizeOf.HEADER
      self.capacity_ = 0
      self.variable_buffer_offset_ = 0
      self.Resize(const.kPayloadUnit)
      struct.pack_into(self.byteorder_ + 'I', self.header_, 0, 0)
    elif type(a)==int and b==None:
      # Initialize a Pickle object with the specified header size in bytes, which
      # must be greater-than-or-equal-to sizeof(Pickle::Header).  The header size
      # will be rounded up to ensure that the header size is 32bit-aligned.
      self.header_ = None
      self.header_size_ = AlignInt(int(a), SizeOf.UINT32)
      self.capacity_ = 0
      self.variable_buffer_offset_ = 0
      if self.header_size_ < SizeOf.HEADER:
        raise ValueError('header size less than minimum allowed')
      if self.header_size_ > const.kPayloadUnit:
        raise ValueError('header size is greater than current capacity')
      self.Resize(const.kPayloadUnit)
      struct.pack_into(self.byteorder_ + 'I', self.header_, 0, 0)
    elif (type(a)==bytes or type(a)==memoryview or type(a)==bytearray) and b==None:
      # Initializes a Pickle from a const block of data.  The data is not copied;
      # instead the data is merely referenced by this Pickle.  Only const methods
      # should be used on the Pickle when initialized this way.  The header
      # padding size is deduced from the data length.
      self.header_ = memoryview(a)
      self.header_size_ = 0
      self.capacity_ = const.kCapacityReadOnly
      self.variable_buffer_offset_ = 0
      data_len = len(self.header_)
      if data_len >= SizeOf.HEADER:
        payload_size : int = struct.unpack_from(self.byteorder_ + 'I', self.header_, 0)
        self.header_size_ = data_len - payload_size[0]

      if self.header_size_ > data_len:
        self.header_size_ = 0

      if (self.header_size_ != AlignInt(self.header_size_, SizeOf.UINT32)):
        # NOTE: This path is taken multiple times when processing a file produced by Chrome
        self.header_size_ = 0

      # If there is anything wrong with the data, we're not going to use it.
      if self.header_size_ == 0:
        self.header_ = None
    else:
      raise ValueError("Pickle: unknown parameter in constructor")

  # Resize the capacity, note that the input value should include the size of
  # the header: new_capacity = sizeof(Header) + desired_payload_capacity.
  # A realloc() failure will cause a Resize failure... and caller should check
  # the return result for true (i.e., successful resizing).
  def Resize(self, new_capacity : int) -> bool:
    new_capacity = AlignInt(new_capacity, const.kPayloadUnit)

    if self.capacity_ == const.kCapacityReadOnly:
      raise ValueError('readonly Pickle cannot be resized')

    if new_capacity == 0:
      self.header_ = bytearray(SizeOf.HEADER)
      self.header_size_ = SizeOf.HEADER
      self.capacity_ = 0
      self.variable_buffer_offset_ = 0
    elif new_capacity < self.capacity_:
      if self.header_ is not None:
        self.header_ = self.header_[0:new_capacity]
      else:
        self.header_ = bytearray(new_capacity)
    elif new_capacity == self.capacity_:
      if self.header_ is None:
        self.header_ = bytearray(new_capacity)
    else:
      if self.header_ is not None:
        extend_length = new_capacity - self.capacity_
        self.header_.extend(bytearray(extend_length))
      else:
        self.header_size_ = SizeOf.HEADER
        self.header_ = bytearray(new_capacity)
    self.capacity_ = new_capacity
    return True

  # Returns the size of the Pickle's data.
  def size(self) -> int:
    if self.header_ is None:
      return 0
    payload_size : int = struct.unpack_from(self.byteorder_ + 'I', self.header_, 0)
    return self.header_size_ + payload_size[0]

  # Returns the data for this Pickle.
  def data(self) -> memoryview:
    if self.header_ is None:
      return bytearray()
    return memoryview(self.header_)

  # The payload is the pickle data immediately following the header.
  def payload_size(self) -> int:
    payload_size : int = struct.unpack_from(self.byteorder_ + 'I', self.header_, 0)
    return payload_size[0]
  
  # Payload is uint32 aligned.
  def payload(self) -> int:
    # In Python, return the offset to the payload.
    # In C++, this is a pointer to the payload.
    return self.header_size_

  # Returns the address of the byte immediately following the currently valid
  # header + payload.
  def end_of_payload(self) -> int:
    # We must have a valid header_.
    if self.header_ is None:
      raise ValueError('header is not set')
    return self.payload() + self.payload_size()

  def capacity(self) -> int:
    return self.capacity_

  # Resizes the buffer for use when writing the specified amount of data. The
  # location that the data should be written at is returned, or NULL if there
  # was an error. Call EndWrite with the returned offset and the given length
  # to pad out for the next write.
  def BeginWrite(self, length : int) -> int:
    # write at a uint32-aligned offset from the beginning of the header
    payload_size : int = struct.unpack_from(self.byteorder_ + 'I', self.header_, 0)
    offset : int = AlignInt(payload_size[0], SizeOf.UINT32)

    new_size : int = offset + length
    needed_size : int = self.header_size_ + new_size
    if needed_size > self.capacity_:
      if False == self.Resize(max(self.capacity_ * 2, needed_size)):
        return None

    if length > const.kuint32max:
      raise ValueError('BeginWrite: length exceeds limit')

    struct.pack_into(self.byteorder_ + 'I', self.header_, 0, int(new_size))
    return self.payload() + offset

  # Completes the write operation by padding the data with NULL bytes until it
  # is padded. Should be paired with BeginWrite, but it does not necessarily
  # have to be called after the data is written.
  def EndWrite(self, dest, length : int):
    # Zero-pad to keep tools like valgrind from complaining about uninitialized
    # memory.
    if length % SizeOf.UINT32:
      self.header_[(dest + length) : (dest + length) + (SizeOf.UINT32 - (length % SizeOf.UINT32))] = bytearray(SizeOf.UINT32 - (length % SizeOf.UINT32))

  # "Bytes" is a blob with no length. The caller must specify the lenght both
  # when reading and writing. It is normally used to serialize PoD types of a
  # known size. See also WriteData.
  def WriteBytes(self, data, data_len : int) -> bool:
    if self.capacity_ == const.kCapacityReadOnly:
      raise ValueError('oops: pickle is readonly')
    dest = self.BeginWrite(data_len)
    if dest is None:
      return False

    v = memoryview(data)
    self.header_[dest : (dest + data_len)] = v[0:data_len]
    self.EndWrite(dest, data_len)
    return True

  # Methods for adding to the payload of the Pickle.  These values are
  # appended to the end of the Pickle's payload.  When reading values from a
  # Pickle, it is important to read them in the order in which they were added
  # to the Pickle.

  def WriteInt(self, value : int) -> bool:
    return self.WriteBytes(value.to_bytes(SizeOf.INT, sys.byteorder), SizeOf.INT)

  def WriteBool(self, value : bool) -> bool:
    return self.WriteInt(1 if value else 0)

  def WriteUInt16(self, value : uint16) -> bool:
    return self.WriteBytes(value.to_bytes(SizeOf.UINT16, sys.byteorder), SizeOf.UINT16)
  
  def WriteUInt32(self, value : uint32) -> bool:
    return self.WriteBytes(value.to_bytes(SizeOf.UINT32, sys.byteorder), SizeOf.UINT32)
  
  def WriteInt64(self, value : int64) -> bool:
    return self.WriteBytes(value.to_bytes(SizeOf.INT64, sys.byteorder), SizeOf.INT64)
  
  def WriteUInt64(self, value : uint64) -> bool:
    return self.WriteBytes(value.to_bytes(SizeOf.UINT64, sys.byteorder), SizeOf.UINT64)
  
  def WriteString(self, value : str) -> bool:
    # https://docs.python.org/3/library/codecs.html
    # utf-8, utf-16, utf-32, utf-16-be, utf-16-le, utf-32-be, utf-32-le
    data : bytes = value.encode('utf-8')
    if False == self.WriteInt(len(data)):
      return False
    return self.WriteBytes(data, len(data))

  def WriteWString(self, value : str) -> bool:
    # https://docs.python.org/3/library/codecs.html
    # utf-8, utf-16, utf-32, utf-16-be, utf-16-le, utf-32-be, utf-32-le
    if sys.byteorder == 'big':
      encoding = 'utf-32-be'
    else:
      encoding = 'utf-32-le'
    data : bytes = value.encode(encoding)
    if False == self.WriteInt(len(data)):
      return False
    return self.WriteBytes(data, len(data))

  def WriteString16(self, value : str) -> bool:
    # https://docs.python.org/3/library/codecs.html
    # utf-8, utf-16, utf-32, utf-16-be, utf-16-le, utf-32-be, utf-32-le
    if sys.byteorder == 'big':
      encoding = 'utf-16-be'
    else:
      encoding = 'utf-16-le'
    data : bytes = value.encode(encoding)
    if False == self.WriteInt(len(data)):
      return False
    return self.WriteBytes(data, len(data))

  # "Data" is a blob with a length. When you read it out you will be given the
  # length. See also WriteBytes.
  def WriteData(self, data, length : int) -> bool:
    if length < 0:
      return False
    if False == self.WriteInt(length):
      return False
    return self.WriteBytes(data, length)

  # Same as WriteData, but allows the caller to write directly into the
  # Pickle. This saves a copy in cases where the data is not already
  # available in a buffer. The caller should take care to not write more
  # than the length it declares it will. Use ReadData to get the data.
  # Returns NULL on failure.
  #
  # The returned pointer will only be valid until the next write operation
  # on this Pickle.
  def BeginWriteData(self, length : int) -> int:
    if self.variable_buffer_offset_ != 0:
      raise ValueError('There can only be one variable buffer in a Pickle')

    if length < 0:
      return None
    if False == self.WriteInt(length):
      return None

    data_ptr = self.BeginWrite(length)
    if data_ptr is None:
      return None

    self.variable_buffer_offset_ = data_ptr - SizeOf.INT

    # EndWrite doesn't necessarily have to be called after the write operation,
    # so we call it here to pad out what the caller will eventually write.
    self.EndWrite(data_ptr, length)
    return data_ptr

  # For Pickles which contain variable length buffers (e.g. those created
  # with BeginWriteData), the Pickle can
  # be 'trimmed' if the amount of data required is less than originally
  # requested.  For example, you may have created a buffer with 10K of data,
  # but decided to only fill 10 bytes of that data.  Use this function
  # to trim the buffer so that we don't send 9990 bytes of unused data.
  # You cannot increase the size of the variable buffer; only shrink it.
  # This function assumes that the length of the variable buffer has
  # not been changed.
  def TrimWriteData(self, new_length : int):
    # No variable length buffer
    if self.variable_buffer_offset_ == 0:
      return

    # Fetch the the variable buffer size
    cur_length : int = struct.unpack_from(self.byteorder_ + 'I', self.header_, self.variable_buffer_offset_)
    if new_length < 0 or new_length > cur_length[0]:
      raise ValueError('Invalid length in TrimWriteData.')

    # Update the payload size and variable buffer size
    payload_size : int = struct.unpack_from(self.byteorder_ + 'I', self.header_, 0)
    new_payload_size = payload_size[0] - (cur_length[0] - new_length)
    struct.pack_into(self.byteorder_ + 'I', self.header_, 0, int(new_payload_size))
    struct.pack_into(self.byteorder_ + 'I', self.header_, 0, int(new_length))

  # Find the end of the pickled data that starts at rstart.  Returns None
  # if the entire Pickle is not found in the given data range.
  def FindNext(self, header_size : int, start : int, end : int):
    if header_size != AlignInt(header_size, SizeOf.UINT32):
      raise ValueError('header size is not aligned')
    if header_size > const.kPayloadUnit:
      raise ValueError('header size is larger than kPayloadUnit')

    if (end - start) < SizeOf.HEADER:
      return None

    payload_size : int = struct.unpack_from(self.byteorder_ + 'I', start, 0)
    payload_base = start + header_size
    payload_end = payload_base + payload_size[0]
    if payload_end < payload_base:
      return None
    if payload_end > end:
      return None
    return payload_end
