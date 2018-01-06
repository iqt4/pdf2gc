
# -*- coding: utf-8 -*-

"""
Extension of pdfminer to read bank statements.
"""

from re import sub
from decimal import Decimal
from collections import namedtuple
from itertools import groupby
from operator import itemgetter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLineHorizontal
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.psparser import literal_name


class PDFResourceManagerNew(PDFResourceManager):
    """Correct broken font - either it has an Encoding or a Unicode_map for text extraction"""
    def get_font(self, objid, spec):
        font = PDFResourceManager.get_font(self, objid, spec)
        # Correct broken fond - either it has an Encoding or a Unicode_map for text extraction
        if literal_name(spec['Encoding']) == 'WinAnsiEncoding':
            font.unicode_map = None
        return font

class Miner(object):
    def __init__(self, filename, laparams = None):
        self.fp = open(filename, 'rb')
        resources = PDFResourceManagerNew()
        self.device = PDFPageAggregator(resources, laparams=laparams)
        self.interpreter = PDFPageInterpreter(resources, self.device)
        self.val = dict()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.fp.close()
        

class Miner_DB(Miner):
    """Extract value from Deutsche Bank"""
    def __init__(self, filename):
        laparams = LAParams()
        laparams.detect_vertical = True
        super().__init__(filename, laparams)

    def process(self):
        page = next(PDFPage.get_pages(self.fp, pagenos=[0]))
        self.interpreter.process_page(page)
        layout = self.device.get_result()

        # Text items are stored in LTTextBox containing LTTextLine
        item_list = []
        item = namedtuple('item', 'x y text')
        text_box = (tb for tb in layout if isinstance(tb, LTTextBox))

        for tb in text_box:
            for tl in tb:
                if not isinstance(tl, LTTextLineHorizontal): continue
                # extract position and text as namedtuples
                # fuzzy workaround for line# because position is not always exact
                item_list.append(item(x=round(tl.x0),
                                      y=round(tl.y1/2)*2,
                                      text=tl.get_text().strip()))

        #Sort top->down, left->right
        item_list.sort(key=lambda itm: (-itm.y, itm.x))

        # Find document type
        itm_idx = None
        try:
            itm = next(i for i in item_list if i.text == 'Dividendengutschrift')
            itm_idx = item_list.index(itm)
            self.val['type'] = itm.text
        except StopIteration:
            pass

        # Exchange ',' -> '.' and omit 'EUR'
        def text2value(t):
            v = sub(r'(-?)\s*([0-9-]*),([0-9]*).*', r'\1\2.\3', t)
            return Decimal(v)

        self.val['quantity'] = text2value(item_list[itm_idx + 4].text)
        self.val['WKN'] = item_list[itm_idx + 5].text
        self.val['ISIN'] = item_list[itm_idx + 6].text
        self.val['name'] = item_list[itm_idx + 7].text

        # Define search parameters and create dict{line#, key}
        sp = {'Dividend': 'Bruttoertrag', 'KESt': 'Kapitalertragsteuer (KESt)', 'QuSt': '% Ausländische Quellensteuer',
              'SolZ': 'Solidaritätszuschlag auf KESt', 'Bank': 'Gutschrift mit Wert'}
        lines = {itm.y: s for s in sp for itm in item_list if sp[s] in itm.text}

        # Group items by line
        for k, g in groupby(item_list, key=lambda itm: itm.y):
            if k in lines:
                itm = next(reversed(list(g))) # last element in line
                key = lines[k] # translate line#
                self.val[key] = text2value(itm.text)

