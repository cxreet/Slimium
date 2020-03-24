#!/bin/bash

UNIQUE_INDEXE_FILE="/home/chenxiong/slimium/out/unique_indexes.txt"
INDEX_FILE="/home/chenxiong/slimium/out/index.txt"
CALLGRAPH_FILE="/home/chenxiong/slimium/out/callgraph.txt"
FUNCTION_BOUNDARIES_FILE="/home/chenxiong/slimium/out/function_boundaries.txt"

python auto_extend_mapping.py -u $UNIQUE_INDEXE_FILE -i $INDEX_FILE -c $CALLGRAPH_FILE -f $FUNCTION_BOUNDARIES_FILE -m $1 -a $2 -b $3 -o $4
