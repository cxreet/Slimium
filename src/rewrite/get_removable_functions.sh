ROOT_DIR="/home/chenxiong/slimium/out"
UNIQUE_INDEX_FILE="$ROOT_DIR/unique_indexes.txt"
INDEX_FILE="$ROOT_DIR/index.txt"
CALLGRAPH_FILE="$ROOT_DIR/callgraph.txt"
FUNCTION_BOUNDARIES_FILE="$ROOT_DIR/function_boundaries.txt"
PROFILING_BASE_FILE="$ROOT_DIR/baseline.log"
NONDETERMINISTIC_FUNCTIONS_FILE="$ROOT_DIR/nondeterministic_funcs_manual_map_1000_1.txt"

cmd="python3 get_removable_functions.py -u $UNIQUE_INDEX_FILE -i $INDEX_FILE -c $CALLGRAPH_FILE -f $FUNCTION_BOUNDARIES_FILE -b $PROFILING_BASE_FILE 
-n $NONDETERMINISTIC_FUNCTIONS_FILE -l $1 -m $2 -o $3 -p $4"

echo $cmd
eval $cmd
