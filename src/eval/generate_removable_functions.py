#!/usr/bin/python
import sys, os, subprocess
from optparse import OptionParser

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

    (options, args) = parser.parse_args()
    out_dir = options.out_dir

    cwd = os.path.dirname(os.path.abspath(__file__))
    os.chdir(cwd + "/../rewrite")
    manual_feature_code_map = cwd + "/" + FEATURE_CODE_MAPPING_DIR + "/manual_feature_code_map.json"
    extended_feature_code_maps_dir = cwd + "/" + FEATURE_CODE_MAPPING_DIR + "/extended_feature_code_maps/"

    cmd = BIN + " " + manual_feature_code_map + " " + os.path.join(out_dir, "manual") + " 0.5"
    execute(cmd)

    for fname in os.listdir(extended_feature_code_maps_dir):
        tmp_name = fname.split(".json")[0]
        cmd = BIN + " " + os.path.join(extended_feature_code_maps_dir, fname) + " " + os.path.join(out_dir, tmp_name) + " 0.5"
        execute(cmd)

    os.chdir(cwd)

if __name__ == "__main__":
    main()

