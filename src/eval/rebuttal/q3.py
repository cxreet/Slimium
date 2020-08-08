#!/usr/bin/python
import sys, os, json

unique_indexes_file = "../../../out/unique_indexes.txt"
feature_code_map = "../../feature_code_mapping/patched_extended_feature_code_maps/extended_0.700000_0.700000_map.json"
front_page_profiling_out = "../../../out/last_logs/"

def main():

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
    
    # content security policy (CSP)
    csp_patterns = ["../../third_party/blink/renderer/core/frame/csp/",
                    "../../content/common/content_security_policy/",
                    "gen/third_party/blink/public/mojom/csp/"]
    csp_files = set()
    for file_name in file_2_ids:
        for csp_pattern in csp_patterns:
            if file_name.startswith(csp_pattern):
                csp_files.add(file_name)
    #print "CSP related files:", csp_files

    # subresource integrity (SRI)
    sri_patterns = ["../../third_party/blink/renderer/core/loader/subresource_integrity_helper.cc",
                    "../../third_party/blink/renderer/platform/loader/subresource_integrity.cc",
                    #"../../third_party/blink/renderer/platform/loader/fetch/integrity_metadata.cc"
                    ]
    sri_files = set()
    for file_name in file_2_ids:
        for sri_pattern in sri_patterns:
            if file_name.startswith(sri_pattern):
                sri_files.add(file_name)
    #print "SRI related files:", sri_files

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
    for file_name in file_2_ids:
        for cors_pattern in cors_patterns:
            if file_name.startswith(cors_pattern):
                cors_files.add(file_name)
    #print "CORS related files:", cors_files

    # get the feature to files mapping 
    feature_2_files = dict()
    with open(feature_code_map, 'r') as in_f:
        feature_2_files = json.load(in_f)

    # how many features contain CSP, SRI, CORS files
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
    #for fname in os.listdir(front_page_profiling_out):


    return

if __name__ == "__main__":
    main()
