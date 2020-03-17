#!/usr/bin/python
import os, sys, subprocess, time

# Modify the following three variables to point to your related executables
CHROME = "/home/chenxiong/chromium/src/out/Profiling/chrome"
SHM_CLEAR = "/home/chenxiong/slimium/src/shm/shm_clear"
SHM_DECODE = "/home/chenxiong/slimium/src/shm/shm_decode"

"""
Customize following variables:
    - WEBSITE_NUM: number of websites to profile
    - SLIDING_WINDOW_SIZE: sliding window size
    - LOADING_TIME: how many seconds for each page loading
"""
WEBSITE_NUM = 3
SLIDING_WINDOW_SIZE = 10
LOADING_TIME = 5

def usage():
    print """python evolve_profiling.py out_dir"""
    sys.exit(1)

def execute(cmd):
    print cmd
    p = subprocess.Popen(cmd, shell=True)
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
            execute(cmd)

def write_log(website, log_idx, idxs):
    out_dir = os.path.join(sys.argv[1], website)
    out_f = os.path.join(out_dir, website+"_"+str(log_idx)+".log")

    with open(out_f, 'w') as out_f:
        for idx in idxs:
            out_f.write(str(idx) + "\n")

def profile_website(website):
    out_dir = os.path.join(sys.argv[1], website)

    if os.path.exists(out_dir):
        print "skip ", website
        return

    # create the out directory for the website
    cmd = "mkdir -p " + out_dir
    execute(cmd)
    
    # clear the fingerprint
    cmd = SHM_CLEAR
    execute(cmd)

    # do the profiling until it gets steady
    sliding_window = []
    sliding_idx = 0
    log_idx = 0
    while True:
        cmd = CHROME + " " + website
        subprocess.Popen(cmd, shell=True)
        
        # sleep for some seconds
        time.sleep(LOADING_TIME)

        cmd = SHM_DECODE
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        out = p.communicate()[0]
        idxs = []
        for line in out.split("\n"):
            line = line.strip()
            try:
                idx = int(line, 10)
                idxs.append(idx)
            except:
                pass

        print "There are ", len(idxs), "functions executed"
        log_idx += 1
        write_log(website, log_idx, idxs)

        if sliding_idx != SLIDING_WINDOW_SIZE:
            sliding_window.append(len(idxs))
            sliding_idx += 1
        else:
            all_equal = True
            # check whether all the elements in sliding window are same
            for i in range(0, SLIDING_WINDOW_SIZE-1):
                if sliding_window[i] != sliding_window[i+1]:
                    all_equal = False
                    break

            if all_equal and sliding_window[SLIDING_WINDOW_SIZE-1] == len(idxs):
                kill_chrome(website)
                break
            else:
                for i in range(0, SLIDING_WINDOW_SIZE-1):
                    sliding_window[i] = sliding_window[i+1]
                sliding_window[SLIDING_WINDOW_SIZE-1] = len(idxs)
        
        # kill chrome
        kill_chrome(website)

    return

def main():
    cmd = "mkdir -p " + sys.argv[1]
    execute(cmd)

    all_websites = []
    with open("top-1m.csv", 'r') as in_f:
        for line in in_f.readlines():
            line = line.strip()
            website = line.split(",")[-1]
            all_websites.append(website)

    for i in range(0, WEBSITE_NUM):
        website = all_websites[i]
        profile_website(website)

    return

if __name__ == "__main__":
    if len(sys.argv) != 2:
        usage()

    main()
