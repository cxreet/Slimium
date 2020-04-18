#!/usr/bin/python
import os, sys, subprocess
from optparse import OptionParser

"""
python rewrite_and_test.py -c ./chrome -i /home/chenxiong/slimium/out/removeable_functions/manual/ -o /home/chenxiong/chromium/src/out/Marking/ -m /home/chenxiong/slimium/out/removeable_functions/manual/feature_functions.json &> 
"""

def execute(cmd):
    print cmd
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    p.communicate()

def main():
    parser = OptionParser()
    parser.add_option("-i", "--input_dir", dest="input_dir", help="The input dir that contains dirs of removeable function results.")
    parser.add_option("-o", "--output_dir", dest="output_dir", help="The output dir to put debloated binary.")

    (options, args) = parser.parse_args()
    input_dir = options.input_dir
    output_dir = options.output_dir

    cwd = os.path.dirname(os.path.abspath(__file__))
    os.chdir(cwd+"/../rewrite")

    for fname in os.listdir(input_dir):
        if not fname.startswith("extended_"):
            continue
        
        remove_func_dir = os.path.join(input_dir, fname)
        cmd = "python rewrite_and_test.py -c ./chrome -i %s -o %s -m %s &> %s"  % \
                (remove_func_dir, output_dir, os.path.join(remove_func_dir, "feature_functions.json"), \
                os.path.join(remove_func_dir, "test_1000_results.txt"))
        
        print cmd
        #execute(cmd)

    os.chdir(cwd)

if __name__ == "__main__":
    main()
