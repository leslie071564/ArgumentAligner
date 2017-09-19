# -*- coding: utf-8 -*-
import os 
import sys
import yaml
import shelve
import argparse
import sqlite3
import utils
from utils import SQLtable

class alignResultProcessor(object):
    dataFormat = ["charStr", "cf_num1", "cf_num2", "goldResult", "outputResult"]
    def __init__(self, config, result_file_prefix):
        self.ev_db = shelve.open(config['DB']['EVENT_PAIR'], flag='r')
        self.feat_db = shelve.open(config['DB']['FEAT'], flag='r')
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

                exp_result = self.getResult(ID, output)
                goldResult, outputResult = exp_result['gold'], exp_result['output']

                evp = self.ev_db[ID]
                charStr = " -> ".join([ev['eventRep'] for ev in evp['events']])

                self.resultData[ID] = dict(zip(self.dataFormat, [charStr, cf1, cf2, goldResult, outputResult])) 

    def getResult(self, ID, output):
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

    def printOverviewTable(self, db_loc):
        conn = sqlite3.connect(db_loc)
        c = conn.cursor()
        cols = ["charStr", "goldResult", "outputResult"]
        table_name = "overview"
        resultDB = SQLtable(c, cols, table_name)

        for ID, data_dict in self.resultData.iteritems():
            data = [] 
            data.append(data_dict['charStr'])
            data.append(self.getColoredAlign(data_dict['goldResult'], highlight_color='green'))
            data.append(self.getColoredAlign(data_dict['outputResult'], highlight_color='red'))

            resultDB.set_row([str(ID)] + data)

        conn.commit()
        conn.close()

    def getColoredAlign(self, aligns_dict, highlight_color='red'):
        aligns_dict['-'] = map(lambda x: x.replace("'", "’"), aligns_dict['-'])
        aligns_dict['+'] = map(lambda x: x.replace("'", "’"), aligns_dict['+'])
        colored_align = []
        colored_align += aligns_dict['+']
        colored_align += ["<font color=\"%s\">\"%s\"</font>" % (highlight_color, x) for x in aligns_dict['-']]
        if '*' in aligns_dict.keys():
            aligns_dict['*'] = map(lambda x: x.replace("'", "’"), aligns_dict['*'])
            colored_align += ["<font color=\"gray\">\"%s\"</font>" % (x) for x in aligns_dict['*']]

        colored_align = " ".join(colored_align)
        return colored_align

                
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', "--result_dir", action="store", dest="result_dir")
    parser.add_argument('--config_file', action="store", default="./config.yaml", dest="config_file")
    options = parser.parse_args() 

    config = yaml.load(open(options.config_file, 'r'))

    evl = alignResultProcessor(config, options.result_dir)
    evl_result = evl.evaluate()
