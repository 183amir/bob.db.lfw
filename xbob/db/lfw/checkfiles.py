#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# Laurent El Shafey <laurent.el-shafey@idiap.ch>
# @date: Thu May 24 10:41:42 CEST 2012
#
# Copyright (C) 2011-2012 Idiap Research Institute, Martigny, Switzerland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Checks for installed files.
"""

import os
import sys

# Driver API
# ==========

def checkfiles(args):
  """Checks lists of files based on your criteria"""

  from .query import Database
  db = Database()

  # go through all files, check if they are available on the filesystem
  good = {}
  bad = {}
  for protocol in db.m_valid_protocols:
    r = db.objects(protocol=protocol)

    for f in r:
      if os.path.exists(f.make_path(args.directory, args.extension)):
        good[f.id] = f
      else:
        bad[f.id] = f

  # report
  output = sys.stdout
  if args.selftest:
    from bob.db.utils import null
    output = null()

  if bad:
    for id, f in bad.items():
      output.write('Cannot find file "%s"\n' % f.make_path(args.directory, args.extension))
    output.write('%d files (out of %d) were not found at "%s"\n' % \
        (len(bad), len(r), args.directory))

  return 0

def add_command(subparsers):
  """Add specific subcommands that the action "checkfiles" can use"""

  from argparse import SUPPRESS

  parser = subparsers.add_parser('checkfiles', help=checkfiles.__doc__)

  parser.add_argument('-d', '--directory', dest="directory", default='', help="if given, this path will be prepended to every entry returned (defaults to '%(default)s')")
  parser.add_argument('-e', '--extension', dest="extension", default='', help="if given, this extension will be appended to every entry returned (defaults to '%(default)s')")
  parser.add_argument('--self-test', dest="selftest", default=False,
      action='store_true', help=SUPPRESS)

  parser.set_defaults(func=checkfiles) #action
