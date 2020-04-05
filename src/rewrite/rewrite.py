#!/usr/bin/python
from __future__ import division
import os, sys, shutil
from optparse import OptionParser
import subprocess, time
import json

chrome = None

def rewrite(in_chrome, out_chrome, function_ranges):
    # copy the original binary and rewrite
    shutil.copyfile(in_chrome, out_chrome)
    
    # mark the useless functions to illegal instructions
    removed_size = 0
    with open(out_chrome, 'r+b') as in_f:
        for f_id in function_ranges:
            (start_addr, end_addr) = function_ranges[f_id]
            f_size = end_addr - start_addr + 1

            removed_size += f_size
            #print "kill ", f_id, hex(start_addr), hex(end_addr)
            in_f.seek(start_addr)
            chunk = b'\x6d' * f_size;
            in_f.write(chunk)

    print " removed: ", removed_size/1000000, "MB"

    return

def test_website(website, remove_file, out_dir, feature_funcs_m):

    out_file = os.path.abspath(os.path.join(out_dir, "chrome_"+website))
    
    # rewrite the original binary
    function_ranges = dict()
    with open(remove_file, 'r') as in_f:
        for line in in_f.readlines():
            line = line.strip()
            if line.startswith("#"):
                continue
            (f_id, start, end) = line.split()
            f_id = int(f_id)

            # exclude some features
            if "Web Notifications" in feature_funcs_m:
                if f_id in feature_funcs_m["Web Notifications"]:
                    continue

            start = int(start, 16)
            end = int(end, 16)
            assert start > 0 and end > 0
            function_ranges[f_id] = (start, end)
    
    # rewrite the binary
    rewrite(chrome, out_file, function_ranges)

    return

def main():
    parser = OptionParser()
    parser.add_option("-c", "--chrome", dest="chrome", help="The chrome binary being debloated.")
    parser.add_option("-i", "--input_log", dest="input_log", help="The file that contains removable functions for a website.")
    parser.add_option("-o", "--out", dest="out_dir", help="The output dir to put chrome file.")
    parser.add_option("-m", "--feature_funcs_mapping", dest="feature_funcs_mapping_json", help="The file contains feature functions mapping.")

    (options, args) = parser.parse_args()
    
    global chrome
    chrome = options.chrome
    input_log = options.input_log
    out_dir = options.out_dir
    feature_funcs_mapping_json = options.feature_funcs_mapping_json
    
    feature_funcs_m = None
    with open(feature_funcs_mapping_json, 'r') as in_f:
        feature_funcs_m = json.loads(in_f.read())
    
    website = input_log.split("/")[-1][:-4]

    test_website(website, input_log, out_dir, feature_funcs_m)
    
    return

if __name__ == "__main__":
    main()
