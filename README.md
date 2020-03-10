

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
6. Edit `11vm/llvm/lib/Transforms/Scalar` (line 178 ~ 180) based on `shm_clear.ll`(line 19 ~ 21).

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
