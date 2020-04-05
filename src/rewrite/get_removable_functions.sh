ROOT_DIR="/home/chenxiong/slimium/out"
LOG_DIR="$ROOT_DIR/last_logs"
UNIQUE_INDEX_FILE="$ROOT_DIR/unique_indexes.txt"
INDEX_FILE="$ROOT_DIR/index.txt"
CALLGRAPH_FILE="$ROOT_DIR/callgraph.txt"
FUNCTION_BOUNDARIES_FILE="$ROOT_DIR/function_boundaries.txt"
PROFILING_BASE_FILE="$ROOT_DIR/baseline.log"
NONDETERMINISTIC_FUNCTIONS_FILE="$ROOT_DIR/nondeterministic_funcs.txt"

cmd="python get_removable_functions.py -u $UNIQUE_INDEX_FILE -i $INDEX_FILE -c $CALLGRAPH_FILE -f $FUNCTION_BOUNDARIES_FILE -b $PROFILING_BASE_FILE 
-n $NONDETERMINISTIC_FUNCTIONS_FILE -l $LOG_DIR -m $1 -o $2 -p $3"

echo $cmd
eval $cmd
