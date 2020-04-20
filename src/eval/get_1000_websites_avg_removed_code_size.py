#!/usr/bin/python
import sys, os, subprocess
from optparse import OptionParser

def main():
    parser = OptionParser()
    parser.add_option("-i", "--input", dest="input_dir", help="The logs dir.")

    (options, args) = parser.parse_args()
    input_dir = options.input_dir

    for fname in os.listdir(input_dir):
        if not fname.startswith("code_cov_"):
            continue

        code_cov = float(fname.split("code_cov_")[-1])
        print code_cov
        
        avg_removed_code_size = dict()
        code_cov_dir = os.path.join(input_dir, fname)
        for fname2 in os.listdir(code_cov_dir):

            if fname2 == "manual":
                tmp_fpath = os.path.join(code_cov_dir, fname2, "avg_removed_code_size.txt")
                if not os.path.exists(tmp_fpath):
                    continue
                with open(tmp_fpath, 'r') as in_f:
                    avg_removed_code_size["manual"] = float(in_f.readlines()[0].split()[0])
            elif fname2.startswith("extended_"):
                call_number_threshold = float(fname2.split("_")[1])
                name_similarity_threshold = float(fname2.split("_")[2])
                tmp_fpath = os.path.join(code_cov_dir, fname2, "avg_removed_code_size.txt")
                if not os.path.exists(tmp_fpath):
                    continue
                with open(tmp_fpath, 'r') as in_f:
                    avg_removed_code_size[str(call_number_threshold) + "_" + str(name_similarity_threshold)] = float(in_f.readlines()[0].split()[0])
        
        if "manual" in avg_removed_code_size:
            print "manual", avg_removed_code_size["manual"]
        for i in range(5, 10):
            for j in range(5, 10):
                s = str(i * 0.1) + "_" + str(j * 0.1)
                if s in avg_removed_code_size:
                    print s, avg_removed_code_size[s]


if __name__ == "__main__":
    main()
