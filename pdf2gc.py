# -*- coding: utf-8 -*-
"""
Script to extract transaction figures from bank statements and
import them into GnuCash
"""

import sys
from mypdfminer import Miner_DB

def extract_figures(files=[], bank=None):
    if not bank: raise(AttributeError)

    if bank == 'DB':
        miner_class = Miner_DB
    else:
        raise(AttributeError)

    for f in files:
        with miner_class(f) as m:
            m.process()
            v = m.val

# main
def main(args=None):
    import argparse
    P = argparse.ArgumentParser(description=__doc__)
    P.add_argument("files", type=str, default=None, nargs="+", help="Files to process.")
    P.add_argument("-b", "--bank", type=str, default="", help = "Bank")
    A = P.parse_args(args=args)

    ## Dictionary expected
    d = extract_figures(**vars(A))

    return 0

if __name__ == '__main__': sys.exit(main())