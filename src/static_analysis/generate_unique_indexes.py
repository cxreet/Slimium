#!/usr/bin/python
import sys, os

"""
Take index.txt and file_functions.txt, generate unique indexes, so that
functions with same names but in different LLVM IR modules will have 
different indexes.

python generate_unique_indexes.py index.txt file_functions.txt

"""

index_2_name = {}
name_2_index = {}
file_2_functions = {}

def usage():
    print """python generate_unique_indexes.py index.txt file_functions.txt"""
    sys.exit(1)

def main():
    global index_2_name, name_2_index, file_2_functions

    with open(sys.argv[1], 'r') as in_f:
        for line in in_f.readlines():
            line = line.strip()
            tokens = line.split()
            idx = 0
            name = tokens[1]
            if tokens[0].startswith("+"):
                idx = int(tokens[0][1:], 10)
            else:
                idx = int(tokens[0], 10)
            
            index_2_name[idx] = name
            name_2_index[name] = idx
    
    all_file_names = []
    with open(sys.argv[2], 'r') as in_f:
        for line in in_f.readlines():
            line = line.strip()
            tokens = line.split()
            file_name = tokens[0]
            all_file_names.append(file_name)
            file_2_functions[file_name] = []
            for token in tokens[1:]:
                idx = int(token, 10)
                file_2_functions[file_name].append(idx)

    all_file_names = sorted(all_file_names)
    
    idx = 0

    for file_name in all_file_names:
        s = file_name + " "
        functions = file_2_functions[file_name]
        for func_idx in functions:
            func_name = index_2_name[func_idx]
            s += str(idx) + " " + func_name + " "
            idx += 1

        print s

    return

if __name__ == "__main__":
    main()
