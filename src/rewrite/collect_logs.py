#!/usr/bin/python
import os, sys, subprocess
from shutil import copyfile

def main():
    if not os.path.exists(sys.argv[2]):
        cmd = "mkdir -p " + sys.argv[2]
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        p.communicate()
        
    website_num = 1000
    
    websites = set()
    with open("../profile/top-1m.csv", 'r') as in_f:
        for line in in_f.readlines():
            tokens = line.strip().split(",")
            idx = int(tokens[0], 10)
            website = tokens[1]

            if idx <= website_num:
                websites.add(website)

    for website_name in os.listdir(sys.argv[1]):
        if website_name not in websites:
            continue

        p = os.path.join(sys.argv[1], website_name)
        
        log_num = 0
        for fname in os.listdir(p):
            log_num += 1

        log_path = os.path.join(p, website_name+"_"+str(log_num)+".log")

        out_log_path = os.path.join(sys.argv[2], website_name+".log")

        copyfile(log_path, out_log_path)


if __name__ == "__main__":
    main()
