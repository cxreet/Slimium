#!/usr/bin/python
from __future__ import division
import sys, os, operator
from optparse import OptionParser
from utils import *
import multiprocessing
from multiprocessing import Pool
import json

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
    parser.add_option("-n", "--number", dest="website_number", help="The number of websites.")
    parser.add_option("-a", "--nondeterministic_threshold", dest="nondeterministic_threshold", help="The threshold used for deciding whether a function is nondeterministic. It should be <= website_num.")

    (options, args) = parser.parse_args()
    log_dir = options.log_dir
    out_file = options.out_file
    website_number = int(options.website_number, 10)
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
    
    with open(out_file, 'w') as out_f:
        for f_id in nondeterministic_f_ids:
            if id_freq[f_id] >= nondeterministic_threshold:
                out_f.write(str(f_id)+"\n")

    return

if __name__ == "__main__":
    main()
