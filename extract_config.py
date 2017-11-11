# -*- coding: utf-8 -*-

EXTRACT_DBS = {'CF_CDB': '/windroot/huang/cf_cdbs/20170502/new_cdb/new_cf.cdb.keymap',\
               'COUNT_DB': '/windroot/huang/EventCounts/EventCounts_customized/all_count.cdb.keymap',\
               'KNP_INDEX_DB': '/pear/huang/knp_index_dbs/knp_index_$input_ver/knp_index.cdb.keymap',\
               'KNP_PARENT_DIR': '/pear/huang/knp_index_dbs/knp_index_$input_ver/knp_parent_dir',\
              }

GOLD_INPUT_DEFS = {'arg_file': '/windroot/huang/argumentAligner/goldExp/all_event_pair.txt',\
                   'gold_file': '/windroot/huang/argumentAligner/goldExp/gold.txt',\
                   'input_dir': '/zinnia/huang/EventKnowledge/data',\
                   'word_replace': '$input_dir/db/wordreplace.cdb',\
                   'key2sid': '$input_dir/pa_pairs_relation_db/pa_pairs_relation.cdb.keymap',\
                   'sid2pa': '$input_dir/sid2pa/sid2pa.cdb.keymap',\
                   'sid2sent_dir': '/zinnia/shibata/tsubame.results.orig-cdb'
                   }

INPUT_DEFS_170724 = {'arg_file': '$extract_dir/input_pas.txt',\
                     'gold_file': None,\
                     'input_dir': '/zinnia/shibata/work/InferenceRuleAcquisition/170724',\
                     'word_replace': '$input_dir/db/wordreplace.cdb',\
                     'key2sid': '$input_dir/input/sqlite/pa_pairs.sqlite',\
                     'sid2pa': '$input_dir/sid2pa/sid2pa.cdb.keymap',\
                     'sid2sent_dir': '/pear/share/www-uniq/v2006-2015.text-cdb',\
                    }
    
INPUT_DEFS_170905 = {'arg_file': '$extract_dir/input_pas.txt',\
                     'gold_file': None,\
                     'input_dir': '/zinnia/shibata/work/InferenceRuleAcquisition/170905',\
                     'word_replace': '$input_dir/db/wordreplace.cdb',\
                     'key2sid': '$input_dir/input/sqlite/pa_pairs.sqlite',\
                     'sid2pa': '$input_dir/sid2pa/sid2pa.cdb.keymap',\
                     'sid2sent_dir': '/pear/share/www-uniq/v2006-2015.text-cdb',\
                    }

OUTPUT = {'extract_dir': '$extract_dir',\
          'ev_db': '$extract_dir/ev.db',\
          'feat_db': '$extract_dir/feat.db',\
          'log': '$extract_dir/log.txt',\
          'ids': '$extract_dir/ids.txt',\
          'tmp_db_dir': '$extract_dir/tmp',\
         }
    
INPUT_DEFS = {'gold': GOLD_INPUT_DEFS, '170724': INPUT_DEFS_170724, '170905': INPUT_DEFS_170905}
