# -*- coding: utf-8 -*-
import sys
import utils
import urllib
import shelve
from sqlalchemy import *

class OverviewTable(object):
    table_name = "overview"
    def __init__(self, metadata, config):
        self.ev_db = shelve.open(config.ev_db, flag='r')
        self._init_columns(metadata)

    def _init_columns(self, metadata):
        output_table = Table(self.table_name, metadata, 
                             Column("ID", String(), primary_key=True),
                             Column("charStr", String()),
                             Column("goldResult", String()),
                             Column("outputResult", String()),
                             Column("cf_num1", String()),
                             Column("cf_num2", String()),
                             Column("g1", String()), Column("w1", String()), Column("n1", String()), Column("d1", String()),
                             Column("pred1", String()),
                             Column("g2", String()), Column("w2", String()), Column("n2", String()), Column("d2", String()),
                             Column("pred2", String()),
                            )
        output_table.create()
        self.insert_cursor = output_table.insert()

    def set_rows(self, result_data):
        for ID, data_dict in result_data.iteritems():
            row_data = self._convert_result_data(ID, data_dict)
            self.insert_cursor.execute(**row_data)

    def _convert_result_data(self, ID, data_dict):
        row_data = {}
        row_data.update( {'ID': ID, 'cf_num1': data_dict['cf_num1'], 'cf_num2': data_dict['cf_num2']} )

        evp = self.ev_db[ID]

        charStr = " -> ".join([ev['eventRep'] for ev in evp['events']])
        goldResultStr = utils.getColoredAlign(data_dict['goldResult'], highlight_color='green')
        outputResultStr = utils.getColoredAlign(data_dict['outputResult'], highlight_color='red')
        row_data.update( {'charStr': charStr, 'goldResult': goldResultStr, 'outputResult': outputResultStr} )
        
        for ev_num, ev in enumerate(evp['events']):
            givenArgs, supArgs = ev['givenArgs'], ev['supArgs']

            for case in ['g', 'w', 'n', 'd']:
                table_key = "%s%s" % (case, ev_num + 1)

                if case not in givenArgs.keys():
                    row_data[table_key] = ""
                else:
                    args = [utils.removeHira(x, concatenate=True) for x in supArgs[case].keys()]
                    row_data[table_key] = utils.encode_list(args)

            pred = [utils.removeHira(x) for x in ev['predRep'].split('?')]
            row_data["pred%s" % (ev_num + 1)] = utils.encode_list(pred)

        return {k: v.decode('utf-8') for k, v in row_data.iteritems()}


class EventPairTable(object):
    table_name = "eventpair"

    def __init__(self, metadata, config):
        self.ev_db = shelve.open(config.ev_db, flag='r')
        self.feat_db = shelve.open(config.feat_db, flag='r')
        self._init_columns(metadata)

    def _init_columns(self, metadata):
        output_table = Table(self.table_name, metadata, 
                             Column("ID", String(), primary_key=True),
                             Column("charStr", String()),
                             Column("gold", String()),
                             Column("pred1", String()), Column("pred2", String()),
                             Column("cfs1", String()), Column("cfs2", String()),
                             Column("cf_urls1", String()),
                             Column("cf_urls2", String()),
                             Column("rnnsp_tops_1", String()),
                             Column("rnnsp_tops_2", String()))

        output_table.create()
        self.insert_cursor = output_table.insert()

    def set_rows(self, result_data):
        for ID, data_dict in result_data.iteritems():
            row_data = self._convert_result_data(ID)
            self.insert_cursor.execute(**row_data)

    def _convert_result_data(self, ID):
        evp = self.ev_db[ID]
        feats = self.feat_db[ID]
        row_data = {}

        charStr = " -> ".join([ev['eventRep'] for ev in evp['events']])
        gold = " ".join(feats['goldRaw']) if feats['goldRaw'] != None else ""
        gold = gold.replace("'", "’")
        row_data.update( {"ID": ID, "charStr": charStr, "gold": gold} )

        for ev_num, ev in enumerate(evp['events']):
            pred = utils.removeHira(ev['predRep'])
            cfs_data = [ "[%s] %s(%.3f)" % (cf.cf_id, cf.cf_str, cf.rel_score) for cf in ev['cfs'] ]
            cf_urls = [ utils.get_url(cf.cf_id) for cf in ev['cfs'] for cf in ev['cfs'] ]

            row_data["pred%s" % (ev_num + 1)] = pred
            row_data["cfs%s" % (ev_num + 1)] = utils.encode_list(cfs_data)
            row_data["cf_urls%s" % (ev_num + 1)] = utils.encode_list(cf_urls)

            if 'rnnsp_tops' not in ev.keys():
                row_data["rnnsp_tops_%s" % (ev_num + 1)] = ""
            else:
                tops_list = ["[X %s %s]: %s" % (utils.ENG_HIRA[case], ev['eventRep'], ' | '.join(t_list)) for case, t_list in ev['rnnsp_tops'].items()]
                row_data["rnnsp_tops_%s" % (ev_num + 1)] = utils.encode_list(tops_list)

        return {k: v.decode('utf-8') for k, v in row_data.iteritems()}


class GeneralFeatureTable(object):
    table_name = "general_feature"

    def __init__(self, metadata, config):
        self.ev_db = shelve.open(config.ev_db, flag='r')
        self.feat_db = shelve.open(config.feat_db, flag='r')
        self._init_columns(metadata)

    def _init_columns(self, metadata):
        output_table = Table(self.table_name, metadata, 
                             Column("ID", String(), primary_key=True),
                             Column("conflict", String()),
                             Column("contextArg", String()),
                             Column("contextCase", String()),
                             Column("embed", String()),
                             Column("embed_s", String()),
                             Column("contextArgText", String()),
                             Column("contextCaseText", String()) )

        output_table.create()
        self.insert_cursor = output_table.insert()

    def set_rows(self, result_data):
        for ID, data_dict in result_data.iteritems():
            row_data = self._convert_result_data(ID)
            self.insert_cursor.execute(**row_data)

    def _convert_result_data(self, ID):
        contributors = self.ev_db[ID]['feature_contributors']['general']
        feats = self.feat_db[ID]['features']['general']
        row_data = {}
        
        row_data['ID'] = ID

        for feat_type in ["conflict", "embed", "embed_s", "cArg", "cCase"]:
            # will be modify in the future
            feat_col_name = feat_type if feat_type not in ['cArg', 'cCase'] else feat_type.replace('c', 'context')
            # will be modify in the future
            if feat_type not in feats:
                row_data[feat_col_name] = ""
            else:
                row_data[feat_col_name] = utils.encode_dict(feats[feat_type])

            if feat_type in contributors:
                row_data["%sText" % feat_col_name] = utils.encode_dict(contributors[feat_type])

        return {k: v.decode('utf-8') for k, v in row_data.iteritems()}

class cfFeatureTable(object):
    table_name = "cf_feature"
    def __init__(self, metadata, config):
        self.ev_db = shelve.open(config.ev_db, flag='r')
        self.feat_db = shelve.open(config.feat_db, flag='r')
        self._init_columns(metadata)

    def _init_columns(self, metadata):
        output_table = Table(self.table_name, metadata, 
                             Column("ID", String(), primary_key=True),
                             Column("cfsim", String()),
                             Column("contextArg", String()),
                             Column("contextCase", String()),
                             Column("cfsimText", String()),
                             Column("contextArgText", String()),
                             Column("contextCaseText", String()) )

        output_table.create()
        self.insert_cursor = output_table.insert()

    def set_rows(self, result_data):
        for ID, data_dict in result_data.iteritems():
            sys.stderr.write('%s\n' % ID)
            for row_data in self._convert_result_data(ID):
                self.insert_cursor.execute(**row_data)

    def _convert_result_data(self, ID):
        evp = self.ev_db[ID]
        feats = self.feat_db[ID]['features']

        for cf_pair, cf_dict in feats.iteritems():
            if cf_pair == "general":
                continue

            row_data = {}
            row_data["ID"] = "%s_%s" % (ID, cf_pair)

            contributors = evp['feature_contributors'][cf_pair]
            for feat_type in ["cfsim", "cArg", "cCase"]:
                feat_col_name = feat_type if feat_type in ["cfsim"] else feat_type.replace('c', 'context')

                if feat_type in cf_dict:
                    row_data[feat_col_name] = utils.encode_dict({k: v for k, v in cf_dict[feat_type].iteritems() if '-' in k})
                else:
                    row_data[feat_col_name] = ""

                if feat_type in contributors:
                    row_data["%sText" % feat_col_name] = utils.encode_dict(contributors[feat_type])

            yield {k: v.decode('utf-8') for k, v in row_data.iteritems()}

