# -*- coding: utf-8 -*-
import sys
import os
import glob
import cdb
from math import sqrt
from pyknp import Juman
juman = Juman(command="/home/huang/usr/bin/juman", rcfile="/home/huang/usr/etc/jumanrc")

CASE_ENG = ['g', 'w', 'n', 'd']
CASE_KATA = [u"ガ", u"ヲ", u"ニ", u"デ"]
CASE_HIRA = [u"が", u"を", u"に", u"で"]

ENG_HIRA = dict(zip(CASE_ENG, CASE_HIRA))
ENG_KATA = dict(zip(CASE_ENG, CASE_KATA))
KATA_ENG = dict(zip(CASE_KATA, CASE_ENG))

VOICE = ['A','P','C','K','M','L']
VOICE_SUFFIX = [[""],[u"[受動]",u"[受動│可能]"], [u"[使役]"], [u"[可能]"], [u"[もらう]"], [u"[判]"]]
VOICE2SUFFIX = dict(zip(VOICE, VOICE_SUFFIX))

NEG = ['v', 'j', 'n']
NEG_SUFFIX = ["", u"[準否定]", u"[否定]"]
NEG2SUFFIX = dict(zip(NEG, NEG_SUFFIX))

def getPredRep(vStr, voice):
    postfix = {'P': "+れる/れる", 'C': "+せる/せる", 'sahen': "+する/する"}
    if voice in ['P', 'C']:
        if isSahen(vStr):
            vStr += postfix['sahen']
        vStr += postfix[voice]

    return vStr

def isSahen(vStr):
    result = juman.analysis(vStr.decode('utf-8').split('/')[0])
    if len(result.mrph_list()) == 1 and result.mrph_list()[0].bunrui == u'サ変名詞':
        return True
    return False

def getAmbiguousPredicate(predRep):
    postfix = ""
    if predRep.split('+') > 1:
        postfix = "+".join(predRep.split('+')[1:])

    result = juman.analysis(predRep.split('/')[0].decode('utf-8'))
    ambPred = result.mrph_list()[0].repnames()
    ambPred = "%s+%s" % (ambPred, postfix) if postfix else ambPred

    return ambPred if ambPred != predRep else None

### file operation
def seaech_file_with_prefix(prefix, extension=None):
    in_dir = os.path.dirname(prefix)
    if extension:
        search_prefixes = ["%s*.%s" % (prefix, extension)]
    else:
        search_prefixes = ["%s*" % prefix ]

    all_files = []
    for search_prefix in search_prefixes:
        all_files += glob.glob(search_prefix)

    return all_files

def search_cdbs(cdbs, key, save_null=False):
    hits = []
    for this_cdb in cdbs:
        this_cdb = cdb.init(this_cdb)
        this_hits = this_cdb.get(key)
        if this_hits != None or save_null:
            hits.append(this_hits)
    return hits
### Features. 
def cosineSimilarity(v1, v2, strip=False, skip_set = [u"<主体準>"], restrict_set=[], get_contributors=False):
    """
    calculate cosine similarity of two dictionary-vector.
    """
    norm_v1, norm_v2 = vector_norm(v1), vector_norm(v2)
    denom = norm_v1 * norm_v2
    if denom == 0:
        return 0 if not get_contributors else (0, [])

    if strip:
        v1 = {"+".join(map(lambda x: x.split('/')[0], arg.split('+'))) : count for arg, count in v1.iteritems()}
        v2 = {"+".join(map(lambda x: x.split('/')[0], arg.split('+'))) : count for arg, count in v2.iteritems()}

    # calculate inner product
    inner, contribute_list = 0, []
    for w in set(v1.keys()).intersection(set(v2.keys())):
        if w in skip_set:
            continue
        if restrict_set == [] or w in restrict_set:
            inner += v1[w]*v2[w]
            if get_contributors:
                contribute_list.append("%s(%s,%s)" % (w, v1[w],v2[w]))

    return inner/denom if not get_contributors else (inner/denom, contribute_list)

def vector_norm(v):
    n2 = 0
    for key, value in v.iteritems():
        if key == 'all':
            continue
        n2 += value ** 2
    return sqrt(n2)

