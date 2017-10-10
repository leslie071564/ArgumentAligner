#!/bin/sh
config_file=$1
extract_script=./extract.py

# generate task file from input arg_file 
arg_file=`cat $config_file | shyaml get-value Raw.ARG_FILE`
task_file=./extract.task
log_file=./tmp
python $extract_script print_task --arg_file $arg_file --config_file $config_file --task_file $task_file

# extract eventChain data by gxpc.
tmpDBDir=`cat $config_file | shyaml get-value Output.TMP_DB_DIR`
mkdir -p $tmpDBDir
gxpc js -a work_file=extract.task -a cpu_factor=0.25 2> $log_file

# merge
python $extract_script merge_tmp_db --config_file $config_file

#rm tmp files
rm -f $task_file
rm -rf $tmpDBDir
