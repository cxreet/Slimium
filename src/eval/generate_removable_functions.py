#!/usr/bin/python
import sys, os, subprocess
from optparse import OptionParser
import multiprocessing
from multiprocessing import Pool

"""
./get_removable_functions.sh ~/slimium/src/feature_code_mapping/manual_feature_code_map.json ~/slimium/out/removeable_functions 0.5
"""

BIN = "./get_removable_functions.sh"
FEATURE_CODE_MAPPING_DIR = "../feature_code_mapping/"

def execute(cmd):
    print cmd
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    p.communicate()

def main():
    parser = OptionParser()
    parser.add_option("-o", "--out", dest="out_dir", help="The output dir.")
    parser.add_option("-i", "--input", dest="input_dir", help="The logs dir.")

    (options, args) = parser.parse_args()
    out_dir = options.out_dir
    input_dir = options.input_dir

    cwd = os.path.dirname(os.path.abspath(__file__))
    os.chdir(cwd + "/../rewrite")
    manual_feature_code_map = cwd + "/" + FEATURE_CODE_MAPPING_DIR + "/manual_feature_code_map.json"
    extended_feature_code_maps_dir = cwd + "/" + FEATURE_CODE_MAPPING_DIR + "/extended_feature_code_maps/"

    all_cmds = list()
    
    for i in range(2, 10):
        code_cov_threshold = float(i) * 0.05
        new_out_dir = os.path.join(out_dir, "code_cov_"+str(code_cov_threshold))
        cmd = BIN + " " + input_dir + " " + manual_feature_code_map + " " + os.path.join(new_out_dir, "manual") + " " + str(code_cov_threshold)
        all_cmds.append(cmd)
        #execute(cmd)

        for fname in os.listdir(extended_feature_code_maps_dir):
            tmp_name = fname.split(".json")[0]
            cmd = BIN + " " + input_dir + " " + os.path.join(extended_feature_code_maps_dir, fname) + " " + os.path.join(new_out_dir, tmp_name) + " " + str(code_cov_threshold)
            #execute(cmd)
            all_cmds.append(cmd)

    nprocess = multiprocessing.cpu_count()
    pool = Pool(processes=nprocess)
    pool.map(execute, all_cmds, chunksize=1)
    pool.terminate()


    os.chdir(cwd)

if __name__ == "__main__":
    main()

