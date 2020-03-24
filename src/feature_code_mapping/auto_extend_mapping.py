import os
import cPickle as pickle
import logging, json
from operator import itemgetter
from bz2 import BZ2File
from optparse import OptionParser
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
        self.func_boundary_objdmp = feeds_in[3]    # 'disassembled_functions.txt'
        
        # data structures related to file/dir deps
        self.all_source_files = set()
        self.bin_files = set()
        self.third_party_libs = set()
        self.file_deps = dict()
        self.dir_deps = dict()

        # complted features
        self.completed_features = set()
        
        self.ffmap = dict()

        self.feature_files_m = dict()

        # exclude the following names
        self.exclude_names = ["../../chrome/browser/ui/", "../../ui/"]
    
        for fi in feeds_in:
            if not os.path.isfile(fi):
                logging.error("[-] %s has not been found...!" % fi)

    def init(self):
        # [Step I] Generate all IR functions from the global mapping info, the ids are unique
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

            # file found in binary
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

    def extend_feature_code_mapping(self, call_threshold, similarity_threshold):
        # relate file to features
        file_2_features = dict()
        extended_feature_file_m = dict()

        for feature in self.feature_files_m:
            logging.info("checking " + feature)
            extended_feature_file_m[feature] = dict()

            file_names = self.feature_files_m[feature]
            # files related to feature
            files = set()
            for f_name in file_names:
                if f_name in self.file_deps:
                    files.add(self.file_deps[f_name])
            
            # find files upwards/downwards
            upwards_files = set()
            downwards_files = set()
            for f in files:
                for up_f in f.ref_from:
                    if up_f in files:
                        continue

                    # exclude sensitive files
                    to_exclude = False
                    for ex_name in self.exclude_names:
                        if up_f.path.startswith(ex_name):
                            to_exclude = True
                            break
                    if to_exclude:
                        continue

                    # mark which features are related to this file
                    if up_f.path not in file_2_features:
                        file_2_features[up_f.path] = set()
                    file_2_features[up_f.path].add(feature)

                    # calculate the weight
                    w = 0
                    in_num = 0
                    total_similarity = 0.0
                    for to_f in up_f.ref_to:
                        if to_f not in files:
                            continue
                        w += len(up_f.ref_to[to_f])
                        in_num += 1.0
                        total_similarity += up_f.ref_to_sim_m[to_f]
                    upwards_files.add((up_f.path, float(w)/float(up_f.out_weight), total_similarity/in_num))

                for down_f in f.ref_to:
                    if down_f in files:
                        continue

                    # exclude sensitive files
                    to_exclude = False
                    for ex_name in self.exclude_names:
                        if down_f.path.startswith(ex_name):
                            to_exclude = True
                            break
                    if to_exclude:
                        continue
                    
                    # mark which features are related to this file
                    if down_f.path not in file_2_features:
                        file_2_features[down_f.path] = set()
                    file_2_features[down_f.path].add(feature)

                    # calculate the weight
                    w = 0
                    in_num = 0
                    total_similarity = 0.0
                    for from_f in down_f.ref_from:
                        if from_f not in files:
                            continue
                        w += len(down_f.ref_from[from_f])
                        in_num += 1
                        total_similarity += down_f.ref_from_sim_m[from_f]
                    downwards_files.add((down_f.path, float(w)/float(down_f.in_weight), total_similarity/in_num))

            
            extended_feature_file_m[feature]["up_files"] = upwards_files
            extended_feature_file_m[feature]["down_files"] = downwards_files
        
        ret_m = dict()
        for feature in extended_feature_file_m:
            if feature in self.completed_features:
                continue

            feature_completed = True

            ret_m[feature] = dict()
            ret_m[feature]["up_files"] = list()
            ret_m[feature]["down_files"] = list()

            up_files = extended_feature_file_m[feature]["up_files"]
            down_files = extended_feature_file_m[feature]["down_files"]

            r_c = call_threshold
            r_s = similarity_threshold

            logging.info("Using relation vector:" + str(r_c) + " " + str(r_s) + "\n")
            
            #most_related_up_file = (None, 0, 0)
            for (f, w, s) in up_files:
                if len(file_2_features[f]) > 1:
                    continue

                if s > r_c or w > r_s:
                    feature_completed = False
                    ret_m[feature]["up_files"].append((f, w, s))
                
            #most_related_down_file = (None, 0, 0)
            for (f, w, s) in down_files:
                if len(file_2_features[f]) > 1:
                    continue
                if s > r_c or w > r_s:
                    feature_completed = False
                    ret_m[feature]["down_files"].append((f, w, s))
                
            if feature_completed:
                self.completed_features.add(feature)
                logging.info("Completed feature: " + feature)

        return ret_m
    

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

    parser = OptionParser()
    parser.add_option("-o", "--output", dest="out_file", help="The output file that contains extend feature code mapping.")
    parser.add_option("-m", "--mapping", dest="feature_code_mapping_json", help="The jason file that contains the mappings between blink features and code.")
    #parser.add_option("-n", "--new_mapping", dest="new_feature_code_mapping_json", help="The new jason file that contains the mappings between blink features and code.")
    parser.add_option("-u", "--unique_index", dest="unique_index_file", help="The unique index file.")
    parser.add_option("-i", "--index", dest="index_file", help="The index file.")
    parser.add_option("-c", "--callgraph", dest="callgraph_file", help="The callgraph file.")
    parser.add_option("-f", "--disassembled_functions", dest="disassembled_functions_file", help="The file that contains disassembled functions.")
    parser.add_option("-a", "--call_threshold", dest="call_threshold", help="The call number threshold.")
    parser.add_option("-b", "--similarity_threshold", dest="similarity_threshold", help="The function name similarity threshold.")
    
    (options, args) = parser.parse_args()
    out_file = options.out_file
    feature_code_mapping_json = options.feature_code_mapping_json
    #new_feature_code_mapping_json = options.new_feature_code_mapping_json
    unique_index_file = options.unique_index_file
    index_file = options.index_file
    callgraph_file = options.callgraph_file
    disassembled_functions_file = options.disassembled_functions_file
    call_threshold = float(options.call_threshold)
    similarity_threshold = float(options.similarity_threshold)
    
    # get the feature code mapping
    feature_source_map = dict()
    with open(feature_code_mapping_json, 'r') as in_f:
        feature_source_map = json.loads(in_f.read())

    # create the object
    FFMG = FeatureFunctionMappingGenerator(
        [unique_index_file, index_file, callgraph_file,
         disassembled_functions_file] # input
    )
    
    # initialize the object to prepare everything
    FFMG.init()
    FFMG.generate_file_deps()
    logging.info("Total files in binary: " + str(len(FFMG.bin_files)))
    
    # for each manual defined feature and third_party lib, find the related source code files
    logging.info("Mapping source code files with features.")
    FFMG.get_third_party_lib_and_web_feature_code(feature_source_map)
    total_mapped_files = set()
    for feature in FFMG.feature_files_m:
        for fname in FFMG.feature_files_m[feature]:
            total_mapped_files.add(fname)
    logging.info("Total files mapped to features: " + str(len(total_mapped_files)))

    # extend the feature code mapping
    finished = False
    i = 0
    while not finished:
        i += 1
        print i, "iteration..."
        finished = True
        extended_feature_code_mapping = FFMG.extend_feature_code_mapping(call_threshold, similarity_threshold)
        for feature in extended_feature_code_mapping:
            up_files = extended_feature_code_mapping[feature]["up_files"]
            down_files = extended_feature_code_mapping[feature]["down_files"]
            if len(up_files) > 0:
                for (fname, w, s) in up_files:
                    FFMG.feature_files_m[feature].add(fname)
                    print feature, "+up", fname
                finished = False
            if len(down_files) > 0:
                for (fname, s, s) in down_files:
                    FFMG.feature_files_m[feature].add(fname)
                    print feature, "+down", fname
                finished = False

    with open(out_file, 'w') as out_f:
        data = dict()
        for feature in FFMG.feature_files_m:
            data[feature] = list(FFMG.feature_files_m[feature])
        json.dump(data, out_f, indent=4, sort_keys=True)
