#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of Export Layers.
#
# Copyright (C) 2013-2018 khalim19 <khalim19@gmail.com>
#
# Export Layers is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Export Layers is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Export Layers.  If not, see <https://www.gnu.org/licenses/>.

"""
This script automatically formats commit messages (header and body) and prevents
a commit from proceeding if some formatting conventions are violated (e.g. too
long commit header).
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import inspect
import sys
import textwrap


FIRST_LINE_MAX_CHAR_LENGTH = 70
MESSAGE_BODY_MAX_CHAR_LINE_LENGTH = 72

COMMIT_MESSAGE_FUNCS_PREFIX = "commit_msg"


def commit_msg_check_first_line_length(commit_message):
  first_line = commit_message.split("\n")[0]
  
  if len(first_line) <= FIRST_LINE_MAX_CHAR_LENGTH:
    return commit_message
  else:
    print_error_message_and_exit(
      "First line of commit message too long ({}), must be at most {}".format(
        len(first_line), FIRST_LINE_MAX_CHAR_LENGTH))


def commit_msg_check_second_line_is_empty(commit_message):
  lines = commit_message.split("\n")
  
  if len(lines) <= 1 or not lines[1]:
    return commit_message
  else:
    print_error_message_and_exit(
      "If writing a commit message body, the second line must be empty")


def commit_msg_remove_trailing_period_from_first_line(commit_message):
  lines = commit_message.split("\n")
  first_line, body = lines[0], lines[1:]
  
  first_line_processed = first_line.rstrip(".")
  
  return "\n".join([first_line_processed] + body)


def commit_msg_capitalize_first_letter_in_header(commit_message):
  lines = commit_message.split("\n")
  first_line, body = lines[0], lines[1:]
  
  first_line_segments = first_line.split(":", 1)
  if len(first_line_segments) <= 1:
    first_line_processed = first_line
  else:
    scope, header = first_line_segments
    header_without_leading_space = header.lstrip(" ")
    
    header_capitalized = (
      " " + header_without_leading_space[0].upper()
      + header_without_leading_space[1:])
    first_line_processed = ":".join([scope, header_capitalized])
  
  return "\n".join([first_line_processed] + body)


def commit_msg_wrap_message_body(commit_message):
  lines = commit_message.split("\n")
  first_line, body = lines[0], lines[1:]
  
  if not body:
    return commit_message
  else:
    wrapped_body = [
      textwrap.fill(
        line,
        MESSAGE_BODY_MAX_CHAR_LINE_LENGTH,
        replace_whitespace=False,
        drop_whitespace=False)
      for line in body]
    
    return "\n".join([first_line] + wrapped_body)


def commit_msg_remove_trailing_newlines(commit_message):
  return commit_message.rstrip("\n")


def process_commit_messages(commit_message_filepath):
  with open(commit_message_filepath, "r") as commit_message_file:
    commit_message = commit_message_file.read()
  
  commit_message_funcs = (
    _get_module_level_functions_with_prefix(COMMIT_MESSAGE_FUNCS_PREFIX))
  
  for func in commit_message_funcs:
    commit_message = func(commit_message)
  
  with open(commit_message_filepath, "w") as commit_message_file:
    commit_message_file.write(commit_message)


def _get_module_level_functions_with_prefix(prefix):
  return [
    member_obj
    for member_name, member_obj in inspect.getmembers(sys.modules[__name__])
    if inspect.isfunction(member_obj) and member_name.startswith(prefix)]


def print_error_message_and_exit(message, exit_status=1):
  print(message, file=sys.stderr)
  sys.exit(exit_status)


#===============================================================================


def main():
  process_commit_messages(sys.argv[1])


if __name__ == "__main__":
  main()
