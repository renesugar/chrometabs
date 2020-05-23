# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Copyright (c) 2020 Rene Sugar. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE.chromium file.

import sys
import struct

from enum import Enum, IntEnum
from typing import TypeVar, Generic, NewType, Callable, Iterable, Any, Tuple

import const

const.kPayloadUnit = 64
const.kCapacityReadOnly = sys.maxsize
const.kuint32max = sys.maxsize

#------------------------------------------------------------------------------

# https://docs.python.org/dev/library/stdtypes.html#memoryview

class SizeOf(IntEnum):
  BOOL = 1
  INT = 4
  LONG = 4
  UINT8 = 1
  UINT16 = 2
  UINT32 = 4
  INT32 = 4
  INT64 = 8
  UINT64 = 8
  FLOAT = 4
  DOUBLE = 8
  HEADER = 4
  FILEHEADER = 8
  SIZE_TYPE = 2
  ID_TYPE = 1

# Identifies the type of session service this is. This is used by the
# backend to determine the name of the files.
class SessionType(IntEnum):
  SESSION_RESTORE = 0
  TAB_RESTORE = 1

# https://chromium.googlesource.com/external/WebKit/Source/Platform/chromium/public/+/ad66491450101178db06dc094cb1836fb3d80825/WebReferrerPolicy.h
class WebKitWebReferrerPolicy(IntEnum):
  WebReferrerPolicyAlways = 0
  WebReferrerPolicyDefault = 1
  WebReferrerPolicyNever = 2
  WebReferrerPolicyOrigin = 3

# Types of transitions between pages. These are stored in the history
# database to separate visits, and are reported by the renderer for page
# navigations.
# 
# WARNING: don't change these numbers. They are written directly into the
# history database, so future versions will need the same values to match
# the enums.
# 
# A type is made of a core value and a set of qualifiers. A type has one
# core value and 0 or or more qualifiers.
class PageTransition(IntEnum):
  # User got to this page by clicking a link on another page.
  PAGE_TRANSITION_LINK = 0

  # User got this page by typing the URL in the URL bar.  This should not be
  # used for cases where the user selected a choice that didn't look at all
  # like a URL; see GENERATED below.
  # 
  # We also use this for other "explicit" navigation actions.
  PAGE_TRANSITION_TYPED = 1

  # User got to this page through a suggestion in the UI, for example,
  # through the destinations page.
  PAGE_TRANSITION_AUTO_BOOKMARK = 2

  # This is a subframe navigation. This is any content that is automatically
  # loaded in a non-toplevel frame. For example, if a page consists of
  # several frames containing ads, those ad URLs will have this transition
  # type. The user may not even realize the content in these pages is a
  # separate frame, so may not care about the URL (see MANUAL below).
  PAGE_TRANSITION_AUTO_SUBFRAME = 3

  # For subframe navigations that are explicitly requested by the user and
  # generate new navigation entries in the back/forward list. These are
  # probably more important than frames that were automatically loaded in
  # the background because the user probably cares about the fact that this
  # link was loaded.
  PAGE_TRANSITION_MANUAL_SUBFRAME = 4

  # User got to this page by typing in the URL bar and selecting an entry
  # that did not look like a URL.  For example, a match might have the URL
  # of a Google search result page, but appear like "Search Google for ...".
  # These are not quite the same as TYPED navigations because the user
  # didn't type or see the destination URL.
  # See also KEYWORD.
  PAGE_TRANSITION_GENERATED = 5

  # This is a toplevel navigation. This is any content that is automatically
  # loaded in a toplevel frame.  For example, opening a tab to show the ASH
  # screen saver, opening the devtools window, opening the NTP after the safe
  # browsing warning, opening web-based dialog boxes are examples of
  # AUTO_TOPLEVEL navigations.
  PAGE_TRANSITION_AUTO_TOPLEVEL = 6

  # The user filled out values in a form and submitted it. NOTE that in
  # some situations submitting a form does not result in this transition
  # type. This can happen if the form uses script to submit the contents.
  PAGE_TRANSITION_FORM_SUBMIT = 7

  # The user "reloaded" the page, either by hitting the reload button or by
  # hitting enter in the address bar.  NOTE: This is distinct from the
  # concept of whether a particular load uses "reload semantics" (i.e.
  # bypasses cached data).  For this reason, lots of code needs to pass
  # around the concept of whether a load should be treated as a "reload"
  # separately from their tracking of this transition type, which is mainly
  # used for proper scoring for consumers who care about how frequently a
  # user typed/visited a particular URL.
  # 
  # SessionRestore and undo tab close use this transition type too.
  PAGE_TRANSITION_RELOAD = 8

  # The url was generated from a replaceable keyword other than the default
  # search provider. If the user types a keyword (which also applies to
  # tab-to-search) in the omnibox this qualifier is applied to the transition
  # type of the generated url. TemplateURLModel then may generate an
  # additional visit with a transition type of KEYWORD_GENERATED against the
  # url 'http://' + keyword. For example, if you do a tab-to-search against
  # wikipedia the generated url has a transition qualifer of KEYWORD, and
  # TemplateURLModel generates a visit for 'wikipedia.org' with a transition
  # type of KEYWORD_GENERATED.
  PAGE_TRANSITION_KEYWORD = 9

  # Corresponds to a visit generated for a keyword. See description of
  # KEYWORD for more details.
  PAGE_TRANSITION_KEYWORD_GENERATED = 10

  # ADDING NEW CORE VALUE? Be sure to update the LAST_CORE and CORE_MASK
  # values below.  Also update CoreTransitionString().
  PAGE_TRANSITION_LAST_CORE =   PAGE_TRANSITION_KEYWORD_GENERATED
  PAGE_TRANSITION_CORE_MASK = 0xFF

  # Qualifiers
  # Any of the core values above can be augmented by one or more qualifiers.
  # These qualifiers further define the transition.

  # User used the Forward or Back button to navigate among browsing history.
  PAGE_TRANSITION_FORWARD_BACK = 0x01000000

  # User used the address bar to trigger this navigation.
  PAGE_TRANSITION_FROM_ADDRESS_BAR = 0x02000000

  # User is navigating to the home page.
  PAGE_TRANSITION_HOME_PAGE = 0x04000000

  # The beginning of a navigation chain.
  PAGE_TRANSITION_CHAIN_START = 0x10000000

  # The last transition in a redirect chain.
  PAGE_TRANSITION_CHAIN_END = 0x20000000

  # Redirects caused by JavaScript or a meta refresh tag on the page.
  PAGE_TRANSITION_CLIENT_REDIRECT = 0x40000000

  # Redirects sent from the server by HTTP headers. It might be nice to
  # break this out into 2 types in the future, permanent or temporary, if we
  # can get that information from WebKit.
  PAGE_TRANSITION_SERVER_REDIRECT = 0x80000000

  # Used to test whether a transition involves a redirect.
  PAGE_TRANSITION_IS_REDIRECT_MASK = 0xC0000000

  # General mask defining the bits used for the qualifiers.
  PAGE_TRANSITION_QUALIFIER_MASK = 0xFFFFFF00

int16    = NewType('int16', int)
uint16    = NewType('uint16', int)
int32     = NewType('int32', int)
uint32    = NewType('uint32', int)
int64     = NewType('int64', int)
uint64    = NewType('uint64', int)

# These get written to disk, so we define types for them.
# Type for the identifier.
id_type   = NewType('id_type', int)
# Type for writing the size.
size_type = NewType('size_type', int)

# File version number.
const.kFileCurrentVersion = 1
# The signature at the beginning of the file = SSNS (Sessions).
const.kFileSignature = 0x53534E53
const.kFileReadBufferSize = 1024

# chromium/chrome/browser/sessions/session_service.cc

# # Identifier for commands written to file.
# const.kCommandSetTabWindow = 0
# # OBSOLETE Superseded by kCommandSetWindowBounds3.
# # const.kCommandSetWindowBounds = 1
# const.kCommandSetTabIndexInWindow = 2
# # Original kCommandTabClosed/kCommandWindowClosed. See comment in
# # MigrateClosedPayload for details on why they were replaced.
# const.kCommandTabClosedObsolete = 3
# const.kCommandWindowClosedObsolete = 4
# const.kCommandTabNavigationPathPrunedFromBack = 5
# const.kCommandUpdateTabNavigation = 6
# const.kCommandSetSelectedNavigationIndex = 7
# const.kCommandSetSelectedTabInIndex = 8
# const.kCommandSetWindowType = 9
# # OBSOLETE Superseded by kCommandSetWindowBounds3. Except for data migration.
# # const.kCommandSetWindowBounds2 = 10;
# const.kCommandTabNavigationPathPrunedFromFront = 11
# const.kCommandSetPinnedState = 12
# const.kCommandSetExtensionAppID = 13
# const.kCommandSetWindowBounds3 = 14
# const.kCommandSetWindowAppName = 15
# const.kCommandTabClosed = 16
# const.kCommandWindowClosed = 17
# const.kCommandSetTabUserAgentOverride = 18
# const.kCommandSessionStorageAssociated = 19


# Tab Navigation

const.TabNavigation_kMaxEntries = 25

# chromium/chrome/browser/sessions/tab_restore_service.cc

# Identifier for commands written to file.
# The ordering in the file is as follows:
# . When the user closes a tab a command of type
#   kCommandSelectedNavigationInTab is written identifying the tab and
#   the selected index, then a kCommandPinnedState command if the tab was
#   pinned and kCommandSetExtensionAppID if the tab has an app id and
#   the user agent override if it was using one.  This is
#   followed by any number of kCommandUpdateTabNavigation commands (1 per
#   navigation entry).
# . When the user closes a window a kCommandSelectedNavigationInTab command
#   is written out and followed by n tab closed sequences (as previoulsy
#   described).
# . When the user restores an entry a command of type kCommandRestoredEntry
#   is written.
const.TabNavigation_kCommandUpdateTabNavigation = 1
const.TabNavigation_kCommandRestoredEntry = 2
const.TabNavigation_kCommandWindow = 3
const.TabNavigation_kCommandSelectedNavigationInTab = 4
const.TabNavigation_kCommandPinnedState = 5
const.TabNavigation_kCommandSetExtensionAppID = 6
const.TabNavigation_kCommandSetWindowAppName = 7
const.TabNavigation_kCommandSetTabUserAgentOverride = 8
const.TabNavigation_kCommandUnknown = 9

# Number of entries (not commands) before we clobber the file and write
# everything.
const.TabNavigation_kEntriesPerReset = 40

# ----------

# Every kWritesPerReset commands triggers recreating the file.
const.kWritesPerReset = 250

# File names (current and previous) for a type of TAB.
const.kCurrentTabSessionFileName = "Current Tabs"
const.kLastTabSessionFileName = "Last Tabs"

# File names (current and previous) for a type of SESSION.
const.kCurrentSessionFileName = "Current Session"
const.kLastSessionFileName = "Last Session"

