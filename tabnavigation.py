from __future__ import annotations
from typing import TypeVar, Generic, NewType, Callable, Iterable, Any, Tuple
from logging import Logger
from enum import Enum, IntEnum
from timeit import default_timer as timer

import sys
import os
import struct
import weakref

from pickle import Pickle, PickleIterator
from constants import SizeOf, WebKitWebReferrerPolicy, PageTransition, const, uint16, int16, uint32, int32, uint64, int64

import urllib
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone

# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Copyright (c) 2020 Rene Sugar. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE.chromium file.

# chromium/content/public/common/referrer.h

# This struct holds a referrer URL, as well as the referrer policy to be
# applied to this URL. When passing around referrers that will eventually end
# up being used for URL requests, always use this struct.
class Referrer:
  def __init__(self, url : str, policy : WebKitWebReferrerPolicy):
    self.url_ : str = url
    self.policy_ : WebKitWebReferrerPolicy = policy

# A mask used for arbitrary boolean values needed to represent a
# NavigationEntry. Currently only contains HAS_POST_DATA.
#
# NOTE(akalin): We may want to just serialize |has_post_data_|
# directly.  Other bools (|is_overriding_user_agent_|) haven't been
# added to this mask.
class TypeMask(IntEnum):
  HAS_POST_DATA = 1

# TabNavigation  -------------------------------------------------------------

# TabNavigation is a "freeze-dried" version of NavigationEntry.  It
# contains the data needed to restore a NavigationEntry during
# session restore and tab restore, and it can also be pickled and
# unpickled.  It is also convertible to a sync protocol buffer for
# session syncing.
#
# Default copy constructor and assignment operator welcome.
class TabNavigation:
  def __init__(self):
    # Index in the NavigationController.
    self.index_ : int = -1
    # Member variables corresponding to NavigationEntry fields.
    self.unique_id_ : int = 0
    self.referrer_ : Referrer = None
    self.virtual_url_ : str = None
    self.title_ : str = None
    self.content_state_ : str = None
    self.transition_type_ : PageTransition = 0
    self.has_post_data_ : bool = False
    self.post_id_ : int64 = -1
    self.original_request_url_ : str = None
    self.is_overriding_user_agent_ : bool = False

    # Timestamp when the navigation occurred.
    self.timestamp_ : datetime = datetime.now()

  # Pickle order:
  #
  # index_
  # virtual_url_
  # title_
  # content_state_
  # transition_type_
  #
  # Added on later:
  #
  # type_mask (has_post_data_)
  # referrer_
  # original_request_url_
  # is_overriding_user_agent_

  def ReadFromPickle(self, iterator : PickleIterator) -> bool:
    status, self.index_ = iterator.ReadInt()
    if status == False:
      return False
    status, self.virtual_url_ = iterator.ReadString()
    if status == False:
      return False
    status, self.title_ = iterator.ReadString16()
    if status == False:
      return False
    status, self.content_state_ = iterator.ReadBinaryString()
    if status == False:
      return False
    status, self.transition_type_ = iterator.ReadInt()
    if status == False:
      return False

    # type_mask did not always exist in the written stream. As such, we
    # don't fail if it can't be read.
    type_mask : int = 0
    has_type_mask : bool = False
    has_type_mask, type_mask = iterator.ReadInt()

    if has_type_mask == True:
      self.has_post_data_ = type_mask & TypeMask.HAS_POST_DATA
      # the "referrer" property was added after type_mask to the written
      # stream. As such, we don't fail if it can't be read.
      referrer_spec : str = None
      status, referrer_spec = iterator.ReadString()
      if status == False:
        referrer_spec = ''
      # The "referrer policy" property was added even later, so we fall back to
      # the default policy if the property is not present.
      policy : WebKitWebReferrerPolicy = WebKitWebReferrerPolicy.WebReferrerPolicyDefault
      status, policy = iterator.ReadInt()
      if status == True:
        pass
      else:
        policy = WebKitWebReferrerPolicy.WebReferrerPolicyDefault
      self.referrer_ = Referrer(referrer_spec, policy)

      # If the original URL can't be found, leave it empty.
      original_request_url_spec : str = None
      status, original_request_url_spec = iterator.ReadString()
      if status == False:
        original_request_url_spec = ''
      self.original_request_url_ = original_request_url_spec

      # Default to not overriding the user agent if we don't have info.
      status, self.is_overriding_user_agent_ = iterator.ReadBool()
      if status == False:
        self.is_overriding_user_agent_ = False

    # TODO(akalin): Restore timestamp when it is persisted.
    return True

  # The index in the NavigationController. This TabNavigation is
  # valid only when the index is non-negative.
  #
  # This is used when determining the selected TabNavigation and only
  # used by SessionService.
  def index(self) -> int:
    return self.index_

  def set_index(self, index : int):
    self.index_ = index

  # Accessors for some fields taken from NavigationEntry.
  def unique_id(self) -> int:
    return self.unique_id_

  def virtual_url(self) -> str:
    return self.virtual_url_

  def title(self) -> str:
    return self.title_

  def content_state(self) -> str:
    return self.content_state_

  # Timestamp this navigation occurred.
  def timestamp(self) -> datetime:
    return self.timestamp_
