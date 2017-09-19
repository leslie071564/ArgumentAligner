# -*- coding: utf-8 -*-
import sys
import yaml
import argparse
from argparse import Namespace
from FeatureGenerator import FeatureGenerator
import utils

def setArgs(parser):
    subparsers = parser.add_subparsers(dest="_subcommand")

    test_parser = subparsers.add_parser("print_test")
    test_parser.add_argument("--config_file", action="store", dest="config_file")
    test_parser.add_argument('-i', "--id", action="store", dest="id")
    test_parser.add_argument('-g', "--only_gold_align", action='store_true', dest="only_gold_align")
    #test_parser.add_argument('-w', "--without_impossible_align", action='store_true', dest="without_impossible_align")
    test_parser.add_argument('-o', "--output_file", action='store', dest='output_file')

    train_parser = subparsers.add_parser("print_train")
    train_parser.add_argument("--config_file", action="store", dest="config_file")
    train_parser.add_argument('-k', "--key", action='store', dest='key')
    train_parser.add_argument('-o', "--output_file", action='store', dest='output_file')

    return parser

def setPrintFeatureConfig(config_file):
    config = yaml.load(open(config_file, 'r'))
    feature_config = Namespace()

    feature_config.feat_db = config['DB']['FEAT']

    feature_config.normalFeats, feature_config.rivalFeats, feature_config.combFeats = [], [], []
    for feat in config['Feature extraction']['Load']:
        if feat.endswith('Riv'):
            feature_config.rivalFeats.append(feat)
        elif "*" in feat:
            feature_config.combFeats.append(feat)
        else:
            feature_config.normalFeats.append(feat)

    feature_config.neg_sample_size = config['Training']['NegSample']
    return feature_config

def print_train_feature_file(options):
    feature_config = setPrintFeatureConfig(options.config_file)
    printer = FeatureGenerator(feature_config)
    feature_strs = printer.get_train_features(options.key)

    output_file = open(options.output_file, 'w')
    output_file.write('\n'.join(feature_strs))
    output_file.close()

def print_test_feature_file(options):
    feature_config = setPrintFeatureConfig(options.config_file)
    printer = FeatureGenerator(feature_config)
    feature_strs = printer.get_test_features(options.id, only_gold=options.only_gold_align)

    output_file = open(options.output_file, 'w')
    output_file.write('\n'.join(feature_strs))
    output_file.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    setArgs(parser)
    options = parser.parse_args() 
    
    if options._subcommand == "print_train":
        print_train_feature_file(options)

    elif options._subcommand == "print_test":
        print_test_feature_file(options)

