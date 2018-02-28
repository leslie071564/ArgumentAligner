#!/bin/sh
NICE="nice -n 19"
exp_dir="$1"
config_file="$2"
model="$3"

#model=`cat $config_file | shyaml get-value MODEL`

# set paths
ids=$exp_dir/ids.txt
result_file=$exp_dir/result.txt

test_dir=$exp_dir/test
mkdir -p $test_dir

SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"
train_script=$SCRIPTPATH/train_utils.py

# create test files
test_task_file=./test.task
python $train_script print_test_task --config_file $config_file --ids_file $ids --output_dir $test_dir > $test_task_file
gxpc js -a work_file=test.task -a cpu_factor=0.25
rm -f $test_task_file

# print result_file
cat $test_dir/* | classias-tag -m $model -tk > $result_file
echo result file: $result_file
