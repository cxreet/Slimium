
# Slimium

## Setup

###  Get Chromium source code
1. Install `dep_tools` following this [link](https://chromium.googlesource.com/chromium/src/+/master/docs/linux/build_instructions.md).
2. Get the code: 
	- `mkdir ~/chromium && cd ~/chromium`
	- `fetch --nohooks chromium`

### Get customized llvm source code
1. Download and build `11vm` from this [link](https://github.com/cxreet/11vm).
2. Modify `llvm/lib/Transforms/Scalar/DumpIR.cpp` line 81 to change the directory path that you want to store the LLVM bitcode.

### Compile Chromium
Go to Chromium source code `src`:
1. `./build/install-build-deps.sh`
2. `gclient runhooks`
3.  Patch `build/config/compiler/BUILD.gn`: line 43 ~ 49 and line 252 ~ 268.

#### Dump LLVM IR
1. `gn gen out/DumpIR`
2. `cp 
