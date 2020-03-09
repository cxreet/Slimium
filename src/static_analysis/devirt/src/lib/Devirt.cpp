#include "Devirt.h"

static cl::opt<std::string> BitcodeFileDir(cl::Positional, cl::desc("[The directory that contains bitcode files.]"), cl::Required);
static cl::opt<std::string> OutDir(cl::Positional, cl::desc("[Output dir.]"), cl::Required);

static unsigned indirect_call_num = 0;
static unsigned virtual_call_num = 0;
static unsigned missed_type_check = 0;

typedef vector<Module*> ModuleList;
typedef vector<MDNode*> MDNodeList;
typedef vector<TypeMDNode*> TypeMDNodeList;
typedef vector<GlobalVariable*> GVList;
typedef unordered_map<GlobalVariable*, MDNodeList> GVMDNodeListMap;
typedef unordered_map<MDNode*, GVList> MDNodeGVListMap;
typedef unordered_map<string, MDNodeList> Name2MDNodeList;
typedef unordered_map<const Metadata*, MDNodeList> Metadata2MDNodeList;
typedef unordered_map<MDNode*, TypeMDNode*> MD2TyMDMap;
typedef unordered_map<string, GVList> DemangledName2GVListMap;
typedef unordered_map<GlobalVariable*, FlatVTable*> GV2FlatVTMap;
typedef unordered_map<string, uint64_t> IndexMap;
typedef unordered_map<uint64_t, set<uint64_t>> CallGraphMap;

// all modules
ModuleList AllModules;
// key is global variable, value is a list of the metadata related to this GV
GVMDNodeListMap GVWithMDs;
// key is a metadata, value is a list of GVs that has this metadata
MDNodeGVListMap MD2GVs;
// key is a mangled type name, value is a list of metadata with this type name, this is usually for 
// type checks across modules
Name2MDNodeList Name2MDNodes;
// key is a metadata, value is a list of metadata nodes that has this metadata
Metadata2MDNodeList Metadata2MDNodes;
// key is a MDNode, value is the detail info for the node
MD2TyMDMap MD2TyMD;
// key is the demangled class name, value is the GV
DemangledName2GVListMap DemangledName2GVs;
// key is GV, value is the flatten vtable
GV2FlatVTMap GV2FlatVT;
// key is module name, value is index
IndexMap FileIndexes;
uint64_t NextFileIndex = 0;
// key is function name, value is index
IndexMap FunctionIndexes;
uint64_t NextFunctionIndex = 0;
// call graph
CallGraphMap G;

bool find_vtable(string type_str, Value* called_value, vector<Value*> &callees)
{
	std::size_t pos = 0;
	pos = type_str.find("class.");
	if (pos == std::string::npos)
	{
		pos = type_str.find("struct.");
		if (pos == std::string::npos)
			return false;
		else
			pos += 7;
	} else
	{
		pos += 6;
	}
	
	std::size_t end_pos = pos;
	for (; end_pos < type_str.length(); end_pos++)
	{
		if (type_str[end_pos] == '\"')
			break;
	}

	if (end_pos == type_str.length())
		return false;

	string real_type_str = type_str.substr(pos, end_pos-pos);
	if (DemangledName2GVs.find(real_type_str) == DemangledName2GVs.end())
	{
		return false;
	}

	string func_type_str;
	raw_string_ostream rso(func_type_str);
	called_value->getType()->print(rso);
	//errs() << rso.str() << '\n';
	string s1 = rso.str();
	
	for (GlobalVariable* gv : DemangledName2GVs[real_type_str])
	{
		if (GV2FlatVT.find(gv) == GV2FlatVT.end())
			continue;

		FlatVTable *flat_vtable = GV2FlatVT[gv];
		for (Value* v : flat_vtable->function_ptrs)
		{
			if (!v)
				continue;
			string func_type_str2;
			raw_string_ostream rso2(func_type_str2);
			v->getType()->print(rso2);
			//errs() << rso2.str() << '\n';
			if (s1 == rso2.str()) {
				callees.push_back(v);
			}
		}
	}

	return true;

}

void xtract_module_metainfo(Module *module)
{
	for (Module::global_iterator it = module->global_begin(), ie = module->global_end(); it != ie; ++it)
	{
		GlobalVariable &gv = *it;

		// demangle the name
		const char *mangled_name = (gv.getName()).data();
		int status = 0;
		bool is_vtable = false;
		string demangled_name = "";
		try {
			char *realname = abi::__cxa_demangle(mangled_name, 0, 0, &status);
			demangled_name = string(realname);
			is_vtable = demangled_name.find("vtable for") == 0 || demangled_name.find("construction vtable for") == 0;
			free(realname);
		} catch(...)
		{
			//errs() << "Exception happens on demangling: " << status << " " << mangled_name << '\n';
		}
		if (status == 0 && is_vtable)
		{
			std::size_t pos = demangled_name.find("vtable for");
			string class_name = demangled_name.substr(pos + 11);
			if (DemangledName2GVs.find(class_name) == DemangledName2GVs.end())
			{
				DemangledName2GVs[class_name] = GVList();
			}
			DemangledName2GVs[class_name].push_back(&gv);
			//errs() << "vtable " << class_name << '\n';

			// flat the vtable
			if (GV2FlatVT.find(&gv) == GV2FlatVT.end())
			{
				FlatVTable *flat_vtable = new FlatVTable(&gv);
				if (flat_vtable->has_initializer)
				{
					GV2FlatVT[&gv] = flat_vtable;
				}
			}
		}

		if (gv.hasMetadata())
		{
			SmallVector<std::pair<unsigned, MDNode *>, 1> mds;
			gv.getAllMetadata(mds);
			
			for(auto p : mds)
			{
				if (p.first != LLVMContext::MD_type)
					continue;
				
				MDNode *md = p.second;
				//errs() << *md << '\n';
				// construct the GVWithMDs and MD2GVs map
				if (GVWithMDs.find(&gv) == GVWithMDs.end())
				{
					GVWithMDs[&gv] = MDNodeList();
				}
				GVWithMDs[&gv].push_back(md);
				if (MD2GVs.find(md) == MD2GVs.end())
				{
					MD2GVs[md] = GVList();
				}
				MD2GVs[md].push_back(&gv);
				
				// construct MD2TyMD
				TypeMDNode *typeMDNode = new TypeMDNode(md);
				MD2TyMD[md] = typeMDNode;
				// construct Name2MDNodes and Metadata2MDNodes
				const Metadata *second_metadata = typeMDNode->second_metadata;
				string name = typeMDNode->name;
				if (second_metadata)
				{
					if (Metadata2MDNodes.find(second_metadata) == Metadata2MDNodes.end())
					{
						Metadata2MDNodes[second_metadata] = MDNodeList();
					}
					Metadata2MDNodes[second_metadata].push_back(md);
				} else {
					if (Name2MDNodes.find(name) == Name2MDNodes.end())
					{
						Name2MDNodes[name] = MDNodeList();
					}
					Name2MDNodes[name].push_back(md);
				}
			}
		}
	}
}

bool devirt_without_type_check(Value *called_value, vector<Value*> &callees)
{
	LoadInst *load_inst = dyn_cast<LoadInst>(called_value);
	if (!load_inst)
		return false;

	const Value *pointer_op = load_inst->getPointerOperand();
	const GetElementPtrInst *gep_inst = dyn_cast<GetElementPtrInst>(pointer_op);
	if (!gep_inst)
		return false;

	const LoadInst *class_load_inst = dyn_cast<LoadInst>(gep_inst->getPointerOperand());
	if (!class_load_inst)
		return false;

	const Value *class_op = class_load_inst->getPointerOperand();
	const BitCastInst *bitcast_inst = dyn_cast<BitCastInst>(class_op);
	if (!bitcast_inst)
		return false;

	int64_t gep_offset = 0;
	Value *second_op = gep_inst->getOperand(1);
	ConstantInt *cnst_int = dyn_cast<ConstantInt>(second_op);
	if (!cnst_int)
	{
		gep_offset = -1;
		errs() << "called value " << *called_value << '\n';
		return false;
	} else
	{
		gep_offset = cnst_int->getSExtValue();
	}

	Type *ty = bitcast_inst->getSrcTy();
	string ty_str;
	raw_string_ostream rso(ty_str);
	ty->print(rso);
	string class_name = rso.str();
	size_t pos = class_name.find("class.");
	if (pos == string::npos)
		return false;

	pos = pos + 6;
	unsigned l = class_name.length();
	unsigned len = 0;
	if (class_name[l-2] == '\"')
	{
		len = (l-3) - pos + 1;
	} else
	{
		len = (l-2) - pos + 1;
	}

	string real_class_name = class_name.substr(pos, len);
	if (DemangledName2GVs.find(real_class_name) == DemangledName2GVs.end())
	{
		//errs() << real_class_name.c_str() << '\n';
		return false;
	}
	
	bool found = false;	
	GVList gvs = DemangledName2GVs[real_class_name];
	for (GlobalVariable *gv : gvs)
  {
		if (GV2FlatVT.find(gv) != GV2FlatVT.end())
		{
			FlatVTable *flat_vtable = GV2FlatVT[gv];
			if (gep_offset >= 0 && gep_offset <= flat_vtable->function_num - 1)
			{
				if (flat_vtable->function_ptrs[gep_offset] != nullptr)
				{
					callees.push_back(flat_vtable->function_ptrs[gep_offset]);
					found = true;
				}
			} else if (gep_offset == -1)
			{
				errs() << "called value: " << *called_value << '\n';
			}
		}
	}

	return found;
}

bool devirt_with_type_check(Value *called_value, unordered_map<Value*, Metadata*> type_tests, vector<Value*> &callees)
{
	LoadInst *load_inst = dyn_cast<LoadInst>(called_value);
	if (!load_inst)
		return false;

	int64_t gep_offset = 0;	
	Metadata *metadata = nullptr;
	Value *pointer_op = load_inst->getPointerOperand();
	if (type_tests.find(pointer_op) != type_tests.end())
	{
		metadata = type_tests[pointer_op];
	}

	if (!metadata)
	{
		GetElementPtrInst *gep_inst = dyn_cast<GetElementPtrInst>(pointer_op);
		if (!gep_inst)
			return false;
		Value *first_op = gep_inst->getOperand(0);
		if (type_tests.find(first_op) != type_tests.end())
		{
			metadata = type_tests[first_op];
		}

		if (!metadata)
			return false;

		Value *second_op = gep_inst->getOperand(1);
		ConstantInt *cnst_int = dyn_cast<ConstantInt>(second_op);
		if (!cnst_int)
		{
			errs() << "called value " << *called_value << '\n';
			// cannot figure out the vtable index
			return false;
		}
		//assert(cnst_int);
		gep_offset = cnst_int->getSExtValue();
	}

	// get md nodes related to the type check's second argument (i.e., metadata)
	MDString *md_str = dyn_cast<MDString>(metadata);
	if (!md_str)
	{
		assert (Metadata2MDNodes.find(metadata) != Metadata2MDNodes.end());
		MDNodeList md_nodes = Metadata2MDNodes[metadata];
		// explore the vtables to get the target functions
		for (MDNode *md_node : md_nodes)
		{
			TypeMDNode *ty_md_node = MD2TyMD[md_node];
			assert(MD2GVs.find(md_node) != MD2GVs.end());
			GVList gv_list = MD2GVs[md_node];
			uint64_t idx = ty_md_node->offset / 8 + gep_offset;
			for (GlobalVariable *gv : gv_list)
			{
				FlatVTable *flat_vtable = GV2FlatVT[gv];
				if (idx >= flat_vtable->function_num)
					continue;

				Value *callee = flat_vtable->function_ptrs[idx];
				if (!callee)
					continue;
				callees.push_back(callee);
			}
		}
	} else {
		string type_name = (md_str->getString()).str();
		if (Name2MDNodes.find(type_name) == Name2MDNodes.end())
		{
			missed_type_check += 1;
			return false;
		}
		MDNodeList md_nodes = Name2MDNodes[type_name];
		// explore the vtables to get the target functions
		for (MDNode *md_node : md_nodes)
		{
			TypeMDNode *ty_md_node = MD2TyMD[md_node];
			assert(MD2GVs.find(md_node) != MD2GVs.end());
			GVList gv_list = MD2GVs[md_node];
			uint64_t idx = ty_md_node->offset / 8 + gep_offset;
			for (GlobalVariable *gv : gv_list)
			{
				FlatVTable *flat_vtable = GV2FlatVT[gv];
				if (idx >= flat_vtable->function_num)
					continue;
				Value *callee = flat_vtable->function_ptrs[idx];
				if (!callee)
					continue;
				callees.push_back(callee);
			}
		}
	}

	return true;
}

uint64_t get_function_index(string name)
{
	assert (name.length() > 0);
	uint64_t ret_index;
	if (FunctionIndexes.find(name) == FunctionIndexes.end())
	{
		FunctionIndexes[name] = NextFunctionIndex;
		ret_index = NextFunctionIndex;
		NextFunctionIndex += 1;
	} else {
		ret_index = FunctionIndexes[name];
	}
	return ret_index;
}

void devirt(Module *module)
{
	for (Module::iterator function_it = module->begin();
			function_it != module->end(); ++function_it)
	{
		Function *function = &(*function_it);

		if (function->isDeclaration())
			continue;

		if (function->isIntrinsic())
			continue;
		
		// get caller name and its index
		string caller_name = string((function->getName()).data());
		uint64_t cur_caller_index = get_function_index(caller_name);

		// the callee indexes set
		set<uint64_t> &callee_index_set = G[cur_caller_index];
		
		// iterate to collect all type tests
		unordered_map<Value*, Metadata*> type_tests;
		for (inst_iterator inst_it = inst_begin(function),
				inst_it_end = inst_end(function); inst_it != inst_it_end; ++inst_it)
		{
			Instruction *inst = &(*inst_it);
			CallInst *call_inst = dyn_cast<CallInst>(inst);
			InvokeInst *invoke_inst = dyn_cast<InvokeInst>(inst);
			CallSite *callsite = nullptr;
			Function *callee = nullptr;

			if (call_inst)
			{
				callee = call_inst->getCalledFunction();
				callsite = new CallSite(call_inst);
			}
			if (invoke_inst)
			{
				callee = invoke_inst->getCalledFunction();
				callsite = new CallSite(invoke_inst);
			}

			if (!callee)
				continue;
			
			string callee_name = (callee->getName()).str();
			if (strcmp(callee_name.c_str(), "llvm.type.test") == 0)
			{
				// first argument is vtable
				Value *first_op = callsite->getArgument(0);
				BitCastInst *bitcast_inst = dyn_cast<BitCastInst>(first_op);
				assert(bitcast_inst);
				
				// second argument is the typecheck metadata
				Value *second_op = callsite->getArgument(1);
				MetadataAsValue *meta_as_val = dyn_cast<MetadataAsValue>(second_op);
				assert(meta_as_val);
				Metadata *meta_data = meta_as_val->getMetadata();
				type_tests[bitcast_inst->getOperand(0)] = meta_data;
			}
		}

		// build call graphs
		for (inst_iterator inst_it = inst_begin(function),
				inst_it_end = inst_end(function); inst_it != inst_it_end; ++inst_it)
		{
			CallSite *callsite = nullptr;
			Instruction *inst = &(*inst_it);
			CallInst *call_inst = dyn_cast<CallInst>(inst);
			InvokeInst *invoke_inst = dyn_cast<InvokeInst>(inst);
			Function *callee = nullptr;
			Value *called_value = nullptr;

			if (!call_inst && !invoke_inst)
				continue;
			
			if (call_inst)
			{
				callsite = new CallSite(call_inst);
				callee = call_inst->getCalledFunction();
				called_value =  call_inst->getCalledValue();
			}
			if (invoke_inst)
			{
				callsite = new CallSite(invoke_inst);
				callee = invoke_inst->getCalledFunction();
				called_value = invoke_inst->getCalledValue();
			}

			if (callee) 
			{
				if (!callee->isIntrinsic())
				{
					string callee_name = string((callee->getName()).data());
					uint64_t callee_index = get_function_index(callee_name);					
					callee_index_set.insert(callee_index);
				}
				continue;
			}
			
			// the called value is bitcast operator or global alias
			BitCastOperator *bitcast_op = dyn_cast<BitCastOperator>(called_value);
			if (bitcast_op)
			{
				Value *operand = bitcast_op->getOperand(0);
				Type *ty = operand->getType();
				if (ty->isPointerTy() && ty->getPointerElementType()->isFunctionTy())
				{
					string callee_name = string((operand->getName()).data());
					if (callee_name.length() > 0)
					{
						uint64_t callee_index = get_function_index(callee_name);
						callee_index_set.insert(callee_index);
						continue;
					}
				}
			}
			GlobalAlias *global_alias = dyn_cast<GlobalAlias>(called_value);
			if (global_alias)
			{
				const Constant *cnst = global_alias->getAliasee();
				Type *ty = cnst->getType();
				if (ty->isPointerTy() && ty->getPointerElementType()->isFunctionTy())
				{
					string callee_name = string((cnst->getName()).data());
					if (callee_name.length() == 0)
					{
						//errs() << *inst << '\n';
						//errs() << *cnst << '\n';
						//errs() << cnst->getName() << '\n';
						//errs() << cnst->getName().data() << '\n';
						const BitCastOperator *tmp_bco = dyn_cast<BitCastOperator>(cnst);
						assert (tmp_bco);
						Value *operand = tmp_bco->getOperand(0);
						callee_name = string((operand->getName()).data());
						if (callee_name.length() > 0)
						{
							uint64_t callee_index = get_function_index(callee_name);
							callee_index_set.insert(callee_index);
							continue;
						}

					} else {
						uint64_t callee_index = get_function_index(callee_name);
						callee_index_set.insert(callee_index);
						continue;
					}
				}
			}
			InlineAsm *inline_asm = dyn_cast<InlineAsm>(called_value);
			if (inline_asm)
			{
				continue;
			}

			// devirt indirect calls
			vector<Value*> callees;
			bool devirted = devirt_with_type_check(called_value, type_tests, callees);
			if (!devirted)
			{
				devirted = devirt_without_type_check(called_value, callees);
			}
			if (devirted)
			{
				virtual_call_num += 1;

				for (Value *v : callees)
				{
					string callee_name = string((v->getName()).data());
					uint64_t callee_index = get_function_index(callee_name);
					callee_index_set.insert(callee_index);
				}
			} else {
				if (LoadInst *load_inst = dyn_cast<LoadInst>(called_value))
				{
					if (GetElementPtrInst *gep_inst = dyn_cast<GetElementPtrInst>(load_inst->getPointerOperand()))
					{
						string type_str;
						raw_string_ostream rso(type_str);
						gep_inst->getOperand(0)->getType()->print(rso);
						if (find_vtable(rso.str(), called_value, callees))
						{
							if (callees.size() > 0)
							{
								virtual_call_num += 1;
							}
							for (Value *v : callees)
							{
								string callee_name = string((v->getName()).data());
								uint64_t callee_index = get_function_index(callee_name);
								callee_index_set.insert(callee_index);
							}
						}
					}
				}
			}

			indirect_call_num += 1;
		}
	}

}

int main(int argc, char** argv) 
{
	cl::ParseCommandLineOptions(argc, argv, "Parsing arguments\n");

	struct dirent *entry = nullptr;
	DIR *dp = nullptr;
	
	dp = opendir(BitcodeFileDir.data());
	if (dp == nullptr)
		assert(false);
	
	while ((entry = readdir(dp)))
	{
		if ((strncmp(entry->d_name, ".", 1) == 0 ||
					(strncmp(entry->d_name, "..", 2) == 0)))
			continue;

		string file_name(entry->d_name);

		LLVMContext *context = new LLVMContext();
		SMDiagnostic Err;

		std::unique_ptr<Module> m = parseIRFile(string(BitcodeFileDir.data()) + file_name, Err, *context);
		Module *module = m.release();
		if (module == NULL)
		{
			errs() << "loading " << string(BitcodeFileDir.data()) + file_name << " failed\n";
			errs() << Err.getMessage() << '\n';
			assert(false);
		}

		//errs() << "analyzing " << file_name << '\n';
		AllModules.push_back(module);
	}
	
	// collect all metadata first
	for (Module *module : AllModules)
	{
		errs() << "Collecting metainfo: " << module->getName() << '\n';
		xtract_module_metainfo(module);
	}
	
	for (Module *module : AllModules)
	{
		errs() << "Devirtualizing: " << module->getName() << '\n';
		devirt(module);
	}	
	errs() << "There are " << indirect_call_num << " indirect calls and " << virtual_call_num << " can be devirtualized!\n";
	errs() << "There are " << missed_type_check << " missing type checks...\n";

	// dump indirect calls	
	string out_dir = string(OutDir.data());
	string out_call_graph = out_dir + "/callgraph.txt";
	string out_index = out_dir + "/index.txt";
	
	ofstream index_file (out_index.c_str());
	for (auto it : FunctionIndexes)
	{
		string function_name = it.first;
		uint64_t idx = it.second;
		index_file << idx << " " << function_name.c_str() << '\n';
	}
	index_file.close();

	ofstream call_graph_file (out_call_graph.c_str());
	for (auto it : G)
	{
		uint64_t caller_idx = it.first;
		set<uint64_t> callee_idxes = it.second;
		call_graph_file << caller_idx;
		for (uint64_t callee_idx : callee_idxes)
		{
			call_graph_file << " " << callee_idx;
		}
		call_graph_file << '\n';
	}
	call_graph_file.close();
	return 0;
}
