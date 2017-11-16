# -*- coding: utf-8 -*-
import sys
import re
import os
import glob
import cdb
import itertools
from math import sqrt
from pyknp import Juman
from itertools import permutations
juman = Juman(command="/home/huang/usr/bin/juman", rcfile="/home/huang/usr/etc/jumanrc")

CASE_ENG = ['g', 'w', 'n', 'd']
CASE_VERBOSE = ['ga', 'wo', 'ni', 'de']
CASE_KATA = [u"ガ", u"ヲ", u"ニ", u"デ"]
CASE_HIRA = [u"が", u"を", u"に", u"で"]

ENG_HIRA = dict(zip(CASE_ENG, CASE_HIRA))
ENG_KATA = dict(zip(CASE_ENG, CASE_KATA))
KATA_ENG = dict(zip(CASE_KATA, CASE_ENG))
KATA_VER = dict(zip(CASE_KATA, CASE_VERBOSE))

ALL_ALIGN = []
for i in [1,2,3,4]:
    for p1 in itertools.combinations(CASE_ENG, i):
        for p2 in itertools.permutations(CASE_ENG, i):
             align = ["%s-%s" % (p1[x], p2[x]) for x in range(i)]
             if align not in ALL_ALIGN:
                 ALL_ALIGN.append(align)
ALL_ALIGN.append([])

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

def getArgsRep(args):
    arg_reps = ["(%s) %s" % (",".join(arg_list), ENG_HIRA[case].encode('utf-8')) for case, arg_list in args.items()]
    return " ".join(arg_reps)

def getAmbiguousPredicate(predRep):
    postfix = ""
    if predRep.split('+') > 1:
        postfix = "+".join(predRep.split('+')[1:])

    result = juman.analysis(predRep.split('/')[0].decode('utf-8'))
    ambPred = result.mrph_list()[0].repnames()
    ambPred = "%s+%s" % (ambPred, postfix) if postfix else ambPred

    return ambPred if ambPred != predRep else None

def getAmbiguousPredicates(predRep):
    ambPreds = []
    for pred in predRep.split('?'):
        postfix = '+'.join(pred.split('+')[1:]) if '+' in pred else ""

        result = juman.analysis(pred.split('/')[0].decode('utf-8'))
        amb = result.mrph_list()[0].repnames()
        ambs = ["?".join(x) for x in permutations(amb.split('?'))]

        if postfix != "":
            ambPreds = ["%s+%s" % (amb, postfix) for amb in ambs]
        else:
            ambPreds += ambs
    return ambPreds


### file operation
def search_file_with_prefix(prefix, extension=None):
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
def cosineSimilarity(v1, v2, strip=False, skip_set = [u"<主体準>"], restrict_set=[], get_contributors=False, threshold=0):
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

    if threshold != 0:
        restrict_set1 = [arg for arg, count in v1.iteritems() if count > threshold]
        restrict_set2 = [arg for arg, count in v2.iteritems() if count > threshold]
        restrict_set = set(restrict_set1) & set(restrict_set2)

    # calculate inner product
    inner, contribute_list = 0, []
    for w in set(v1.keys()).intersection(set(v2.keys())):
        if w in skip_set:
            continue
        if restrict_set == [] or w in restrict_set:
            inner += v1[w]*v2[w]
            if get_contributors:
                contribute_list.append("%s(%s,%s)" % (w, v1[w],v2[w]))

    return inner/denom if not get_contributors else (inner/denom, "<br>".join(contribute_list) )

def vector_norm(v):
    n2 = 0
    for key, value in v.iteritems():
        if key == 'all':
            continue
        n2 += value ** 2
    return sqrt(n2)

#
def getExpandedAlign(aligns):
    alignDict = getAlignCorrespondence(aligns)
    expandedAlign = [x for x in set(sum(alignDict.values(), [])) if x != ""]
    return expandedAlign
    
def getAllPossibleAlign(aligns):
    alignDict = getAlignCorrespondence(aligns)
    allPossible = list(itertools.product(*alignDict.values()))

    allPossible = [[x for x in conf if x != ""] for conf in allPossible]
    return allPossible

def getAlignCorrespondence(aligns):
    """
    For the alignment configuration provided, return a dictionary of each alignment with its correspondent set of alignments.
        ex: g/w-w =>[g-w, w-w]
    """
    if aligns == ['null'] or aligns == ['X']:
        return {}
    alignCorresponceDict = {}
    checkZero = ['(', ')', 'p', 'g2']
    for align in aligns:
        nullAlignFlag, acceptSet = False, []
        originalAlign = align

        # parenthisis/p/g2
        if any(x in align for x in checkZero):
            nullAlignFlag = True
            align = align.translate(None, '()2')

        # Multi.
        c1s, c2s = map(lambda x: x.split('/'), align.split('-'))
        acceptSet += ["%s-%s" % (c1, c2) for c1, c2 in itertools.product(c1s, c2s) if 'p' not in [c1, c2]]

        # Quasi.
        if all("\'" in case for case in c1s) or all("\'" in case for case in c2s):
            nullAlignFlag = True
        acceptSet = map(lambda x: x.replace("\'", ""), acceptSet)

        # d-d.
        if 'd-d' in acceptSet:
            nullAlignFlag = True
        acceptSet = list(set(acceptSet))

        # null alignment.
        if nullAlignFlag:
            acceptSet.append("")

        alignCorresponceDict[originalAlign] = acceptSet

    return alignCorresponceDict

###
def getNounRep(thisTag, prevTag):
    # 正規化代表表記? 
    thisRep = thisTag.repname.split('+')
    if not thisRep:
        return None

    flag = False
    if len(thisRep) == 1 and len(thisRep[0].split('/')[0]) == 1:
        flag = True

    if prevTag: 
        prevMrph = prevTag.mrph_list()[-1]
    else:
        prevMrph = None

    for mrph in thisTag.mrph_list():
        if mrph.repname not in thisRep:
            prevMrph = mrph
            continue
        mrph_index = thisRep.index(mrph.repname)
        if mrph.hinsi == u"特殊":
            return None
        thisRep[mrph_index] = replace_by_category(mrph)
        if flag:
            if u"<複合←>" in mrph.fstring or mrph.hinsi == u"接尾辞":
                prevMrphRep = replace_by_category(prevMrph)
                if not prevMrphRep:
                    return None
                thisRep.insert(0, prevMrphRep)
                break
    return "+".join(thisRep)

def replace_by_category(mrph):
    if not mrph:
        return None
    if mrph.bunrui in [u"数詞", u"人名", u"地名"]:
        return "[%s]" % mrph.bunrui
    return mrph.repname

def removeHira(verboseStr, splitChar=['+'], concatenate=False):
    verboseStrs = re.split(r'[%s]+' % ("".join(splitChar)), verboseStr)
    shortStrs = map(lambda x: x.split('/')[0], verboseStrs)

    if concatenate:
        return "".join(shortStrs)
    return "+".join(shortStrs)

def get_sentence_by_sid(sid, sid2sent_dir):
    sid = sid.split('%')[0]
    sid_components = sid.split('-')

    if os.path.basename(sid2sent_dir) == "tsubame.results.orig-cdb":
        sub_dirs = [sid_components[0], sid_components[1][:4], sid_components[1][:6]]
        sub_dir_str = "/".join(sub_dirs)

    elif os.path.basename(sid2sent_dir) == "v2006-2015.text-cdb": 
        if 'data' in sid:
            sid_components = [x for x in sid_components if x != ""]
            sub_dirs = [sid_components[0], sid_components[1]] + list(sid_components[2][:3]) + [sid_components[2][:4]]
            sub_dir_str = "/".join(sub_dirs)
        else:
            sub_dirs = [sid_components[0]] + list(sid_components[1][:3]) + [sid_components[1][:4]]
            sub_dir_str = "/".join(sub_dirs)

    sid2sent = "%s/%s.cdb" % (sid2sent_dir, sub_dir_str)
    SID2SENT = cdb.init(sid2sent.encode('utf-8'))

    sent = SID2SENT.get(sid)
    if sent == None:
        sys.stderr.write("Cannot retrieve sentence of sid:%s.\n" % sid)
    return sent

