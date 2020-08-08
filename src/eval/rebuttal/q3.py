#!/usr/bin/python
import sys, os, json

unique_indexes_file = "../../../out/unique_indexes.txt"
feature_code_map = "../../feature_code_mapping/patched_extended_feature_code_maps/extended_0.700000_0.700000_map.json"
front_page_profiling_out = "../../../out/last_logs/"
manual_profiling_out = "../manual_logs/"
function_boundaries_file = "../../../out/function_boundaries.txt"

def get_code_size(func_id_2_size, func_ids):
    s = 0
    for func_id in func_ids:
        if func_id not in func_id_2_size:
            continue
        s += func_id_2_size[func_id]
    return s

def main():
    # read function boundaries
    func_id_2_size = dict()
    with open(function_boundaries_file, 'r') as in_f:
        for line in in_f.readlines():
            line = line.strip()
            tokens = line.split()
            func_id = int(tokens[0])
            func_start_addr = int(tokens[1], 16)
            func_end_addr = int(tokens[2], 16)
            func_id_2_size[func_id] = func_end_addr - func_start_addr - 13

    file_2_ids = dict()
    # read unique_indexes file to get the file to function ids mapping
    with open(unique_indexes_file, 'r') as in_f:
        for line in in_f.readlines():
            line = line.strip()
            tokens = line.split()
            file_name = tokens[0].strip()
            func_ids = set()
            for i in range(0, (len(tokens)-1)/2):
                func_id = int(tokens[1+i*2], 10)
                func_ids.add(func_id)
            file_2_ids[file_name] = func_ids
    
    # same origin policy (SOP)
    sop_patterns = ["../../third_party/blink/common/origin_policy/",
                    "../../services/network/origin_policy/",
                    "gen/services/network/public/mojom/origin_policy_manager.mojom-blink.cc",
                    "../../content/browser/frame_host/origin_policy_throttle.cc",
                    "../../components/security_interstitials/content/origin_policy_ui.cc",
                    "gen/services/network/public/mojom/origin_policy_manager.mojom-shared.cc",
                    "../../services/network/public/cpp/origin_policy.cc",
                    "../../components/security_interstitials/content/origin_policy_interstitial_page.cc",
                    "../../chrome/browser/ssl/secure_origin_policy_handler.cc",
                    "gen/services/network/public/mojom/origin_policy_manager.mojom.cc"]
    sop_files = set()
    sop_ids = set()
    for file_name in file_2_ids:
        for sop_pattern in sop_patterns:
            if file_name.startswith(sop_pattern):
                sop_files.add(file_name)
                sop_ids = sop_ids | file_2_ids[file_name]
    sop_size = get_code_size(func_id_2_size, sop_ids)

    # content security policy (CSP)
    csp_patterns = ["../../third_party/blink/renderer/core/frame/csp/",
                    "../../content/common/content_security_policy/",
                    "gen/third_party/blink/public/mojom/csp/"]
    csp_files = set()
    csp_ids = set()
    for file_name in file_2_ids:
        for csp_pattern in csp_patterns:
            if file_name.startswith(csp_pattern):
                csp_files.add(file_name)
                csp_ids = csp_ids | file_2_ids[file_name]
    csp_size = get_code_size(func_id_2_size, csp_ids)

    # subresource integrity (SRI)
    sri_patterns = ["../../third_party/blink/renderer/core/loader/subresource_integrity_helper.cc",
                    "../../third_party/blink/renderer/platform/loader/subresource_integrity.cc",
                    #"../../third_party/blink/renderer/platform/loader/fetch/integrity_metadata.cc"
                    ]
    sri_files = set()
    sri_ids = set()
    for file_name in file_2_ids:
        for sri_pattern in sri_patterns:
            if file_name.startswith(sri_pattern):
                sri_files.add(file_name)
                sri_ids = sri_ids | file_2_ids[file_name]
    sri_size = get_code_size(func_id_2_size, sri_ids)

    # cross-origin resource sharing (CORS)
    cors_patterns = ["../../third_party/blink/renderer/platform/loader/cors/",
                     "gen/services/network/public/mojom/cors_origin_pattern.mojom-blink.cc",
                     "../../services/network/public/cpp/cors/",
                     "../../services/network/cors/",
                     "gen/services/network/public/mojom/cors.mojom.cc",
                     "../../content/public/browser/cors_exempt_headers.cc",
                     #"../../extensions/common/cors_util.cc",
                     "gen/services/network/public/mojom/cors.mojom-blink.cc",
                     "gen/services/network/public/mojom/cors_origin_pattern.mojom.cc",
                     "gen/services/network/public/mojom/cors_origin_pattern.mojom-shared.cc",
                     "gen/services/network/public/mojom/cors.mojom-shared.cc",
                     "../../content/public/browser/cors_origin_pattern_setter.cc"]
    cors_files = set()
    cors_ids = set()
    for file_name in file_2_ids:
        for cors_pattern in cors_patterns:
            if file_name.startswith(cors_pattern):
                cors_files.add(file_name)
                cors_ids = cors_ids | file_2_ids[file_name]
    cors_size = get_code_size(func_id_2_size, cors_ids)

    # get the feature to files mapping 
    feature_2_files = dict()
    with open(feature_code_map, 'r') as in_f:
        feature_2_files = json.load(in_f)

    # how many features contain SOP, CSP, SRI, CORS files
    print "Following features have SOP related code:"
    for feature in feature_2_files:
        files = feature_2_files[feature]
        for sop_file in sop_files:
            if sop_file in files:
                print feature
                break

    print "Following features have CSP related code:"
    for feature in feature_2_files:
        files = feature_2_files[feature]
        for csp_file in csp_files:
            if csp_file in files:
                print feature
                break

    print "Following features have SRI related code:"
    for feature in feature_2_files:
        files = feature_2_files[feature]
        for sri_file in sri_files:
            if sri_file in files:
                print feature
                break

    print "Following features have CORS related code:"
    for feature in feature_2_files:
        files = feature_2_files[feature]
        for cors_file in cors_files:
            if cors_file in files:
                print feature
                break

    # read the profiling results of top 1000 websites
    sop_used_websites = set()
    csp_used_websites = set()
    sri_used_websites = set()
    cors_used_websites = set()
    for fname in os.listdir(front_page_profiling_out):
        with open(os.path.join(front_page_profiling_out, fname), 'r') as in_f:
            executed_sop_func_ids = set()
            executed_csp_func_ids = set()
            executed_sri_func_ids = set()
            executed_cors_func_ids = set()
            for line in in_f.readlines():
                func_id = int(line.strip(), 10)
                if func_id in sop_ids:
                    executed_sop_func_ids.add(func_id)
                if func_id in csp_ids:
                    executed_csp_func_ids.add(func_id)
                if func_id in sri_ids:
                    executed_sri_func_ids.add(func_id)
                if func_id in cors_ids:
                    executed_cors_func_ids.add(func_id)
            #sop_code_cov = len(executed_sop_func_ids)/float(len(sop_ids)) 
            #csp_code_cov = len(executed_csp_func_ids)/float(len(csp_ids))
            #sri_code_cov = len(executed_sri_func_ids)/float(len(sri_ids))
            #cors_code_cov = len(executed_cors_func_ids)/float(len(cors_ids))
            sop_code_cov = get_code_size(func_id_2_size, executed_sop_func_ids)/float(sop_size)
            csp_code_cov = get_code_size(func_id_2_size, executed_csp_func_ids)/float(csp_size)
            sri_code_cov = get_code_size(func_id_2_size, executed_sri_func_ids)/float(sri_size)
            cors_code_cov = get_code_size(func_id_2_size, executed_cors_func_ids)/float(cors_size)
            print fname, sop_code_cov, csp_code_cov, sri_code_cov, cors_code_cov
            if sop_code_cov >= 0.05:
                sop_used_websites.add(fname)
            if csp_code_cov >= 0.05:
                csp_used_websites.add(fname)
            if sri_code_cov >= 0.05:
                sri_used_websites.add(fname)
            if cors_code_cov >= 0.05:
                cors_used_websites.add(fname)

    print "There are", len(sop_used_websites), "websites use SOP,", \
            len(csp_used_websites), "websites use CSP,", len(sri_used_websites), \
            "websites use SRI,", len(cors_used_websites), "websites use CORS."

    sop_used_websites = set()
    csp_used_websites = set()
    sri_used_websites = set()
    cors_used_websites = set()
    total_sop_code_cov = 0.0
    total_csp_code_cov = 0.0
    total_sri_code_cov = 0.0
    total_cors_code_cov = 0.0
    min_cors_code_cov = 1.0
    max_cors_code_cov = 0.0
    for fname in os.listdir(manual_profiling_out):
        with open(os.path.join(manual_profiling_out, fname), 'r') as in_f:
            executed_sop_func_ids = set()
            executed_csp_func_ids = set()
            executed_sri_func_ids = set()
            executed_cors_func_ids = set()
            for line in in_f.readlines():
                try:
                    func_id = int(line.strip(), 10)
                    if func_id in sop_ids:
                        executed_sop_func_ids.add(func_id)
                    if func_id in csp_ids:
                        executed_csp_func_ids.add(func_id)
                    if func_id in sri_ids:
                        executed_sri_func_ids.add(func_id)
                    if func_id in cors_ids:
                        executed_cors_func_ids.add(func_id)
                except:
                    continue
            #sop_code_cov = len(executed_sop_func_ids)/float(len(sop_ids)) 
            #csp_code_cov = len(executed_csp_func_ids)/float(len(csp_ids))
            #sri_code_cov = len(executed_sri_func_ids)/float(len(sri_ids))
            #cors_code_cov = len(executed_cors_func_ids)/float(len(cors_ids))
            sop_code_cov = get_code_size(func_id_2_size, executed_sop_func_ids)/float(sop_size)
            csp_code_cov = get_code_size(func_id_2_size, executed_csp_func_ids)/float(csp_size)
            sri_code_cov = get_code_size(func_id_2_size, executed_sri_func_ids)/float(sri_size)
            cors_code_cov = get_code_size(func_id_2_size, executed_cors_func_ids)/float(cors_size)
            if cors_code_cov < min_cors_code_cov:
                min_cors_code_cov = cors_code_cov
            if cors_code_cov > max_cors_code_cov:
                max_cors_code_cov = cors_code_cov
            total_sop_code_cov += sop_code_cov
            total_csp_code_cov += csp_code_cov
            total_sri_code_cov += sri_code_cov
            total_cors_code_cov += cors_code_cov
            print fname, sop_code_cov, csp_code_cov, sri_code_cov, cors_code_cov
            if sop_code_cov >= 0.05:
                sop_used_websites.add(fname)
            if csp_code_cov >= 0.05:
                csp_used_websites.add(fname)
            if sri_code_cov >= 0.05:
                sri_used_websites.add(fname)
            if cors_code_cov >= 0.05:
                cors_used_websites.add(fname)
    print "There are", len(sop_used_websites), "websites use SOP,", \
            len(csp_used_websites), "websites use CSP,", len(sri_used_websites), \
            "websites use SRI,", len(cors_used_websites), "websites use CORS."
    print "Average code coverage:", total_sop_code_cov/40.0, total_csp_code_cov/40.0, total_sri_code_cov/40.0, total_cors_code_cov/40.0
    print "Min CORS code cov:", min_cors_code_cov, "Max CORS code cov:", max_cors_code_cov


    return

if __name__ == "__main__":
    main()
