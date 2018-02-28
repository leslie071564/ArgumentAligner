#!/bin/sh
NICE="nice -n 19"
exp_dir="$1"
config_file="$2"

SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"
train_script=$SCRIPTPATH/train.sh
test_script=$SCRIPTPATH/test.sh

# mkdir.
result_dir=$exp_dir/result
mkdir -p $exp_dir $result_dir

exp_config=$exp_dir/exp_config.yaml
cp $config_file $exp_config

IDS_raw=`cat $config_file | shyaml get-value db.ids`
IDS=$exp_dir/ids.txt
cp $IDS_raw $IDS

# split ids for each cv-fold.
shuf $IDS --output=$IDS
total_instance_num=$(cat $IDS | wc -l)
cv_fold_num=$(( `cat $config_file | shyaml get-value CV.FoldNum` ))
fold_instance=$(($total_instance_num / $cv_fold_num + 1))
split -dl $fold_instance -a 1 $IDS $exp_dir/ids_

for i in $(seq 0 $(( $cv_fold_num -1)) )
do
    cv_dir=$exp_dir/$i
    train_dir=$cv_dir/train
    test_dir=$cv_dir/test
    mkdir -p $train_dir $test_dir

    cp $exp_dir/ids_* $cv_dir
    mv $cv_dir/ids_$i $test_dir/ids.txt
    cat $cv_dir/ids_* > $train_dir/ids.txt
    rm -f $cv_dir/ids_*

    echo "##### in the $i-th fold #####"
    $train_script $train_dir $exp_config
    $test_script $test_dir $exp_config $train_dir/model

    sed -i '/@[eb]oi/d;/Accuracy*/d' $test_dir/result.txt
    cp $test_dir/result.txt $result_dir/result_$i.txt
    cp $train_dir/model $result_dir/model_$i
done

# evaluation
eval_dir=$SCRIPTPATH/../eval
python $eval_dir/evaluation.py --result_dir $result_dir/result_ --config_file $exp_config --print_scores
