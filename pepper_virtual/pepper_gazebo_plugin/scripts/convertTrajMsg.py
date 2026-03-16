#!/usr/bin/env python3

# Copyright (C) 2014 Aldebaran Robotics
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# authors: Mikael Arguedas [mikael DOT arguedas AT gmail DOT com]
#FIXME Add : Fingers for Humanoids and Sensors

import sys
import argparse
import os

HEADER_LINES = 12   # lines to skip at the start of the rostopic echo output
FOOTER_LINES = 6    # lines to skip at the end

parser = argparse.ArgumentParser(usage='Convert rostopic echo trajectory output to a clean format')
parser.add_argument('-i', '--input', default=None, required=True,
                    help='file containing the trajectory (rostopic echo controller/follow_joint_trajectory/goal)')

args = parser.parse_args()

if not os.path.isfile(args.input):
    print("Error: input file '{}' does not exist".format(args.input), file=sys.stderr)
    sys.exit(1)

with open(args.input, 'r') as f:
    lines = f.readlines()

min_lines = HEADER_LINES + FOOTER_LINES + 1
if len(lines) < min_lines:
    print("Error: input file has {} lines, expected at least {}".format(len(lines), min_lines),
          file=sys.stderr)
    sys.exit(1)

output = args.input[:args.input.rfind('.')] + '_modified' + args.input[args.input.rfind('.'):]
print(output)

with open(output, 'w+') as outfile:
    for line in lines[HEADER_LINES:len(lines) - FOOTER_LINES]:
        if len(line) >= 2:
            outfile.write(line[2:])
        else:
            outfile.write('\n')
