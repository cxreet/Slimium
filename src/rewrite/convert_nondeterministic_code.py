#!/usr/bin/python
#!/usr/bin/python
from __future__ import division
from optparse import OptionParser
from utils import *


def convert_index_2_function(unique_index_file, input_file, output_file):
    file_functions = dict()
    (sorted_file_names, file_name_2_funcs) = read_unique_indexes_with_name(unique_index_file)
    indexes = list()
    with open(input_file, 'r') as in_f:
        for line in in_f.readlines():
            line = line.strip()
            indexes.append(int(line, 10))
    
    idx_2_file_func = dict()
    for file_name in file_name_2_funcs:
        for (func_idx, func_name) in file_name_2_funcs[file_name]:
            idx_2_file_func[func_idx] = (file_name, func_name)

    for idx in indexes:
        (file_name, func_name) = idx_2_file_func[idx]
        if file_name not in file_functions:
            file_functions[file_name] = list()
        file_functions[file_name].append(func_name)

    with open(output_file, 'w') as out_f:
        for file_name in file_functions:
            out_f.write(file_name)
            out_f.write(' ')
            for func_name in file_functions[file_name]:
                out_f.write(func_name)
                out_f.write(' ')
            out_f.write("\n")

    return

def convert_function_2_index(unique_index_file, input_file, output_file):
    (sorted_file_names, file_name_2_funcs) = read_unique_indexes_with_name(unique_index_file)

    file_func_2_idx = dict()
    for file_name in file_name_2_funcs:
        for (func_idx, func_name) in file_name_2_funcs[file_name]:
            file_func_2_idx[(file_name, func_name)] = func_idx
    
    indexes = list()
    with open(input_file, 'r') as in_f:
        for line in in_f.readlines():
            line = line.strip()
            tokens = line.split()
            file_name = tokens[0].strip()
            for func_name in tokens[1:]:
                idx = file_func_2_idx[(file_name, func_name)]
                indexes.append(idx)

    with open(output_file, 'w') as out_f:
        for idx in indexes:
            out_f.write(str(idx)+"\n")


    return

def main():
    parser = OptionParser()
    parser.add_option("-u", "--unique_index_file", dest="unique_index_file", help="The unique index file.")
    parser.add_option("-c", "--command", dest="command", help="The command: i2f -- indexes to functions; f2i -- functions to indexes.")
    parser.add_option("-i", "--input_file", dest="input_file", help="The input file.")
    parser.add_option("-o", "--output_file", dest="output_file", help="The output file.")

    (options, args) = parser.parse_args()
    unique_index_file = options.unique_index_file
    command = options.command
    input_file = options.input_file
    output_file = options.output_file

    if command == "i2f":
        convert_index_2_function(unique_index_file, input_file, output_file)
    elif command == "f2i":
        convert_function_2_index(unique_index_file, input_file, output_file)
    else:
        assert(False)

if __name__ == "__main__":
    main()

