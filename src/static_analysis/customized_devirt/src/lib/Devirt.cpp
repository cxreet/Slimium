#include "Devirt.h"

static cl::opt<std::string> BitcodeFileDir(cl::Positional, cl::desc("[The directory that contains bitcode files.]"), cl::Required);
static cl::opt<std::string> OutDir(cl::Positional, cl::desc("[Output dir.]"), cl::Required);


typedef unordered_map<string, uint64_t> IndexMap;

IndexMap FunctionIndexes;
uint64_t NextFunctionIndex = 0;

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

		}

		delete module;
		delete context;

	}
	
	// dump indirect calls	
	string out_dir = string(OutDir.data());
	string out_index = out_dir + "/index.txt";
	
	ofstream index_file (out_index.c_str());
	for (auto it : FunctionIndexes)
	{
		string function_name = it.first;
		uint64_t idx = it.second;
		index_file << idx << " " << function_name.c_str() << '\n';
	}
	index_file.close();

	return 0;
}
