#!/usr/bin/python
import sys, os, subprocess

"""
Before running this script, please generate the disassembly by running:
    objdump -d -w -z --insn-width=32 /mnt/sdb/chenxiong/chrome/chromium/src/out/Marking/chrome > chrome.asm

Then run this script:
    python disassemble.py chrome.asm > disassembled_functions.txt

The output format for each line:
    function_id, function_start_addr, function_end_addr, function_name
"""

lines = None
line_num = 0

def get_bitnum(n):
    ret = 1

    while n >= 2:
        ret += 1
        n = n/2

    return ret

def get_id(s):
    tokens = s.split(",")
    int_num_str = tokens[-1].split("(")[0]
    int_num = 0
    if int_num_str != "":
        int_num = int(int_num_str, 16)
    bit_num = int(tokens[0].split("$")[-1], 16)
    idx = int_num*8 + get_bitnum(bit_num) - 1

    return idx


def main():
    global lines, line_num
    
    # disassemble chrome
    cwd = os.path.dirname(os.path.realpath(__file__))
    if not os.path.exists(cwd+"/chrome.asm"):
        cmd = "objdump -d -w -z --insn-width=32 %s > %s/chrome.asm" % (sys.argv[1], cwd)
        print cmd
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        p.communicate()

    functions = []

    with open(cwd+"/chrome.asm", 'r') as in_f:
        lines = in_f.readlines()
        line_num = len(lines)

        i = 0
        while i < line_num:
            line = lines[i].strip()
            # found a function head
            if line.endswith(">:"):
                tokens = line.split()
                f_addr = int("0x"+tokens[0], 16)
                f_name = tokens[-1][1:-2]

                insns = [] 
                # parse the function body until an empty line
                j = i + 1
                while j < line_num:
                    insn_line = lines[j].strip()
                    if len(insn_line) == 0:
                        break
                    
                    tokens = insn_line.split()

                    try:
                        i_addr = int("0x"+tokens[0][:-1], 16)
                        i_len = len(insn_line[:106].split()) - 1
                        tokens2 = insn_line[106:].split()
                        i_opcode = tokens2[0]
                        i_operands = []
                        if len(tokens2) > 1:
                            i_operands = tokens2[1:]
                        insns.append((i_addr, i_len, i_opcode, i_operands))
                    except:
                        print insn_line

                    j += 1
                
                functions.append((f_addr, f_name, insns))

                i = j + 1
            else:
                i += 1
    
    out_f = open(sys.argv[2], 'w')

    total_ids = 0
    out = []
    for (f_addr, f_name, insns) in functions:
        f_end = insns[-1][0] + insns[-1][1] - 1
        ids = []
        i = 0
        found_global_id_ref = False
        while i < len(insns):
            (i_addr, i_len, i_opcode, i_operands) = insns[i]
            if i_opcode == "mov" and len(i_operands) == 4 and i_operands[-1] == "<_DYNAMIC+0x460>":
                found_global_id_ref = True
                register = i_operands[0].split(",")[-1]
                j = i + 1
                while j < len(insns):
                    (i_addr2, i_len2, i_opcode2, i_operands2) = insns[j]
                    if i_opcode2 == "movl" and len(i_operands2) == 1 and i_operands2[0].endswith("(" + register + ")"):
                        func_id = int(i_operands2[0].split(",")[0][1:], 16)
                        ids.append(func_id)
                        total_ids += 1
                        break
                    j += 1

                i = j + 1
            else:
                i += 1
        
        if found_global_id_ref and len(ids) == 0:
            print "WARN:", hex(f_addr)
        assert len(ids) <= 1
        if len(ids) == 1:
            #print ids[0], hex(f_addr), hex(f_end), f_name
            out_f.write("%d 0x%x 0x%x %s\n" % (ids[0], f_addr, f_end, f_name))
    
    """
    cmd = "rm " + cwd + "/chrome.asm"
    print cmd
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    p.communicate()
    """

    #print "====There are ", len(functions), "functions and ", total_ids, "ids===="


if __name__ == "__main__":
    main()
