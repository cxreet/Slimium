#!/bin/bash
LOG_DIR="/home/chenxiong/slimium/out/profile_out/"
UNIQUE_INDEX_FILE="/home/chenxiong/slimium/out/unique_indexes.txt"
FUNCTION_BOUNDARIES_FILE="/home/chenxiong/slimium/out/function_boundaries.txt"

python ./count_nondeterministic_code.py -l $LOG_DIR -u $UNIQUE_INDEX_FILE -d $FUNCTION_BOUNDARIES_FILE -m $1 -n $2 -a $3 -o $4
