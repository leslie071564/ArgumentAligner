# -*- coding: utf-8 -*-
import os 
import sys
import yaml
import shelve
import argparse
import sqlite3
import utils
from visulize_utils import OverviewTable, EventPairTable, GeneralFeatureTable, cfFeatureTable
from collections import namedtuple
import xlwt

evalConfig = namedtuple('evalConfig', 'ev_db, feat_db')

def setEvalConfig(config_fn):
    config = yaml.load(open(config_fn, 'r'))
    eval_config = evalConfig(config['output']['ev_db'], config['output']['feat_db'])

    return eval_config

class alignResultProcessor(object):
    dataFormat = ["cf_num1", "cf_num2", "goldResult", "outputResult"]
    def __init__(self, config, result_file_prefix):
        self.config = config
        self.feat_db = shelve.open(config.feat_db, flag='r')
        self.resultFiles = utils.search_file_with_prefix(result_file_prefix)

        self._setResultData()

    def _setResultData(self):
        self.resultData = {}
        for result_file in self.resultFiles:
            for line in open(result_file).readlines():
                if line[0] in ["#", "@", "A"]:
                    continue
                line = line.rstrip().split("_")
                ID, cf1, cf2 = line[:3]
                output = line[3:]

                exp_result = self._getResult(ID, output)
                goldResult, outputResult = exp_result['gold'], exp_result['output']

                self.resultData[ID] = dict(zip(self.dataFormat, [cf1, cf2, goldResult, outputResult])) 

    def _getResult(self, ID, output):
        if output == ['null']:
            output = []

        feats = self.feat_db[ID]
        goldRaw = feats['goldRaw']
        if goldRaw == None:
            outputPos, outputNeg = output, []
            goldPos, goldNeg, goldNeu = [], [], []
        else:
            goldAligns = utils.getAlignCorrespondence(feats['goldRaw'])

            outputPos = []
            goldPos, goldNeg, goldNeu = [], [], []
            for gold, acceptSet in goldAligns.iteritems():
                correctSet = set(acceptSet) & set(output)
                if correctSet != set():
                    goldPos.append(gold)
                    outputPos += list(correctSet)
                elif "" in acceptSet:
                    goldNeu.append(gold)
                else:
                    goldNeg.append(gold)

            outputPos = list(set(outputPos))
            outputNeg = [x for x in output if x not in outputPos]

        return {'output': {'+': outputPos, '-': outputNeg}, 'gold': {'+': goldPos, '-': goldNeg, '*': goldNeu}}

    def evaluate(self):
        outputResult = self._get_output_counts()
        outputAll = sum(outputResult.values())
        precision = float(outputResult['+']) / outputAll 

        goldResult = self._get_gold_counts()
        goldAll = goldResult['+'] + goldResult['-']
        recall = float(goldResult['+']) / goldAll

        AER = 1 - ( float(outputResult['+'] + goldResult['+']) / (outputAll + goldAll) )

        print 'AER: %.3f' % (AER)
        print 'precision: %.3f (%s/%s)' % (precision, outputResult['+'], outputAll)
        print 'recall: %.3f (%s/%s)' % (recall, goldResult['+'], goldAll)

        return {'AER': AER, 'precision': precision, 'recall': recall}

    def _get_gold_counts(self):
        gold_pos = sum([len(x['goldResult']['+']) for x in self.resultData.values()])
        gold_neg = sum([len(x['goldResult']['-']) for x in self.resultData.values()])
        gold_counts = {'+': gold_pos, '-': gold_neg}
        return gold_counts

    def _get_output_counts(self):
        output_pos = sum([len(x['outputResult']['+']) for x in self.resultData.values()])
        output_neg = sum([len(x['outputResult']['-']) for x in self.resultData.values()])
        output_counts = {'+': output_pos, '-': output_neg}
        return output_counts

    def write_excel(self, xlsx_file, exp_name, minors_only=False):
        book = xlwt.Workbook(encoding="utf-8")
        error_sheet = book.add_sheet("error")
        corret_sheet = book.add_sheet("correct")

        # set header line and column width.
        for ws in [error_sheet, corret_sheet]:
            self.write_excel_row(ws, 0, ['ID', 'Event Pair', 'output', 'gold', 'detail', 'judge'])
            evp_col, output_col = ws.col(1), ws.col(2)
            evp_col.width, output_col.width = 70 * 256, 10 * 256

        error_num, correct_num = 1, 1
        for ID, data in self.resultData.iteritems():
            goldResult = " ".join(data['goldResult'].items())
            outputResult = " ".join(data['outputResult'].items())
            if minors_only and outputResult in ['g-g', '']:
                continue

            ids_page = "http://lotus.kuee.kyoto-u.ac.jp/~huang/argAligner/ids.php?id=%s&exp=%s" % (ID, exp_name)
            hyperlink = 'HYPERLINK("%s", "link")' % (ids_page)

            row_data = [ID, data["charStr"], outputResult, goldResult, xlwt.Formula(hyperlink), '']

            if data['outputResult']['-'] == [] and data['goldResult']['-'] == []:
                self.write_excel_row(corret_sheet, correct_num, row_data)
                correct_num += 1
            else:
                self.write_excel_row(error_sheet, error_num, row_data)
                error_num += 1

        book.save(xlsx_file)

    def write_excel_row(self, ws, row_num, row):
        for col_num, element in enumerate(row):
            ws.write(row_num, col_num, element)

    def printOverviewTable(self, db_loc, exp_name=None):
        if os.path.exists(db_loc) and os.stat(db_loc).st_size != 0:
            sys.stderr.write("not new file, skip initialization.\n")
            existed = True
        else:
            existed = False
        conn = sqlite3.connect(db_loc)
        c = conn.cursor()

        self._printOverviewTable(c, exp_name, existed)

        conn.commit()
        conn.close()

    def _printOverviewTable(self, cursor, exp_name, existed):
        sys.stderr.write("loading overview table...\n")
        overviewTable = OverviewTable(cursor, self.config, exp_name, existed)
        for ID, data_dict in self.resultData.iteritems():
            overviewTable.set_row(ID, data_dict)

    def printDetailTables(self, db_loc):
        conn = sqlite3.connect(db_loc)
        c = conn.cursor()

        self.printEventPairTable(c)
        self.printGeneralFeatureTable(c)
        self.printCfFeatureTable(c)

        conn.commit()
        conn.close()

    def printEventPairTable(self, cursor):
        sys.stderr.write("loading eventpair table...\n")
        evpTable = EventPairTable(cursor, self.config)
        for ID in self.resultData.keys():
            evpTable.set_row(ID)

    def printGeneralFeatureTable(self, cursor):
        sys.stderr.write("loading general feature table...\n")
        genTable = GeneralFeatureTable(cursor, self.config)
        for ID in self.resultData.keys():
            genTable.set_row(ID)

    def printCfFeatureTable(self, cursor):
        sys.stderr.write("loading cf feature table...\n")
        cfTable = cfFeatureTable(cursor, self.config)
        for ID in self.resultData.keys():
            cfTable.set_rows(ID)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', "--result_dir", action="store", dest="result_dir")
    parser.add_argument('--config_file', action="store", default="./config.yaml", dest="config_file")
    parser.add_argument('--exp_name', action="store", dest="exp_name")
    parser.add_argument('--minors_only', action="store_true", dest="minors_only")

    parser.add_argument('--print_scores', action="store_true", dest="print_scores")
    parser.add_argument('--build_overview_db', action="store", dest="build_overview_db")
    parser.add_argument('--build_detail_db', action="store", dest="build_detail_db")
    parser.add_argument('--print_excel', action="store", dest="print_excel")
    options = parser.parse_args() 

    config = setEvalConfig(options.config_file)
    evl = alignResultProcessor(config, options.result_dir)

    if options.print_scores:
        evl.evaluate()

    if options.build_overview_db:
        evl.printOverviewTable(options.build_overview_db)

    if options.build_detail_db:
        evl.printDetailTables(options.build_detail_db)

    if options.print_excel:
        if options.exp_name == None:
            sys.stderr.write('please specify exp_name')
            sys.exit()
            evl.write_excel(options.print_excel, options.exp_name, minors_only=options.minors_only)

