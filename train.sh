#!/bin/sh
NICE="nice -n 19"
exp_dir="$1"
config_file="$2"

# set paths
ids=$exp_dir/ids.txt
model=$exp_dir/model
key_file=$exp_dir/train_key.txt
new_key_file=$exp_dir/train_key_new.txt

choose_dir=$exp_dir/choose
train_dir=$exp_dir/train
mkdir -p $choose_dir $train_dir

train_script=./train_utils.py

# print choose files.
choose_task_file=./choose.task
python $train_script print_choose_task --config_file $config_file --ids_file $ids --output_dir $choose_dir > $choose_task_file
gxpc js -a work_file=choose.task -a cpu_factor=0.25
rm -f $choose_task_file

# initilize
# to be modified
python $train_script initialize --ids_file $ids --key_file $key_file --config_file $config_file

# train recursively.
iter_max=$(( `cat $config_file | shyaml get-value Training.IterMax` ))
for i in $(seq 1 $iter_max)
do
    echo "##### iteration $i #####"
    train_task_file=./train.task
    python $train_script print_train_task --config_file $config_file --key_file $key_file --output_dir $train_dir > $train_task_file
    gxpc js -a work_file=train.task -a cpu_factor=0.25
    echo learn model:
    classias-train -tc -a lbfgs.logistic -m $model $train_dir/*

    # check convergence
    cat $choose_dir/* | classias-tag -m $model > $new_key_file
    sed -i '/^@/d' $new_key_file
    if cmp --silent $new_key_file $key_file 2>&1
    then
        echo "converged at iter$i"
        break
    fi
    echo "continue"
    mv $new_key_file $key_file

    rm -f $train_task_file
done

echo "model: $model"
