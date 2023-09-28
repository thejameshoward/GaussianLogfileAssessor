#!/usr/bin/env python3
# coding: utf-8

'''
Analyzes Gaussian .log files
'''

from __future__ import annotations

import re

from pathlib import Path

import psutil
proc = psutil.Process()
proc.cpu_affinity([proc.cpu_affinity()[0]])