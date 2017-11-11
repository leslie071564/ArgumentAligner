#!/bin/sh
input_ver="$1"
extract_dir="$2"

extract_script=./extract.py

# write config file.
mkdir -p $extract_dir
config_file=$extract_dir/extract_config.yaml
python $extract_script write_config "$@" --config_file $config_file

# generate task file from input arg_file 
arg_file=`cat $config_file | shyaml get-value input_pas.arg_file`
task_file=./extract.task
python $extract_script print_task --arg_file $arg_file --config_file $config_file --task_file $task_file
echo $task_file

# extract eventChain data by gxpc.
log_file=`cat $config_file | shyaml get-value output.log`
tmpDBDir=`cat $config_file | shyaml get-value output.tmp_db_dir`
mkdir -p $tmpDBDir
gxpc js -a work_file=extract.task -a cpu_factor=0.125 2> $log_file

# merge
python $extract_script merge_tmp_db --config_file $config_file

#rm tmp files
rm -f $task_file
rm -rf $tmpDBDir
