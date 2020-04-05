import os
import cPickle as pickle
import logging, json
from operator import itemgetter
from bz2 import BZ2File
from optparse import OptionParser
import subprocess

import unit

class FeatureFunctionMappingGenerator(object):
    """
    FuncID: (FuncName, FuncStart, FuncEnd, DirectoryNameFuncBelongsTo, FileNameFuncBelongsTo,
            XrefFrom, XrefTo, FeatureID, FeatureType, RelevantCVE_if_any,
            HasBeenExercised, IsDeterministic)
    """
    def __init__(self, feeds_in):
        # Feeds are a series of input/output files: feeds_in and feeds_out

        # input files
        self.feeds_in = feeds_in
        self.index = feeds_in[0]                   # 'unique_indexes.txt'
        self.callgraph_index = feeds_in[1]         # 'index.txt'
        self.callgraph = feeds_in[2]               # 'callgraph.txt'
        self.func_boundary_objdmp = feeds_in[3]    # 'function_boundaries.txt'
        self.profiling_base_file = feeds_in[4]
        
        # data structures related to file/dir deps
        self.all_source_files = set()
        self.bin_files = set()
        self.third_party_libs = set()
        self.file_deps = dict()
        self.dir_deps = dict()
        
        # map from each feature and related source code files
        self.feature_files_m = dict()
        # map from each feature and related functions
        self.feature_funcs_m = dict()
        # map from each feature to code size
        self.feature_code_size_m = dict()
        # map from each feature to function #
        self.feature_func_num_m = dict()
        # total code size for identified features
        self.total_size = 0

        self.code_cov_threshold = 0.0

        self.ffmap = dict()

        for fi in feeds_in:
            if not os.path.isfile(fi):
                logging.error("[-] %s has not been found...!" % fi)

        self.profiling_base = set()
        self.executed_func_freq_m = dict()
        self.log_num = 0
        with open(self.profiling_base_file, 'r') as in_f:
            for line in in_f.readlines():
                line = line.strip()
                func_id = int(line)
                self.profiling_base.add(func_id)

    def extend_profiling_base(self, logs_dir):
        for fname in os.listdir(logs_dir):
            self.log_num += 1
            fpath = os.path.join(logs_dir, fname)
            with open(fpath, 'r') as in_f:
                for line in in_f.readlines():
                    line = line.strip()
                    func_id = int(line, 10)
                    if func_id not in self.executed_func_freq_m:
                        self.executed_func_freq_m[func_id] = 0
                    self.executed_func_freq_m[func_id] += 1
        
        added_base_funcs = 0
        for func_id in self.executed_func_freq_m:
            # update the exe_freq of functions
            BF = self.ffmap[func_id]
            BF.exe_freq = self.executed_func_freq_m[func_id]

            # if some functions are executed by all websites, add them to the profiling base
            if self.executed_func_freq_m[func_id] == self.log_num and (func_id not in self.profiling_base):
                added_base_funcs += 1
                self.profiling_base.add(func_id)

        logging.info("Added " + str(added_base_funcs) + " functions to baseline, " + str(len(self.profiling_base)) + " in total")

    def init(self):
        # [Step I] Generate all IR functions from the global mapping info
        logging.info("Reading %s..." % self.index)
        self._read_ir_functions()

        # [Step II] Update function boundaries in case of (address-taken) binary functions
        logging.info("Reading %s..." % self.func_boundary_objdmp)
        self._update_function_boundaries()

        # [Step III] Update callgraph information
        logging.info("Reading %s..." % self.callgraph_index)
        self._callgraph_mapping()

    def _read_ir_functions(self):
        with open(self.index, 'r') as f:
            for line in f.readlines():

                functions_per_file = line.split(" ")
                assert(len(functions_per_file) > 0)
                src_path = functions_per_file[0].strip()
                self.all_source_files.add(src_path)

                functions_per_file = functions_per_file[1:]
                for f_id, f_name in zip(functions_per_file[0::2], functions_per_file[1::2]):
                    BF = unit.BinaryFunction(0)
                    BF.fid = int(f_id)
                    BF.name = f_name.strip()
                    BF.src_dir = os.path.dirname(src_path)
                    BF.src_file = os.path.basename(src_path)

                    self.ffmap[BF.fid] = BF

            logging.info("[+] # of IR functions collected: %d" % len(self.ffmap))

    def _update_function_boundaries(self):
        f_names_seen = set()
        redundant_fn_cnt = 0
        with open(self.func_boundary_objdmp, 'r') as f:
            for line in f.readlines():
                try:
                    f_id, f_start, f_end, f_name = line.split(" ")
                    f_id = int(f_id)
                    f_start, f_end = int(f_start, 16), int(f_end, 16)
                    f_name = f_name.strip()

                    if f_end - f_start + 1 < 13:
                        print line
                        assert False
                    
                    BF = self.ffmap[f_id]
                    # A few binary function names (~250) are redundant - ingore them
                    if not BF.name in f_names_seen:
                        # Update all function boundries iff unseen
                        BF.start, BF.end = f_start, f_end
                        BF.in_binary = True
                        BF.type = 0x1
                        f_names_seen.add(f_name)
                    else:
                        redundant_fn_cnt += 1
                        BF.redundant_name = True
                        logging.debug("[-] Redundant binary function names found: %s" % BF.name)

                except:
                    logging.warning("[-] Error while processing the line %s" % line)
                    pass

            logging.info("[+] # of binary functions: %d" % (len(f_names_seen) + redundant_fn_cnt))
            logging.info("[+] # of redundant binary functions: %d" % redundant_fn_cnt)
        
    def _callgraph_mapping(self):
        # Build a lookup table by a function name
        bin_fn_info_lookup = dict()
        redundant_function_names = set()
        for f_id in self.ffmap:
            f_name = self.ffmap[f_id].name
            if f_name not in bin_fn_info_lookup:
                bin_fn_info_lookup[f_name] = self.ffmap[f_id]
            else:
                redundant_function_names.add(f_name)
                continue

        logging.info("[+] Redundant IR function names: %d" % len(redundant_function_names))

        # Collect all callgaph indexes
        # then we load corresponding functions only
        cg_indexes = {}  # (cg_index: BF)
        no_ir_function_cnt = 0
        with open(self.callgraph_index, 'r') as f:
            for line in f.readlines():
                cg_index, fn_name = line.split(" ")
                cg_index = int(cg_index)
                fn_name = fn_name.strip()
                try:
                    BF = bin_fn_info_lookup[fn_name]
                    BF.cid = cg_index
                    cg_indexes[cg_index] = BF
                except KeyError:
                    cg_indexes[cg_index] = None
                    no_ir_function_cnt += 1

        logging.info("[+] # of call graph functions not in an IR function set: %d" % no_ir_function_cnt)

        logging.info("[+] Reading %s" % self.callgraph)
        with open(self.callgraph, 'r') as f:
            for line in f.readlines():
                callgraph = line.split(' ')
                caller, callees = int(callgraph[0]), [int(x) for x in callgraph[1:]]
                BF_caller = cg_indexes[caller]

                for callee in callees:
                    BF_callee = cg_indexes[callee]
                    if BF_caller:
                        BF_caller.ref_to.append(BF_callee)
                    if BF_callee:
                        BF_callee.ref_from.append(BF_caller)


    def generate_file_deps(self):
        for f_id in sorted(self.ffmap.keys()):
            FM = self.ffmap[f_id]
            if not FM.in_binary:
                continue

            #ref_from_idxes = [x.fid for x in FM.ref_from if x]
            ref_to_idxes = [x.fid for x in FM.ref_to if x]
            caller_file_path = FM.path
            caller_dir_path = os.path.dirname(caller_file_path)
            self.bin_files.add(caller_file_path)

            if caller_file_path not in self.file_deps:
                self.file_deps[caller_file_path] = unit.SourceFile(caller_file_path)
            caller_source_file = self.file_deps[caller_file_path]
            if caller_dir_path not in self.dir_deps:
                self.dir_deps[caller_dir_path] = unit.SourceDir(caller_dir_path)
            caller_source_dir = self.dir_deps[caller_dir_path]

            for to_id in ref_to_idxes:
                if not self.ffmap[to_id].in_binary:
                    continue

                callee_file_path = self.ffmap[to_id].path
                self.bin_files.add(callee_file_path)
                if callee_file_path not in self.file_deps:
                    self.file_deps[callee_file_path] = unit.SourceFile(callee_file_path)
                callee_source_file = self.file_deps[callee_file_path]
                callee_dir_path = os.path.dirname(callee_file_path)
                if callee_dir_path not in self.dir_deps:
                    self.dir_deps[callee_dir_path] = unit.SourceDir(callee_dir_path)
                callee_source_dir = self.dir_deps[callee_dir_path]

                # f_id is the caller id, to_id is the callee_id
                if caller_source_file != callee_source_file:
                    caller_source_file.add_ref_to(callee_source_file, to_id)
                    callee_source_file.add_ref_from(caller_source_file, f_id)
                
                if caller_source_dir != callee_source_dir:
                    caller_source_dir.add_ref_to(callee_source_dir, to_id)
                    callee_source_dir.add_ref_from(caller_source_dir, f_id)

        # calculate source code files' in/out weights
        for f_name in self.file_deps:
            source_file = self.file_deps[f_name]
            in_weight = 0
            for f in source_file.ref_from:
                in_weight += len(source_file.ref_from[f])
            self.file_deps[f_name].in_weight = in_weight

            out_weight = 0
            for f in source_file.ref_to:
                out_weight += len(source_file.ref_to[f])
            self.file_deps[f_name].out_weight = out_weight

    def get_third_party_libs(self):
        if len(self.third_party_libs) > 0:
            return self.third_party_libs

        for f in self.file_deps:
            if not f.startswith("../../third_party/"):
                continue
            lib = f.split("/")[3]
            self.third_party_libs.add(lib)
        return self.third_party_libs
    
    def get_third_party_lib_and_web_feature_code(self, feature_code_mapping):
        for feature in feature_code_mapping:
            self.feature_files_m[feature] = set()
            for f in feature_code_mapping[feature]:
                assert f.startswith("../../") or f.startswith("gen")
                
                for file_path in self.file_deps:
                    if file_path.startswith(f):
                        self.feature_files_m[feature].add(file_path)
        return self.feature_files_m

    def compute_feature_functions_map(self, m):
        visited = set()
        for feature in m:
            self.feature_funcs_m[feature] = set()
            self.feature_code_size_m[feature] = 0
            self.feature_func_num_m[feature] = 0

            files = m[feature]

            for func_id in self.ffmap:
                bin_func = self.ffmap[func_id]
                if bin_func.path in files and bin_func.in_binary:
                    self.feature_funcs_m[feature].add(bin_func)
                    self.feature_code_size_m[feature] += bin_func.size - 13
                    self.feature_func_num_m[feature] += 1

                    if bin_func.size < 13:
                        print func_id, bin_func.name
                        assert False

                    if bin_func not in visited:
                        visited.add(bin_func)
                        self.total_size += bin_func.size - 13
        
        logging.info("Total code size of identified feature: " + str(float(self.total_size)/1000000.0) + " MB")
        with open("feature_func_num_code_size.txt", 'w') as o_f:
            for feature in sorted(m.keys()):
                o_f.write(feature+": " + str(self.feature_func_num_m[feature]) + " " + str(self.feature_code_size_m[feature]) + "\n")
        return
    
    # compute the features to be removed with executed functions
    def remove_features_for_executed_functions(self, executed_func_ids):
        # compute the code coverage for each feature
        logging.info("Compute code coverage for each feature")
        executed_feature_funcs = dict()
        for feature in self.feature_funcs_m:
            executed_feature_funcs[feature] = set()
            for func in self.feature_funcs_m[feature]:
                if func.fid in executed_func_ids:
                    executed_feature_funcs[feature].add(func)
                elif func.fid in self.profiling_base:
                    executed_feature_funcs[feature].add(func)
    
        # get the features to be removed
        features_to_remove = set()
        for feature in self.feature_funcs_m:
            if len(self.feature_funcs_m[feature]) == 0:
                continue
            total_size = self.feature_code_size_m[feature]

            executed_size = 0
            for func in executed_feature_funcs[feature]:
                executed_size += func.size - 13

            code_cov = float(executed_size)/float(total_size)
            if code_cov < self.code_cov_threshold:
                features_to_remove.add(feature)
        logging.info("To remove the following features:")
        s = " "
        for feature in features_to_remove:
            s += feature + ", "
        logging.info(s)
    
        # get the function ids to be removed
        funcs_to_remove = set()
        for feature in features_to_remove:
            for func in self.feature_funcs_m[feature]:
                if func not in executed_feature_funcs[feature]:
                    funcs_to_remove.add((func.fid, func.start, func.end))

        return (funcs_to_remove, executed_feature_funcs)
    
if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

    parser = OptionParser()
    parser.add_option("-l", "--log_dir", dest="log_dir", help="The dir that contains profiling logs.")
    parser.add_option("-o", "--output", dest="output_dir", help="The output dir that contains the function ids to be removed.")
    parser.add_option("-m", "--mapping", dest="feature_code_mapping_json", help="The jason file that contains the mappings between blink features and code.")
    parser.add_option("-u", "--unique_index", dest="unique_index_file", help="The unique index file.")
    parser.add_option("-i", "--index", dest="index_file", help="The index file.")
    parser.add_option("-c", "--callgraph", dest="callgraph_file", help="The callgraph file.")
    parser.add_option("-f", "--function_boundaries", dest="function_boundaries_file", help="The file that contains disassembled functions.")
    parser.add_option("-b", "--profiling_base", dest="profiling_base_file", help="The profiling base file.")
    parser.add_option("-n", "--nondeterministic_code", dest="nondeterministic_code_file", help="The file contains nondeterministic functions.")
    parser.add_option("-p", "--code_cov_threshold_v", dest="code_cov_threshold_v", help="The shreshold value for code cov.")
    
    # parse the input
    (options, args) = parser.parse_args()
    log_dir = options.log_dir
    out_dir = options.output_dir
    feature_code_mapping_json = options.feature_code_mapping_json
    unique_index_file = options.unique_index_file
    index_file = options.index_file
    callgraph_file = options.callgraph_file
    function_boundaries_file = options.function_boundaries_file
    profiling_base_file = options.profiling_base_file
    nondeterministic_code_file = options.nondeterministic_code_file

    # create outdir
    if not os.path.exists(out_dir):
        cmd = "mkdir -p " + out_dir
        print cmd
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        p.communicate()


    nondeterminisitc_functions = set()
    with open(nondeterministic_code_file, 'r') as in_f:
        for line in in_f.readlines():
            line = line.strip()
            nondeterminisitc_functions.add(int(line, 10))

    # manual defined feature and code mapping
    feature_source_map = dict()
    with open(feature_code_mapping_json, 'r') as in_f:
        feature_source_map = json.loads(in_f.read())
    
    # create the object
    FFMG = FeatureFunctionMappingGenerator(
        [unique_index_file, index_file, callgraph_file,
         function_boundaries_file, profiling_base_file], # input
    )
    FFMG.code_cov_threshold = float(options.code_cov_threshold_v)
    
    # initialize the object to prepare everything
    FFMG.init()
    FFMG.extend_profiling_base(log_dir)
    FFMG.generate_file_deps()
    logging.info("Total files in binary: " + str(len(FFMG.bin_files)))

    # for each manual defined feature and third_party lib, find the related source code files
    logging.info("Mapping source code files with features:" + str(len(feature_source_map)))
    m = FFMG.get_third_party_lib_and_web_feature_code(feature_source_map)
    logging.info("Found source code for " + str(len(m)) + " files")
    total_mapped_files = set()
    for feature in FFMG.feature_files_m:
        for fname in FFMG.feature_files_m[feature]:
            total_mapped_files.add(fname)
    logging.info("Total files mapped to features: " + str(len(total_mapped_files)))
    
    # relate bin funcs for each feature
    logging.info("Mapping functions with features.")
    FFMG.compute_feature_functions_map(m)

    with open("feature_functions.json", 'w') as out_f:
        data = dict()
        for feature in FFMG.feature_funcs_m:
            data[feature] = list()
            for bin_func in FFMG.feature_funcs_m[feature]:
                data[feature].append(bin_func.fid)
        json.dump(data, out_f, indent=4, sort_keys=True)

    
    total_removed_size = 0
    website_num = 0

    # read profiling logs
    for log in os.listdir(log_dir):
        logging.info("Reading profiling result: " + log)
        out_file = os.path.join(out_dir, log)
        
        # get executed functions
        executed_func_ids = set()
        log = os.path.join(log_dir, log)
        with open(log, 'r') as in_f:
            for line in in_f.readlines():
                line = line.strip().split()[0]
                func_id = int(line, 10)
                executed_func_ids.add(func_id)

        # add the nondeterminisitc_functions
        for func_id in nondeterminisitc_functions:
            executed_func_ids.add(func_id)

        (funcs_to_remove, executed_feature_funcs) = FFMG.remove_features_for_executed_functions(executed_func_ids)

        # dump the ids to remove
        with open(out_file, 'w') as out_f:
            website_num += 1
            removed_size = 0
            for (f_id, start, end) in funcs_to_remove:
                removed_size += end - start + 1 - 13
                out_f.write(str(f_id) + " " + hex(start) + " " + hex(end) + "\n")
            
            out_f.write("#Removed " + str(float(removed_size)/1000000.0) + " MB\n")
            total_removed_size += removed_size
    
    logging.info("Avg removed code: " + str(float(total_removed_size)/(1000000.0*website_num)) + " MB\n")
