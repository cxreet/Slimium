#ifndef __CODEDEP_PROJECT__
#define __CODEDEP_PROJECT__

#include "llvm/Pass.h"
#include "llvm/IR/Type.h"
#include "llvm/IR/Value.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/CallSite.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/Operator.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/DataLayout.h"
#include "llvm/IR/TypeFinder.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/DerivedTypes.h"
#include "llvm/IR/InstIterator.h"
#include "llvm/IR/Instructions.h"
#include "llvm/IR/PatternMatch.h"
#include "llvm/IR/GetElementPtrTypeIterator.h"
#include "llvm/Support/Format.h"
#include "llvm/Support/ErrorOr.h"
#include "llvm/Support/FileSystem.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/raw_ostream.h"
#include "llvm/Support/MemoryBuffer.h"
#include "llvm/ADT/DenseMap.h"
#include "llvm/ADT/Statistic.h"
#include "llvm/ADT/SmallVector.h"
#include "llvm/ADT/iterator_range.h"
#include "llvm/Analysis/ValueTracking.h"
#include "llvm/Bitcode/BitcodeReader.h"
#include "llvm/IRReader/IRReader.h"
#include "llvm/Support/SourceMgr.h"

#include <dirent.h>
#include <fstream>
#include <sstream>
#include <unordered_map>
#include <set>

using namespace llvm;
using namespace std;

typedef std::vector<Function*> FunctionList;
typedef std::vector<Module*> ModuleList;
typedef std::unordered_map<Module*, FunctionList> ModuleFunctionMap;
typedef std::vector<std::pair<string, string>> SymbolPairList;
typedef std::unordered_map<string, SymbolPairList > FeatureSymbolMap;
typedef std::vector<string> SymbolList;

#endif
