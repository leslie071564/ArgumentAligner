# -*- coding: utf-8 -*-
import sys
import gzip
from CDB_Reader import CDB_Reader

class KNP_extractor(object):
    def __init__(self, knp_index_db, knp_prefix, sub_index_length=1):
        self.knp_index_db = knp_index_db
        self.knp_prefix = knp_prefix
        self.sub_index_length = sub_index_length

    def get_knp(self, sid):
        key = self.get_knp_key(sid)
        if key == None:
            sys.stderr.write("knp not found: %s\n" % sid)
            return ""

        knp_file_base, position = key.split(':')

        sub_dir_index = knp_file_base[:self.sub_index_length]
        knp_file = "%s%s/%s.knp.gz" % (self.knp_prefix, sub_dir_index, knp_file_base)

        return self._read_pos(knp_file, int(position))

    def get_knp_key(self, sid):
        knp_cdb = CDB_Reader(self.knp_index_db)
        return knp_cdb.get(sid)

    def _read_pos(self, f, pos):
        F = gzip.open(f, 'rb')
        F.seek(pos, 0)

        data = ""
        for line in F:
            if line.strip() == 'EOS':
                break
            data += line

        F.close()
        return data

class WordCountDB(object):
    def __init__(self, count_db):
        self.count_db = count_db
