# Slimium

## Setup

###  Get Chromium source code
1. Install `dep_tools` following this [link](https://chromium.googlesource.com/chromium/src/+/master/docs/linux/build_instructions.md).
2. Get the code: 
	- `mkdir ~/chromium && cd ~/chromium`
	- `fetch --nohooks chromium`
	- `cd src && git checkout -b branch_77.0.3864.0 77.0.3864.0`
	- `gclient sync --with_branch_heads --with_tags`

### Get customized llvm source code
1. Download and build `11vm` from this [link](https://github.com/cxreet/11vm).
2. Modify `llvm/lib/Transforms/Scalar/DumpIR.cpp` line 81 to change the directory path that you want to store the LLVM bitcode.

### Compile Chromium
Go to Chromium source code `src` and do some preparations:
1. `./build/install-build-deps.sh`
2. `gclient runhooks`
3.  Patch `build/config/compiler/BUILD.gn` with file `slimium/chromium-build-config/BUILD.gn`(line 43 ~ 49 and line 252 ~ 268).

#### Build Chromium to Dump LLVM IR
1. `gn gen out/DumpIR`
2. `cp slimium/chromium-build-config/dump_ir_args.gn out/DumpIR/args.gn`
3. `autoninja -C out/DumpIR chrome`
4. After compiling chromium, the LLVM bitcode would be dumped into the directory specified in file `llvm/lib/Transforms/Scalar/DumpIR.cpp` (line 81).

#### Static Analysis
After we get the LLVM IR bitcode, we need to do static analysis (i.e., building call graph, creating unique indexes for each function, etc.).

##### Build Call Graph
1. `cd slimium/src/static_analysis/devirt`
2. Customize `Makefile` to change `LLVM_BUILD` to point to your own llvm build directory.
3. `make`
4. Run `devirt` to build a call graph: `./build/Devirt ~/bitcodes/chromium/ ~/slimium/out/`. (`~/bitcodes/chromium/` is the directory used for storing LLVM IR bitcode and `~/slimium/out` is assumed to be the out directory for `devirt`)
5. Under the out directory: `index.txt` contains the mapping between ID and function name, each line is in the format of `ID function_name`; `callgraph.txt` contains the call graph, each line is in the format of `caller_ID callee1_ID callee2_ID callee3_ID ...`. Note that the IDs here can be duplicated, which means functions with same names share same ID even though the functions are from different source code files.

##### Get Unique IDs
1. `cd slimium/src/static_analysis/group-functions`
2. Customize `Makefile` to change `LLVM_BUILD` to point to your own llvm build directory.
3. `make`
4. Run `GroupFunctions`: `./build/GroupFunctions ~/bitcodes/chromium/ ~/slimium/out/index.txt ~/slimium/out/`. The first argument is directory that stores LLVM IR bitcode and the second argument is the index file generated from "**Build Call Graph**", and the third argument is the output directory.
5. The above step generate a file `file_functions.txt`. Each line is in the format of `bitcode_file function1_ID function2_ID function3_ID ...`.
6. `cd ..` and `python generate_unique_indexes.py ~/slimium/out/index.txt ~/slimium/out/file_functions.txt > ~/slimium/out/unique_indexes.txt` 
7. The above step generates `unique_indexes.txt`, which contains unique indexes for functions even when they have same names. Each line is in the format of `bitcode_file function1_ID function1_name function2_ID function2_name ...`.

#### Build Chromium for profiling
Now, we have some static analysis results based on the LLVM IR bitcode. Let's build chromium for profiling purpose. 
##### Create Shared Memory
1. Check `slimium/out/unique_indexes.txt` to get the total function number by look at the last line's last ID. For example, if it's `965973`, then total function number is `965974`.
2. `cd slimium/src/shm`
3. Edit `defs.h` to change line 4 to the total function number. (You can also change line 5 to some key you like.)
4. `make clean && make`
5. Create a shared memory: `./shm_create`.
6. Edit `11vm/llvm/lib/Transforms/Scalar/EnableProfiling.cpp` (line 178 ~ 179) based on `shm_clear.ll`(line 18 ~ 21).

##### Build A LLVM Pass for Profiling Instrumentation
1. `cd 11vm`
2. Edit `llvm/lib/Transforms/Scalar/EnableProfiling.cpp` to change line 240 to let `index_file` point to the absolute path of the `unique_indexes.txt`.
3. ``cd build && make -j`nproc` ``

##### Build chromium binary
1. `cd chromium/src`
2. `gn gen out/Profiling`
3. `cp slimium/chromium-build-config/profiling_args.gn out/Profiling/args.gn`
4. `autoninja -C out/Profiling chrome`
5. Note that during compiling, it runs some tests, so that some instrumented binaries would be executed and if you go to `slimium/src/shm` and run `./shm_decode`, you may see results like `In total, xxxx (0.xxx) out of 965974 functions are executed!`
6. To profile a website such as `youtube.com`:
	```
	- ~/slimium/src/shm/shm_clear (clear the shared memory)
	- ./out/Profiling/chrome youtube.com
	- ~/slimium/src/shm/shm_decode (dump the executed functions)
	```
## Evaluation
### 1. Get function boundaries
1. `cd slimium/src/disassemble`
2. `python disassemble_marking.py ~/chromium/src/out/Marking/chrome ~/slimium/out/function_boundaries.txt`
3. Note that the output is in `function_boundaries`, each line is in the format of `function_id function_start_address function_end_address function_name`.

### 2. Extend feature-code map
1. `cd slimium/src/feature_code_mapping`
2. The `manual_feature_code_map.json` is the manually defined feature-code map, and all the extended prebuilt feature-code maps are under `src/feature_code_mapping/extended_feature_code_maps/`.
3. If you want to generate the extended feature-code maps by yourself:
	- `pip install textdistance`
	- Edit `auto_extend_mapping.sh` to change the variables to point to your relevant file paths
	- Run `./auto_extend_mapping.sh ./manual_feature_code_map.json 0.9 0.9 ./extended_0.9_0.9_map.json` to get the extended feature-code map.
	- Note that the parameters of `auto_extend_mapping.sh` are: the manually defined feature-code map; the call number threshold; the function name similarity threshold; the new extended feature-code map.
	- Or, you can just run `python auto_generate_extended_feature_code_maps.py` to generate all the extended feature-code maps, the output files would be put under `extended_feature_code_maps`.

### 3. Profiling
#### Base (blank website)
1. `cd slimium/src/profile`
2. Edit `baseline_profiling.py` to modify the variables according to the comments.
3. `python baseline_profiling.py ~/slimium/out/baseline.log`
4. Note that the executed functions' IDs are dumped into `~/slimium/out/baseline.log`.

#### Top websites
1. `cd slimium/src/profile`
2. Edit `evolve_profiling.py` to modify the variables according to the comments.
3. `python evolve_profiling.py ~/slimium/out/profile_out`
Note the profiling results about the executed functions are under the `profile_out`, each file contains the function IDs for executed functions.

### 4. Rewriting
#### Get nondeterministic functions
1. `cd slimium/src/rewrite`
2. `python simple_count_nondeterministic_code.py -l ~/slimium/out/profile_out/ -o ~/slimium/out/nondeterministic_funcs_manual_map_1000_1.txt -n 1000 -a 1`

#### Collect the last profiling log of each website
1. `cd slimium/src/rewrite`
2. `python collect_logs.py ~/slimium/out/profile_out/ ~/slimium/out/last_logs/`. The last log of each website is under `last_logs`.

#### Get functions to be removed for each website
1. `cd slimium/src/rewrite`
2. Edit `./get_removable_functions.sh` to change the variables.
3. `./get_removable_functions.sh ~/slimium/out/last_logs/ ~/slimium/src/feature_code_mapping/manual_feature_code_map.json ~/slimium/out/removeable_functions 0.5`. Note that `get_removable_functions.sh`: (1) the log directory. (2) the feature code mapping file. (3) the output directory. (4) the code coverage threshold (i.e., if the code coverage of certain feature exceeds the threshold, the feature should be considered removable).
4. `get_removable_functions.sh` would also generate two files under the output directory: `feature_func_num_code_size.txt` and `feature_functions.json`. The first one contains function number and code size of each feature. The second one contains the function ids of each feature.

#### Rewrite chrome
1. `cd slimium/src/rewrite`
2. `python rewrite.py -c ~/chromium/src/out/Marking/chrome -i ~/slimium/out/removeable_functions/youtube.com.log -o ./ -m ~/slimium/out/removeable_functions/feature_functions.json`
3. Note that `rewrite.py` takes in four arguments: (1) the orginal chrome binary. (2) the file contains removable functions ids for a website. (3) the output directory. (4) the file contains the function ids of each feature. After running `rewrite.py`, a debloated binary `website_chrome` would be generated under the output directory.
