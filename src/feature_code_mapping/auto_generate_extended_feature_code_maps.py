#!/usr/bin/python
import os, sys, subprocess

v_list = [0.5, 0.6, 0.7, 0.8, 0.9]

def main():
    for v1 in v_list:
        for v2 in v_list:
            cmd = "./auto_extend_mapping.sh ./manual_feature_code_map.json %f %f ./extended_feature_code_maps/extended_%f_%f_map.json" % (v1, v2, v1, v2)
            print cmd
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
            p.communicate()

if __name__ == "__main__":
    main()
