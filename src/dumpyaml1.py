#!/usr/bin/env python3

import sys, yaml, pprint

vals = yaml.load(sys.stdin)
pprint.pprint(vals)
