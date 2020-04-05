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

    #print " removed: ", removed_size/1000000, "MB"

    return

def execute_cmd(cmd):
    print cmd
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    p.communicate()

def kill_chrome(website):
    # get the chrome pid
    cmd = "ps -ef | grep chrome"
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    out = p.communicate()[0]

    for line in out.split("\n"):
        line = line.strip()
        if line.endswith(website):

            pid = line.split()[1]
        
            # kill the chrome
            cmd = "sudo kill -15 " + pid
            execute_cmd(cmd)

total_time = 0

def test_website(website, remove_file, out_dir, feature_funcs_m):
    global total_time

    out_file = os.path.abspath(os.path.join(out_dir, "chrome_"+website))
    
    start_time = time.time()
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
                    print "pass"
                    continue
            else:
                print "cannot find Web Notifications"
            if "Shared Web Workers" in feature_funcs_m:
                if f_id in feature_funcs_m["Shared Web Workers"]:
                    continue

            start = int(start, 16)
            end = int(end, 16)
            assert start > 0 and end > 0
            function_ranges[f_id] = (start, end)
    
    # rewrite the binary
    rewrite(chrome, out_file, function_ranges)

    end_time = time.time()

    total_time += (end_time - start_time)
    
    # change the binary permission
    cmd = "chmod +x " + out_file
    execute_cmd(cmd)

    # load the webpage
    cmd = out_file + " " + website
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # sleep for a while
    time.sleep(5)
    
    # kill chrome
    kill_chrome(website)

    out = p.communicate()
    print out

    # remove the binary
    cmd = "rm " + out_file
    execute_cmd(cmd)

    return

def main():
    parser = OptionParser()
    parser.add_option("-c", "--chrome", dest="chrome", help="The chrome binary being debloated.")
    parser.add_option("-i", "--input_dir", dest="input_dir", help="The directory that contains removable functions for websites.")
    parser.add_option("-o", "--out", dest="out_dir", help="The output dir to put chrome file.")
    parser.add_option("-m", "--feature_funcs_mapping", dest="feature_funcs_mapping_json", help="The file contains feature functions mapping.")

    (options, args) = parser.parse_args()
    
    global chrome
    chrome = options.chrome
    input_dir = options.input_dir
    out_dir = options.out_dir
    feature_funcs_mapping_json = options.feature_funcs_mapping_json
    
    feature_funcs_m = None
    with open(feature_funcs_mapping_json, 'r') as in_f:
        feature_funcs_m = json.loads(in_f.read())

    failed_websites = ["ltn.com.tw", "kickstarter.com", "ladbible.com", "dropbox.com", 
            "patreon.com", "sex.com", "smallpdf.com", "hepsiburada.com"]
    
    i = 0
    for fname in os.listdir(input_dir):
        i += 1

        website = fname[:-4]
        
        """
        if website not in failed_websites:
            continue
        """

        print "START: ==============", website

        fpath = os.path.join(input_dir, fname)

        test_website(website, fpath, out_dir, feature_funcs_m)

        print "END: ==============", website
        
        """
        if i == 5:
            break
        """
    
    print "Average time: ", float(total_time)/500.0
    return

if __name__ == "__main__":
    main()
