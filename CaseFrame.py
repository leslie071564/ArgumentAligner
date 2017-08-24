# -*- coding: utf-8 -*-
import sys
import re
import operator
import xml.etree.ElementTree as ET
import utils
from utils import CASE_ENG, CASE_KATA, KATA_ENG, ENG_HIRA
sys.path.insert(1, "/home/huang/work/CDB_handler")
from CDB_Reader import CDB_Reader

class CaseFrame(object):
    id_pattern = r"(\D+):(\D+)(\d+)$"
    def __init__(self, config, cf_id="", xml=None):
        self.config = config
        if cf_id:
            self._set_predicate(cf_id)
            self._set_args()

        elif xml: 
            self._set_predicate(xml.attrib['id'])
            self._set_args(cf_xml=xml)

        else:
            # create empty CaseFrame object.
            pass

    def _set_predicate(self, cf_id):
        self.id = cf_id

        regex = re.compile(CaseFrame.id_pattern)
        self.predRep, self.predType, self.predNum = regex.search(cf_id).groups()
        self.predNum = int(self.predNum)

    def _set_args(self):
        cf_xml = self._get_xml()
        if cf_xml == None:
            sys.stderr.write("CaseFrame object not initialized properly.\n")
            return None

        self.caseFrequencies, self.args = {}, {}
        for case_xml in cf_xml:
            case, freq = case_xml.attrib['case'][0], case_xml.attrib['frequency']
            if case not in CASE_KATA:
                continue

            case = KATA_ENG[case]
            self.caseFrequencies[case] = int(freq)
            self.args[case] = { arg.text.encode('utf-8'): int(arg.attrib['frequency']) for arg in case_xml }

    def _get_xml(self):
        CF = CDB_Reader(self.config.cf_cdb)
        cf_xml = CF.get(self.id)
        if cf_xml:
            cf_xml = ET.fromstring(cf_xml)
            return cf_xml
        else:
            sys.stderr.write("Cannot find case frame with id %s.\n" % (self.id))
            return None

    def _get_xml_from_all(self):
        CF = CDB_Reader(self.config.cf_cdb, repeated_keys=True)
        xmls = CF.get(self.predRep, exhaustive=True)

        root = None
        for xml in xmls:
            xml = ET.fromstring(xml)
            root = xml[0]
            if root.attrib['predtype'] == self.predType:
                continue

        if root == None:
            sys.stderr.write("Cannot find predicate with correct type.")
            return None

        elif len(root) < self.predNum:
            sys.stderr.write("Cannot find cf with correct frame number.")
            return None

        else:
            cf_xml = root[self.predNum - 1]
            return cf_xml

    def get_cf_str(self):
        cf_str = ""
        for case in CASE_ENG:
            if case not in self.args.keys():
                continue

            case_args = self.args[case]
            max_arg = max(case_args.iteritems(), key=operator.itemgetter(1))[0]
            cf_str += "%s %s " % (max_arg, ENG_HIRA[case])
        cf_str += self.predRep
        return cf_str

    def getRelevanceScore(self, supArgs, contextWords={}, supportWeight=1.0, contextWeight=0.5):
        rel_score = 0
        for case in self.args.keys():
            case_rel_score = 0
            if case in supArgs.keys():
                supRel = utils.cosineSimilarity(supArgs[case], self.args[case], strip=False) 
                case_rel_score += supRel * supportWeight

            if contextWords:
                contextRel = utils.cosineSimilarity(contextWords, self.args[case], strip=True)
                case_rel_score += contextRel * contextWeight
            rel_score += case_rel_score

        return rel_score 

