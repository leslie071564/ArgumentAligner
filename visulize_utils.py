# -*- coding: utf-8 -*-
import sys
import utils
import urllib
import shelve

def getColoredAlign(aligns_dict, highlight_color='red'):
    aligns_dict['-'] = map(lambda x: x.replace("'", "’"), aligns_dict['-'])
    aligns_dict['+'] = map(lambda x: x.replace("'", "’"), aligns_dict['+'])
    colored_align = []
    colored_align += aligns_dict['+']
    colored_align += ["<font color=\"%s\">%s</font>" % (highlight_color, x) for x in aligns_dict['-']]
    if '*' in aligns_dict.keys():
        aligns_dict['*'] = map(lambda x: x.replace("'", "’"), aligns_dict['*'])
        colored_align += ["<font color=\"gray\">%s</font>" % (x) for x in aligns_dict['*']]

    colored_align = " ".join(colored_align)
    return colored_align

def encode_list(L):
    """
    ex: ['a', 'b', 'c'] => "0=a&1=b&2=c"
    """
    return "&".join(["%s=%s" % (index, element) for index, element in enumerate(L)])

def encode_dict(d):
    """
    ex: {'k1' : 'v1', 'k2' : 'v2'} => "k1=v1&k2=v2"
    """
    return "&".join(["%s=%s" % (align, score) for align, score in d.items() if '_' not in align])

def get_url(id_str):
    return urllib.quote_plus(id_str.encode('utf-8'))

### classes
class SQLtable(object):
    def __init__(self, c, cols, table_name, existed=False):
        self.c = c
        self.cols = cols
        self.table_name = table_name
        if not existed:
            self.set_columns()

    def set_columns(self):
        self.c.execute("CREATE TABLE %s (id TEXT PRIMARY KEY)" % (self.table_name))
        for col in self.cols:
            self.c.execute("ALTER TABLE %s ADD COLUMN \'%s\' TEXT" % (self.table_name, col))

    def set_row(self, row_data):
        self.c.execute("INSERT INTO %s VALUES (\'%s\')" % (self.table_name, "\',\'".join(row_data)))


class OverviewTable(SQLtable):
    cols = ["charStr", "goldResult", "outputResult", "cf_num1", "cf_num2", \
            "g1", "w1", "n1", "d1", "g2", "w2", "n2", "d2"]
    table_name = "overview"
    def __init__(self, c, config, exp_name=None, existed=False):
        self.exp_name = exp_name
        if exp_name != None:
            self.cols.append("exp_name")
            
        SQLtable.__init__(self, c, OverviewTable.cols, OverviewTable.table_name, existed=existed)
        self.ev_db = shelve.open(config.ev_db, flag='r')

    def set_row(self, ID, data_dict):
        evp = self.ev_db[ID]

        charStr = " -> ".join([ev['eventRep'] for ev in evp['events']])

        row_data = []
        row_data.append(str(ID))
        row_data.append(charStr)
        row_data.append(getColoredAlign(data_dict['goldResult'], highlight_color='green'))
        row_data.append(getColoredAlign(data_dict['outputResult'], highlight_color='red'))
        row_data += [data_dict['cf_num1'], data_dict['cf_num2']]

        for ev in evp['events']:
            givenArgs = ev['givenArgs']
            supArgs = ev['supArgs']
            for case in ['g', 'w', 'n', 'd']:
                if case not in givenArgs.keys():
                    row_data.append("")
                else:
                    args = [utils.removeHira(x, concatenate=True) for x in supArgs[case].keys()]
                    row_data.append(encode_list(args))
                    #print encode_list(args)
        if self.exp_name != None:
            row_data.append(self.exp_name)
            

        self.c.execute("INSERT INTO %s VALUES (\'%s\')" % (self.table_name, "\',\'".join(row_data)))


class EventPairTable(SQLtable):
    cols = ["charStr", "gold", "pred1", "pred2", "cfs1", "cfs2", "cf_urls1", "cf_urls2", 'rnnsp_tops_1', 'rnnsp_tops_2']
    table_name = "eventpair"
    def __init__(self, c, config):
        SQLtable.__init__(self, c, EventPairTable.cols, EventPairTable.table_name)
        self.ev_db = shelve.open(config.ev_db, flag='r')
        self.feat_db = shelve.open(config.feat_db, flag='r')

    def set_row(self, ID):
        evp = self.ev_db[ID]
        feats = self.feat_db[ID]
        row_data = []

        charStr = " -> ".join([ev['eventRep'] for ev in evp['events']])
        gold = " ".join(feats['goldRaw']) if feats['goldRaw'] != None else ""
        gold = gold.replace("'", "’")
        cfs_data = [ ["[%s] %s(%.3f)" % (cf.cf_id, cf.cf_str, cf.rel_score) for cf in ev['cfs']] for ev in evp['events'] ]
        cf_urls = [ [ get_url(cf.cf_id) for cf in ev['cfs'] for cf in ev['cfs']] for ev in evp['events'] ]

        row_data += [ID, charStr, gold]
        row_data += [ utils.removeHira(ev['predRep']) for ev in evp['events'] ]
        row_data += [ encode_list(x) for x in cfs_data ]
        row_data += [ encode_list(x) for x in cf_urls ]

        for ev in evp['events']:
            if 'rnnsp_tops' not in ev.keys():
                row_data.append('')
                continue
            tops_list = ["[X %s %s]: %s" % (utils.ENG_HIRA[case], ev['eventRep'], ' | '.join(t_list)) for case, t_list in ev['rnnsp_tops'].iteritems()]
            row_data.append(encode_list(tops_list))

        self.c.execute("INSERT INTO %s VALUES (\'%s\')" % (self.table_name, "\',\'".join(row_data)))

class GeneralFeatureTable(SQLtable):
    cols = ["conflict", "contextArg", "contextCase", "embed", "embed_s", "contextArgText", "contextCaseText"]
    table_name = "general_feature"
    def __init__(self, c, config):
        SQLtable.__init__(self, c, GeneralFeatureTable.cols, GeneralFeatureTable.table_name)
        self.ev_db = shelve.open(config.ev_db, flag='r')
        self.feat_db = shelve.open(config.feat_db, flag='r')

    def set_row(self, ID):
        contributors = self.ev_db[ID]['feature_contributors']['general']
        feats = self.feat_db[ID]['features']['general']
        row_data = []
        
        row_data.append(ID)

        row_data.append(encode_dict(feats['conflict']))
        row_data.append(encode_dict(feats['cArg']))
        row_data.append(encode_dict(feats['cCase']))

        if "embed" in feats.keys() and "embed_s" in feats.keys():
            row_data.append(encode_dict(feats['embed']))
            row_data.append(encode_dict(feats['embed_s']))
        else:
            row_data += ["", ""]

        row_data.append(encode_dict(contributors['cArg']))
        row_data.append(encode_dict(contributors['cCase']))

        self.c.execute("INSERT INTO %s VALUES (\'%s\')" % (self.table_name, "\',\'".join(row_data)))

class cfFeatureTable(SQLtable):
    cols = ["cfsim", "contextArg", "contextCase", "cfsimText", "contextArgText", "contextCaseText"]
    table_name = "cf_feature"
    def __init__(self, c, config):
        SQLtable.__init__(self, c, cfFeatureTable.cols, cfFeatureTable.table_name)
        self.ev_db = shelve.open(config.ev_db, flag='r')
        self.feat_db = shelve.open(config.feat_db, flag='r')

    def set_rows(self, ID):
        rows = self._get_row(ID)
        for row_data in rows:
            self.c.execute("INSERT INTO %s VALUES (\'%s\')" % (self.table_name, "\',\'".join(row_data)))

    def _get_row(self, ID):
        evp = self.ev_db[ID]
        feats = self.feat_db[ID]['features']

        rows = []
        for cf_pair, cf_dict in feats.iteritems():
            if cf_pair == "general":
                continue
            row_data = [] 
            row_data.append("%s_%s" % (ID, cf_pair))
            row_data.append(encode_dict({k: v for k, v in cf_dict['cfsim'].iteritems() if '-' in k}))
            ### cfContext
            row_data.append('')
            row_data.append('')
            ### cfContext

            contributors = evp['feature_contributors'][cf_pair]
            row_data.append(encode_dict(contributors['cfsim']))
            ### cfContext
            row_data.append('')
            row_data.append('')
            ### cfContext

            rows.append(row_data)

        return rows

