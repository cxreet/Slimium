#include "GroupFunctions.h"
using namespace std;

static cl::opt<std::string> BitcodeFileDir(cl::Positional, cl::desc("[The directory that contains bitcode files.]"), cl::Required);
static cl::opt<std::string> IndexFile(cl::Positional, cl::desc("[The file contains indexes.]"), cl::Required);
static cl::opt<std::string> OutDir(cl::Positional, cl::desc("[Output dir.]"), cl::Required);

typedef unordered_map<string, set<int>> File2IndexesMap;
typedef unordered_map<string, int> Name2IndexMap;
typedef unordered_map<int, set<string>> Index2FilesMap;
typedef unordered_map<int, string> Index2NameMap;

Name2IndexMap Name2Index;
Index2NameMap Index2Name;
File2IndexesMap File2Indexes;
Index2FilesMap Index2Files;

//===========string split begins===========
template<typename Out>
void split(const std::string &s, char delim, Out result) {
	std::stringstream ss(s);
	std::string item;
	while (std::getline(ss, item, delim)) {
		*(result++) = item;
	}
}

std::vector<std::string> split(const std::string &s, char delim) {
	std::vector<std::string> elems;
	split(s, delim, std::back_inserter(elems));
	return elems;
}
//============string split ends==============

void read_indexes(const char* fname)
{
	std::ifstream infile(fname);
	if (infile.is_open())
	{
		string line;
		while (getline(infile, line))
		{
			vector<string> tokens = split(line, ' ');
			int idx = 0;
			string::size_type sz;
			if (tokens[0][0] == '+')
			{
				idx = stoi(tokens[0].substr(1), &sz);
			} else 
			{
				idx = stoi(tokens[0], &sz);
			}
			string func_name = tokens[1];
			if (func_name[func_name.length()-1] == '\n')
				func_name[func_name.length()-1] = '\0';

			Name2Index[func_name] = idx;
			Index2Name[idx] = func_name;
		}
		infile.close();
	}
}

int main(int argc, char** argv) 
{
	cl::ParseCommandLineOptions(argc, argv, "Parsing arguments\n");

	read_indexes(IndexFile.data());

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

		replace(file_name, "$", ".");
		replace(file_name, "@", "/");
		
		errs() << "analyzing " << file_name << '\n';

		if (File2Indexes.find(file_name) == File2Indexes.end())
			File2Indexes[file_name] = set<int>();

		for (Module::iterator function_it = module->begin();
				function_it != module->end(); ++function_it)
		{
			Function *function = &(*function_it);
			if (function->isDeclaration() || function->isIntrinsic())
				continue;
			string func_name = function->getName().str();
			int idx = Name2Index[func_name];
			File2Indexes[file_name].insert(idx);
			
			/*	
			if (function->hasFnAttribute(Attribute::InlineHint) ||
					function->hasFnAttribute(Attribute::AlwaysInline))
				continue;
			*/
			if (Index2Files.find(idx) == Index2Files.end())
				Index2Files[idx] = set<string>();
			Index2Files[idx].insert(file_name);
		}
	}


	// dump indirect calls	
	string out_dir = string(OutDir.data());
	string file_index_name = out_dir + "/file_functions.txt";
	
	ofstream file_index_out (file_index_name.c_str());
	for (auto it : File2Indexes)
	{
		string file_name = it.first;
		set<int> indexes = it.second;
		file_index_out << file_name << ' ';
		for (int idx : indexes)
			file_index_out << idx << ' ';
		file_index_out << '\n';
	}
	file_index_out.close();
	
	/*	
	string duplicate_func_out_name = out_dir + "/duplicates.txt";
	ofstream file_duplicate_out (duplicate_func_out_name.c_str());
	for (auto it : Index2Files) {
		int idx = it.first;
		set<string> files = it.second;
		if (files.size() > 1000) {
			file_duplicate_out << idx << ' ' << Index2Name[idx] << '\n';
			int i = 0;
			for (string file : files) {
				i += 1;
				file_duplicate_out << file << '\n';
				if (i == 10)
					break;
			}
		}
	}
	file_duplicate_out.close();
	*/

	return 0;
}
