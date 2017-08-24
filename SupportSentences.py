# -*- coding: utf-8 -*-
import sys
import cdb
from collections import Counter, defaultdict
sys.path.insert(1, "/home/huang/work/CDB_handler")
from CDB_Reader import CDB_Reader
from utils import KATA_ENG

class SupportSentences(object):
    def __init__(self, config, support_sentence_keys):
        self.config = config
        self.config.key2sid = CDB_Reader(self.config.key2sid)
        self.config.sid2pa = CDB_Reader(self.config.sid2pa)

        self._set_sids(support_sentence_keys)

    def _set_sids(self, support_sentence_keys):
        raw_sids = [self.config.key2sid.get(key) for key in support_sentence_keys]
        raw_sids = sum([x.split(',') for x in raw_sids if x is not None], [])

        self.sids, self.rels, self.sents, self.pas = [], [], [], []
        for raw_sid in raw_sids:
            self._parse_raw_sids(raw_sid)

    def _parse_raw_sids(self, raw_sid):
        sid = raw_sid.split(":")[0]
        rel = raw_sid.split(":")[1].split(";")[0]
        sent = self._get_sentence_by_sid(sid)
        pa = self._get_pa_by_sid(sid)

        self.sids.append(sid)
        self.rels.append(rel)
        self.sents.append(sent)
        self.pas.append(pa)

    def _get_sentence_by_sid(self, sid):
        sid = sid.split('%')[0]
        sub_dirs = sid.split('-')[0], sid.split('-')[1][:4], sid.split('-')[1][:6]
        sid2sent = "%s/%s/%s/%s.cdb" % (self.config.sid2sent_dir, sub_dirs[0], sub_dirs[1], sub_dirs[2])
        SID2SENT = cdb.init(sid2sent)

        sent = SID2SENT.get(sid)
        if sent == None:
            sys.stderr.write("Cannot retrieve sentence of sid:%s.\n" % sid)
        return sent
    
    def _get_pa_by_sid(self, sid):
        paStr = self.config.sid2pa.get("%s:" % sid)
        if paStr == None:
            sys.stderr.write("Cannot retrieve PAS for sid:%s.\n" % sid)
        return paStr

    def get_supArgs(self):
        supArgs = [defaultdict(list), defaultdict(list)]

        for paStr in [x for x in self.pas if x is not None]:
            pas = self._parse_pa_str(paStr)
            for index, pa in enumerate(pas):
                for case, arg in pa.items():
                    supArgs[index][case].append(arg)

        supArgs = [{case: dict(Counter(args)) for case, args in x.items()} for x in supArgs]
        return supArgs

    def _parse_pa_str(self, pa_str):
        pa_str = pa_str.split(" | ")[0]
        pa1, pa2 = map(lambda x: x.split(" "), pa_str.split(" - "))

        pa_dicts = []
        for pa_components in [pa1, pa2]:
            cases = map(lambda x: KATA_ENG[x.decode('utf-8')], pa_components[1::2])
            args = pa_components[0::2]
            pa_dict = dict(zip(cases, args))
            pa_dicts.append(pa_dict)

        return pa_dicts

