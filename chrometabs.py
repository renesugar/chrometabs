#!/usr/bin/env python3
import os
import argparse
import sys
import json
from datetime import datetime, timedelta, timezone
from pprint import pprint

from pickle import Pickle, PickleIterator
from session import SessionCommand, SessionFileReader
from constants import SessionType, const
from tabnavigation import TabNavigation

#
# MIT License
#
# https://opensource.org/licenses/MIT
#
# Copyright 2020 Rene Sugar
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

def main():
  parser = argparse.ArgumentParser(description="chrometabs")
  parser.add_argument("--path", help="Path of the Chrome tabs file")
 
  args = vars(parser.parse_args())

  tabsPath = os.path.abspath(os.path.expanduser(args['path']))

  file_reader = SessionFileReader(tabsPath)

  status, commands = file_reader.Read(SessionType.TAB_RESTORE)

  if status == False:
    print("Could not read commands from tabs file.")
    sys.exit(1)

  for command in commands:
    if command.command_id() == const.TabNavigation_kCommandUpdateTabNavigation:
      pickle = command.PayloadAsPickle()
      if pickle is None:
        print("Could create pickle for command.")
        sys.exit(1)

      iterator = PickleIterator(pickle)
  
      status, tab_id = iterator.ReadInt()
      if status == False:
        print("Could not read tab id %s." % (tab_id,))
        sys.exit(1)

      navigation = TabNavigation()
      navigation.ReadFromPickle(iterator)
      print(navigation.title())
      print(navigation.timestamp().strftime('%Y-%m-%d %H:%M:%S.%f'))
      print(navigation.timestamp().strftime('%Y-%m-%d %H:%M:%S.%f'))
      print(navigation.virtual_url())
    elif command.command_id() == const.TabNavigation_kCommandRestoredEntry:
      pass
    elif command.command_id() == const.TabNavigation_kCommandWindow:
      pass
    elif command.command_id() == const.TabNavigation_kCommandSelectedNavigationInTab:
      pass
    elif command.command_id() == const.TabNavigation_kCommandPinnedState:
      pass
    elif command.command_id() == const.TabNavigation_kCommandSetExtensionAppID:
      pass
    elif command.command_id() == const.TabNavigation_kCommandSetWindowAppName:
      pass
    elif command.command_id() == const.TabNavigation_kCommandSetTabUserAgentOverride:
      pass
    elif command.command_id() == const.TabNavigation_kCommandUnknown:
      pass
    else:
      print("Unknown command %s" % (str(command.command_id()),))
if __name__ == "__main__":
  main()
