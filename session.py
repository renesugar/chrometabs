from __future__ import annotations
from typing import TypeVar, Generic, NewType, Callable, Iterable, Any, Tuple
from logging import Logger
from enum import Enum
from timeit import default_timer as timer

import sys
import os
import struct
import weakref

from pickle import Pickle
from constants import SizeOf, const, uint16, int16, uint32, int32, uint64, int64

# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Copyright (c) 2020 Rene Sugar. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE.chromium file.

#------------------------------------------------------------------------------

# SessionCommand contains a command id and arbitrary chunk of data. The id
# and chunk of data are specific to the service creating them.
#
# Both TabRestoreService and SessionService use SessionCommands to represent
# state on disk.
#
# There are two ways to create a SessionCommand:
# . Specificy the size of the data block to create. This is useful for
#   commands that have a fixed size.
# . From a pickle, this is useful for commands whose length varies.
class SessionCommand:
  def __init__(self, a=None, b=None):
    # Creates a session command with the specified id. This allocates a buffer
    # of size |size| that must be filled via contents().
    if type(a) == int and type(b) == int:
      self.id_ = a
      self.contents_ = bytearray(b)
    # Convenience constructor that creates a session command with the specified
    # id whose contents is populated from the contents of pickle.
    elif type(a) == int and isinstance(b, Pickle):
      self.id_ = a
      if b.size() >= sys.maxsize:
        raise ValueError('SessionCommand: invalid size for pickle parameter')
      v = memoryview(b.data())
      data_len = b.size()
      self.contents_ = bytearray(data_len)
      self.contents_[0 : data_len] = v[0:data_len]
    else:
      raise ValueError('SessionCommand: unknown __init__ parameter')
  # The contents of the command.
  def contents(self) -> memoryview:
    return memoryview(self.contents_)
  # Identifier for the command.
  def command_id(self) -> int:
    return self.id_

  # Size of data.
  def size(self) -> int:
    return len(self.contents_)

  # Returns the contents as a pickle. It is up to the caller to delete the
  # returned Pickle. The returned Pickle references the underlying data of
  # this SessionCommand. If you need it to outlive the command, copy the
  # pickle.
  def PayloadAsPickle(self) -> Pickle:
    return Pickle(self.contents_)

#------------------------------------------------------------------------------

# // The file header is the first bytes written to the file,
# // and is used to identify the file as one written by us.
# struct FileHeader {
#   int32 signature;
#   int32 version;
# };

# SessionFileReader ----------------------------------------------------------

# SessionFileReader is responsible for reading the set of SessionCommands that
# describe a Session back from a file. SessionFileRead does minimal error
# checking on the file (pretty much only that the header is valid).

class SessionFileReader:
  def __init__(self, path):
    self.byteorder_ = '>' if sys.byteorder == "big" else '<'
    self.errored_ = False
    self.buffer_ = bytearray(const.kFileReadBufferSize)
    self.buffer_position_ = 0
    self.available_count_ = 0
    self.file_ = None
    if os.path.isfile(path) == False:
      raise ValueError("file '%s' not found" % (path,))
    self.file_ = open(path, 'rb')

  def __del__(self):
    if self.file_ is not None and self.file_.closed == False:
      self.file_.close()

  # Shifts the unused portion of buffer_ to the beginning and fills the
  # remaining portion with data from the file. Returns false if the buffer
  # couldn't be filled. A return value of false only signals an error if
  # errored_ is set to true.
  def __FillBuffer(self) -> bool:
    if self.available_count_ > 0 and self.buffer_position_ > 0:
      # Shift buffer to beginning.
      self.buffer_[0:self.available_count_] = self.buffer_[self.buffer_position_:self.buffer_position_ + self.available_count_]
    self.buffer_position_ = 0
    if self.buffer_position_ + self.available_count_ >= len(self.buffer_):
      raise ValueError('FillBuffer: out of space')
    to_read : int = len(self.buffer_) - self.available_count_
    v = memoryview(self.buffer_)
    read_count : int = self.file_.readinto(v[self.available_count_:self.available_count_+to_read])
    if read_count is None:
      self.errored_ = True
      return False
    if read_count == 0:
      return False
    self.available_count_ += read_count
    return True

  # Reads a single command, returning it. A return value of None indicates
  # either there are no commands, or there was an error. Use errored_ to
  # distinguish the two. If None is returned, and there is no error, it means
  # the end of file was successfully reached.
  def __ReadCommand(self) -> SessionCommand:
    # Make sure there is enough in the buffer for the size of the next command.
    if self.available_count_ < SizeOf.SIZE_TYPE:
      if False == self.__FillBuffer():
        return None
      if self.available_count_ < SizeOf.SIZE_TYPE:
        # Still couldn't read a valid size for the command, assume write was
        # incomplete and return None.
        return None

    # Get the size of the command.
    command_size : int = struct.unpack_from(self.byteorder_ + 'H', self.buffer_, self.buffer_position_)
    self.buffer_position_ += SizeOf.UINT16
    self.available_count_ -= SizeOf.UINT16

    if command_size[0] == 0:
      # Empty command. Shouldn't happen if write was successful, fail.
      return None

    # Make sure buffer has the complete contents of the command.
    if command_size[0] > self.available_count_:
      if command_size[0] > len(self.buffer_):
        capacity = len(self.buffer_)
        new_capacity = (command_size[0] / const.kFileReadBufferSize + 1) * const.kFileReadBufferSize
        extend_length = int(new_capacity - capacity)
        self.buffer_.extend(bytearray(extend_length))
      if False == self.__FillBuffer():
        return None
      if command_size[0] > self.available_count_:
        # Again, assume the file was ok, and just the last chunk was lost.
        return None

    command_id : int = struct.unpack_from(self.byteorder_ + 'B', self.buffer_, self.buffer_position_)
    # NOTE: command_size includes the size of the id, which is not part of
    # the contents of the SessionCommand.
    if command_size[0] > SizeOf.ID_TYPE:
      v = memoryview(self.buffer_)
      offset = self.buffer_position_ + SizeOf.ID_TYPE
      payload_size = (command_size[0] - SizeOf.ID_TYPE)
      command = SessionCommand(command_id[0], Pickle(v[offset : offset + payload_size]))
    else:
      command = SessionCommand(command_id[0], bytearray())
    self.buffer_position_ += command_size[0]
    self.available_count_ -= command_size[0]
    return command


  # Reads the contents of the file specified in the constructor, returning
  # true on success. It is up to the caller to free all SessionCommands
  # added to commands.
  def Read(self, session_type : int) -> Tuple[bool, list]:
    if self.file_ is None or self.file_.closed == True:
      return (False, [])
    if self.file_.readable() == False:
      return (False, [])
    header = bytearray(SizeOf.FILEHEADER)
    read_count : int = 0
    read_count = self.file_.readinto(header)
    if read_count != SizeOf.FILEHEADER:
      return (False, [])

    header_signature = struct.unpack_from(self.byteorder_ + 'I', header, 0)
    header_version = struct.unpack_from(self.byteorder_ + 'I', header, SizeOf.INT32)

    # Check header signature and header version
    if header_signature[0] != const.kFileSignature or header_version[0] != const.kFileCurrentVersion:
      return (False, [])

    read_commands = []
    command = self.__ReadCommand()
    while (command is not None) and (not self.errored_):
      read_commands.append(command)
      command = self.__ReadCommand()
    
    return (not self.errored_, read_commands)
