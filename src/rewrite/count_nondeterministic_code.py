#!/usr/bin/python
from __future__ import division
import sys, os, operator
from optparse import OptionParser
from utils import *
import multiprocessing
from multiprocessing import Pool
import json

WEBSITE_NUM = 1000

call_graph = None

index_2_file_name = {}
index_2_func_name = {}

file_name_freq = {}
function_id_freq = {}

def get_log_diffs(arg):
    (website, log_dir) = arg
    log_num = 0
    for fname in os.listdir(log_dir):
        log_num += 1
    
    logs = []
    for i in range(1, log_num+1):
        ids = set()
        with open(os.path.join(log_dir, website+"_"+str(i)+".log"), 'r') as in_f:
            for line in in_f.readlines():
                line = line.strip()
                ids.add(int(line, 10))
        logs.append(ids)

    diffs = []
    for i in range(0, len(logs) - 1):
        pre_ids = logs[i]
        succ_ids = logs[i+1]

        diff = succ_ids - pre_ids
        diffs.append(diff)

    return (website, diffs)

def main():
    parser = OptionParser()
    parser.add_option("-l", "--log_dir", dest="log_dir", help="The websites' profiling out directory.")
    parser.add_option("-o", "--out", dest="out_file", help="The output log file.")
    parser.add_option("-u", "--ui", dest="unique_index_file", help="The unique index file.")
    parser.add_option("-n", "--number", dest="website_number", help="The number of websites.")
    parser.add_option("-m", "--feature_code_mapping", dest="feature_code_mapping_file", help="The json file that contains the feature code mapping.")
    parser.add_option("-d", "--function_boundaries", dest="function_boundaries_file", help="The file that contains the disassembled functions.")
    parser.add_option("-a", "--nondeterministic_threshold", dest="nondeterministic_threshold", help="The threshold used for deciding whether a function is nondeterministic. It should be <= website_num.")

    (options, args) = parser.parse_args()
    log_dir = options.log_dir
    out_file = options.out_file
    unique_index_file = options.unique_index_file
    website_number = int(options.website_number, 10)
    feature_code_mapping_file = options.feature_code_mapping_file
    function_boundaries_file = options.function_boundaries_file
    nondeterministic_threshold = int(options.nondeterministic_threshold, 10)

    websites = []
    i = 0
    with open("top-1m.csv", 'r') as in_f:
        for line in in_f.readlines():
            line = line.strip()
            tokens = line.split(",")
            website = tokens[-1]
            websites.append(website)
            i += 1
            if i == website_number:
                break

    # read the unique indexes file
    (sorted_file_names, file_name_2_funcs) = read_unique_indexes_with_name(unique_index_file)
    global index_2_file_name
    for file_name in file_name_2_funcs:
        funcs = file_name_2_funcs[file_name]
        for (idx, func_name) in funcs:
            index_2_file_name[idx] = file_name

    # read the disassembled functions
    bin_file_2_funcs = dict()
    functions = read_disassembled_functions(function_boundaries_file)
    for f_id in functions:
        (f_start, f_end, f_name) = functions[f_id]
        assert f_end - f_start + 1 >= 13
        file_name = index_2_file_name[f_id]
        file_name = "../.."+file_name
        if file_name not in bin_file_2_funcs:
            bin_file_2_funcs[file_name] = set()
        bin_file_2_funcs[file_name].add((f_id, f_start, f_end))

    # read feature code mapping
    feature_files_m = None
    bin_feature_2_funcs = dict()
    with open(feature_code_mapping_file, 'r') as in_f:
        feature_files_m = json.loads(in_f.read())
    for feature in feature_files_m:
        bin_feature_2_funcs[feature] = set()
        file_names = feature_files_m[feature]
        for fname in file_names:
            # skip files not compiled into binary
            if fname not in bin_file_2_funcs:
                continue
            for (f_id, f_start, f_end) in bin_file_2_funcs[fname]:
                bin_feature_2_funcs[feature].add((f_id, f_start, f_end))


    # analyze each website
    args = []
    for website in os.listdir(log_dir):
        if website in websites:
            args.append((website, os.path.join(log_dir, website)))
    
    # get all the log diffs
    pool = Pool(processes=16)
    log_diffs = pool.map(get_log_diffs, args, chunksize=1)
    pool.terminate()


    id_freq = dict()
    nondeterministic_f_ids = set()
    for (website, diffs) in log_diffs:
        for diff in diffs:
            for f_id in diff:
                nondeterministic_f_ids.add(f_id)
                if f_id not in id_freq:
                    id_freq[f_id] = 1
                else:
                    id_freq[f_id] += 1
    
    code_portions = set()
    func_portions = set()
    for feature in sorted(bin_feature_2_funcs.keys()):
        code_size = 0
        nondeterministic_func_num = 0
        nondeterministic_code_size = 0

        for (f_id, f_start, f_end) in bin_feature_2_funcs[feature]:
            code_size += f_end - f_start - 13
            if f_id in nondeterministic_f_ids:
                nondeterministic_code_size += f_end - f_start - 13
                nondeterministic_func_num += 1

        print feature, ",", len(bin_feature_2_funcs[feature]), ",", nondeterministic_func_num, ",", code_size, ",", nondeterministic_code_size
        if code_size == 0.0:
            code_portions.add(0.0)
        else:
            code_portions.add(float(nondeterministic_code_size)/float(code_size))

        if len(bin_feature_2_funcs[feature]) == 0:
            func_portions.add(0)
        else:
            func_portions.add(float(nondeterministic_func_num)/float(len(bin_feature_2_funcs[feature])))
    
    total_portion = 0.0
    for p in code_portions:
        total_portion += p

    print "Avg code portion:", total_portion / float(len(bin_feature_2_funcs.keys()))

    total_portion = 0.0
    for p in func_portions:
        total_portion += p
    print "Avg func portion:", total_portion / float(len(bin_feature_2_funcs.keys()))


    with open(out_file, 'w') as out_f:
        for f_id in nondeterministic_f_ids:
            if id_freq[f_id] >= nondeterministic_threshold:
                out_f.write(str(f_id)+"\n")

    return

if __name__ == "__main__":
    main()
