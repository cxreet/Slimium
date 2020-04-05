
functionality_map = {
                        "/cc/": "compositor",
                        "/chrome/browser/": "browser frontend and backend", 
                        "/content/browser/": "browser backend", 
                        "/chrome/gpu/": "gpu", 
                        "/gpu/": "gpu", 
                        "/content/gpu/": "gpu", 
                        "/chrome/renderer/": "renderer", 
                        "/content/renderer/": "renderer", 
                        "/extensions/": "extension system", 
                        "/media/": "media", 
                        "/net/": "net", 
                        "/ui/": "ui", 
                        "/v8/": "v8", 
                    }

def get_dir(file_name):
    if file_name.startswith("/gen/"):
        file_name = file_name[4:]

    # devices
    if file_name.startswith("/device/"):
        return "device_" + file_name.split("/")[2]
        #return "devices"

    # services
    if file_name.startswith("/chrome/service/"):
        return "service_cloud_print"
        #return "services"

    if file_name.startswith("/services/") or file_name.startswith("/chrome/services/"):
        return "service_"+file_name.split("/")[2]
        #return "services"
    
    # components
    if file_name.startswith("/components/"):
        return "component_"+file_name.split("/")[2]
        #return "components"
    
    # thirdparty projects
    if file_name.startswith("/third_party/"):
        #return "third_party"
        return "third_party_"+file_name.split("/")[2]

    for pre_fix in functionality_map:
        if file_name.startswith(pre_fix):
            return pre_fix

    return "others"

def infer_functionality(file_name):
    if file_name.startswith("/gen/"):
        file_name = file_name[4:]
    
    # devices
    if file_name.startswith("/device/"):
        return "device_" + file_name.split("/")[2]
        #return "devices"

    # services
    if file_name.startswith("/chrome/service/"):
        return "service_cloud_print"
        #return "services"

    if file_name.startswith("/services/") or file_name.startswith("/chrome/services/"):
        return "service_"+file_name.split("/")[2]
        #return "services"
    
    # components
    if file_name.startswith("/components/"):
        return "components_"+file_name.split("/")[2]
        #return "components"
    
    # thirdparty projects
    if file_name.startswith("/third_party/"):
        #return "third_party"
        return "third_party_"+file_name.split("/")[2]

    for pre_fix in functionality_map:
        if file_name.startswith(pre_fix):
            return functionality_map[pre_fix]

    return "others"

def read_unique_indexes(in_f_name):
    sorted_file_names = []
    file_name_2_indexes = {}

    with open(in_f_name, 'r') as in_f:
        for line in in_f.readlines():
            line = line.strip()
            if line.startswith(".."):
                line = line[5:]
            elif not line.startswith("/"):
                line = "/" + line

            tokens = line.split()
            file_name = tokens[0]
            sorted_file_names.append(file_name)
            file_name_2_indexes[file_name] = []

            function_num = (len(tokens) - 1)/2
            for i in range(0, function_num):
                func_idx = int(tokens[i*2+1], 10)
                file_name_2_indexes[file_name].append(func_idx)
    
    sorted_file_names = sorted(sorted_file_names)
    return (sorted_file_names, file_name_2_indexes)

def read_unique_indexes_with_name(in_f_name):
    sorted_file_names = []
    file_name_2_funcs = {}

    with open(in_f_name, 'r') as in_f:
        for line in in_f.readlines():
            line = line.strip()
            if line.startswith(".."):
                line = line[5:]
            elif not line.startswith("/"):
                line = "/" + line

            tokens = line.split()
            file_name = tokens[0]
            sorted_file_names.append(file_name)
            file_name_2_funcs[file_name] = []

            function_num = (len(tokens) - 1)/2
            for i in range(0, function_num):
                func_idx = int(tokens[i*2+1], 10)
                func_name = tokens[i*2+2]
                file_name_2_funcs[file_name].append((func_idx, func_name))
    
    sorted_file_names = sorted(sorted_file_names)
    return (sorted_file_names, file_name_2_funcs)

def create_unique_index_2_filename_map(filename_2_funcs):
    idx_2_filename_map = {}

    for filename in filename_2_funcs:
        funcs = filename_2_funcs[filename]
        for (func_idx, func_name) in funcs:
            idx_2_filename_map[func_idx] = filename

    return idx_2_filename_map


def read_index_file(fname):
    name_2_index = {}
    index_2_name = {}

    with open(fname, 'r') as in_f:
        for line in in_f.readlines():
            line = line.strip()
            tokens = line.split()
            f_id = int(tokens[0], 10)
            f_name = tokens[1].strip()
            assert (f_name not in name_2_index)
            name_2_index[f_name] = f_id
            index_2_name[f_id] = f_name

    return (name_2_index, index_2_name)

# Get all the functions' ranges from the disassembled_functions.txt
def read_disassembled_functions(fname):
    functions = {}

    with open(fname, 'r') as in_f:
        for line in in_f.readlines():
            line = line.strip()
            tokens = line.split()
            f_id = int(tokens[0], 10)
            f_start = int(tokens[1], 16)
            f_end = int(tokens[2], 16)
            f_name = tokens[3]
            functions[f_id] = (f_start, f_end, f_name)

    return functions

# Read callgraph
def read_callgraph_file(fname):
    call_graph = {}
    
    with open(fname, 'r') as in_f:
        for line in in_f.readlines():
            line = line.strip()
            tokens = line.split()
            caller_id = int(tokens[0], 10)

            if caller_id not in call_graph:
                call_graph[caller_id] = set()

            for token in tokens[1:]:
                callee_id = int(token, 10)
                call_graph[caller_id].add(callee_id)

    return call_graph

# Create the related call graph with unique ids.
def create_unique_call_graph(index_2_unique_index, call_graph):
    unique_call_graph = {}
    not_found_ids = set()

    for caller_id in call_graph:
        unique_caller_id = index_2_unique_index[caller_id]
        if unique_caller_id not in unique_call_graph:
            unique_call_graph[unique_caller_id] = set()
        for callee_id in call_graph[caller_id]:
            if callee_id not in index_2_unique_index:
                not_found_ids.add(callee_id)
                continue
            unique_callee_id = index_2_unique_index[callee_id]
            unique_call_graph[unique_caller_id].add(unique_callee_id)

    print "In total, there are", len(not_found_ids), " not found"

    return unique_call_graph

# Get the sub call graph that only contains the functions in the binary.
def get_sub_unique_call_graph(unique_call_graph, functions_in_binary):
    sub_unique_call_graph = {}
    all_function_ids_in_binary = set()
    for filename in functions_in_binary:
        for function_id in functions_in_binary[filename]:
            all_function_ids_in_binary.add(function_id)

    for caller_id in unique_call_graph:
        if caller_id in all_function_ids_in_binary:
            sub_unique_call_graph[caller_id] = set()
        for callee_id in unique_call_graph[caller_id]:
            if callee_id in all_function_ids_in_binary:
                sub_unique_call_graph[caller_id].add(callee_id)
                
    return sub_unique_call_graph

# Create the mapping between ids (index.txt) and unique ids (unique_indexes.txt)
def map_id_and_unique_id(unique_index_2_func_name, func_name_2_index):
    unique_index_2_index = {}
    index_2_unique_index = {}
    for unique_idx in unique_index_2_func_name:
        func_name = unique_index_2_func_name[unique_idx]
        index = func_name_2_index[func_name]
        unique_index_2_index[unique_idx] = index
        index_2_unique_index[index] = unique_idx

    return (unique_index_2_index, index_2_unique_index)
