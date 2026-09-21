#!/usr/bin/env python3
"""Legacy command now creates only an offline synthetic preview.

python test_run.py [--output-dir DIR]
Old note/hatena/x/analyze/summary/mail modes are not supported here.
Use preview.py for samples or the documented main.py live pipeline.
"""
from preview import main

if __name__ == "__main__":
    raise SystemExit(main())
