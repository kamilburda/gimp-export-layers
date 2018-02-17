#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import textwrap

#===============================================================================

FIRST_LINE_MAX_CHAR_LENGTH = 70
MESSAGE_BODY_MAX_CHAR_LINE_LENGTH = 72


def print_error_message_and_exit(message, exit_status=1):
  print(message, file=sys.stderr)
  sys.exit(exit_status)


#===============================================================================


def check_first_line_length(commit_message, max_length):
  first_line = commit_message.split("\n")[0]
  
  if len(first_line) <= max_length:
    return commit_message
  else:
    print_error_message_and_exit(
      "First line of commit message too long ({}), must be at most {}".format(
        len(first_line), max_length))


def check_second_line_is_empty(commit_message):
  lines = commit_message.split("\n")
  
  if len(lines) <= 1 or not lines[1]:
    return commit_message
  else:
    print_error_message_and_exit(
      "If writing a commit message body, the second line must be empty")


def remove_trailing_period_from_first_line(commit_message):
  lines = commit_message.split("\n")
  first_line, body = lines[0], lines[1:]
  
  first_line_processed = first_line.rstrip(".")
  
  return "\n".join([first_line_processed] + body)


def capitalize_first_letter_in_header(commit_message):
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


def wrap_message_body(commit_message, message_body_max_length):
  lines = commit_message.split("\n")
  first_line, body = lines[0], lines[1:]
  
  if not body:
    return commit_message
  else:
    wrapped_body = [
      textwrap.fill(
        line, message_body_max_length, replace_whitespace=False, drop_whitespace=False)
      for line in body]
    
    return "\n".join([first_line] + wrapped_body)


def remove_trailing_newlines(commit_message):
  return commit_message.rstrip("\n")


#===============================================================================

commit_message_process_funcs = [
  [check_first_line_length, FIRST_LINE_MAX_CHAR_LENGTH],
  [check_second_line_is_empty],
  [remove_trailing_period_from_first_line],
  [capitalize_first_letter_in_header],
  [wrap_message_body, MESSAGE_BODY_MAX_CHAR_LINE_LENGTH],
  [remove_trailing_newlines]
]


def main():
  with open(sys.argv[1], "r") as commit_message_file:
    commit_message = commit_message_file.read()
  
  for func_and_args in commit_message_process_funcs:
    func, args = func_and_args[0], func_and_args[1:]
    commit_message = func(commit_message, *args)
  
  with open(sys.argv[1], "w") as commit_message_file:
    commit_message_file.write(commit_message)


if __name__ == "__main__":
  main()
