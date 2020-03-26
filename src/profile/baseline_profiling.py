#!/usr/bin/python
import os, sys, subprocess, time

# Modify the following three variables to point to your related executables
CHROME = "/home/chenxiong/chromium/src/out/Profiling/chrome"
SHM_CLEAR = "/home/chenxiong/slimium/src/shm/shm_clear"
SHM_DECODE = "/home/chenxiong/slimium/src/shm/shm_decode"

"""
Customize following variables:
    - SLIDING_WINDOW_SIZE: sliding window size
    - LOADING_TIME: how many seconds for each page loading
"""
SLIDING_WINDOW_SIZE = 10
LOADING_TIME = 5

def usage():
    print """python baseline_profiling.py out_log_file"""
    sys.exit(1)

def execute(cmd):
    print cmd
    p = subprocess.Popen(cmd, shell=True)
    p.communicate()


def kill_chrome():
    # get the chrome pid
    cmd = "ps -ef | grep chrome"
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    out = p.communicate()[0]

    for line in out.split("\n"):
        line = line.strip()
        tokens = line.split()

        if len(tokens) < 2:
            continue

        pid = tokens[1]
        
        # kill the chrome
        cmd = "sudo kill -15 " + pid
        execute(cmd)

def write_log():
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

    with open(sys.argv[1], 'w') as out_f:
        for idx in idxs:
            out_f.write("%d\n" % (idx))

def profile_blank_website():
    
    # clear the fingerprint
    cmd = SHM_CLEAR
    execute(cmd)

    # do the profiling until it gets steady
    sliding_window = []
    sliding_idx = 0
    while True:
        cmd = CHROME
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
                kill_chrome()
                break
            else:
                for i in range(0, SLIDING_WINDOW_SIZE-1):
                    sliding_window[i] = sliding_window[i+1]
                sliding_window[SLIDING_WINDOW_SIZE-1] = len(idxs)
        
        # kill chrome
        kill_chrome()

    return

def main():

    profile_blank_website()
    write_log()

    return

if __name__ == "__main__":
    main()
