#!/usr/bin/python3
import textdistance

class Section(object):
    def __init__(self):
        """
        This class represent each section in ELF
        """
        self.idx = -1
        self.parser = None      # Pointer to elf.get_section(idx)

        # Section description
        self.type = None        # 'sh_type': "Section Type"
        self.align = 0x0        # 'sh_addralign': "Section Address Align"
        self.offset = 0x0       # 'sh_offset': "Section Offset"
        self.entsize = 0x0      # 'sh_entsize': "Section Entry Size"
        self.name = ''          # 'sh_name': "Section Name"
        self.flags = 0x0        # 'sh_flags': "Section Flags"
        self.sz = 0x0           # 'sh_size': "Section Size"
        self.va = 0x0           # 'sh_addr': "Section VA"
        self.link = 0x0         # 'sh_link': "Section Link"
        self.info = 0x0         # 'sh_info': "Section Info"

        self.start = 0x0
        self.end = 0x0
        self.file_offset = 0x0  # includes the alignment to rewrite a binary
        self.next = None

    def __repr__(self):
        return '[Sec#%2d] FileOff[0x%04x:0x%04x] VA=0x%08x (%s)' \
               % (self.idx, self.start, self.file_offset, self.va, self.name)


class Symbol(object):
    def __init__(self):
        """
        This class represent each symbol in ELF (i.e., .symtab or .dynsym)
        """
        self.idx = -1
        self.parser = None

        # Symbol description
        self.name = ''
        self.type = 0x0
        self.bind = 0x0
        self.other = 0x0
        self.shndx = 0x0
        self.val = 0x0
        self.sz = 0x0

        # Property
        self.is_import = False
        self.is_export = False
        self.file_path = None

    def __repr__(self):
        return '[Sym#%2d] %s (Val=0x%08x, Size=%d)' \
            % (self.idx, self.name, self.val, self.sz)


class Function(object):
    def __init__(self):
        self.idx = -1
        self.name = None
        self.demangled = None
        self.start = 0x0
        self.end = 0x0

        self.cu = None
        self.line = 0x0
        self.refs_to = set()
        self.refs_from = set()

        self.is_webapi = False

    def __repr__(self):
        '''
        return '[Fun#%3d] %s (RefTos=%d, RefFroms=%d)' \
            % (self.idx, self.demangled, len(self.refs_to), len(self.refs_from))
        '''
        return ('%d' % (self.idx))


class BinaryFunction(object):
    """
    Note that we are working on (best-effort) collected data
    Incompleteness and unsoundness may happen!
    """
    def __init__(self, fid):
        # A function id (fid) is a unique identifier to access any binary function
        # This is the id from a global mapping (i.e., shared memory)
        self.fid = fid

        # Another index used in a call graph
        # Default value is negative, meaning no such function found
        self.cid = -1

        # Two types
        #   a) function available only from IR (0x0)
        #   b) binary function available from both IR/symbol (0x1)
        self.type = 0x0

        # Basic info
        self.name = None            # Binary function name (i.e., mangled symbol name)
        self.redundant_name = False # Multiple functions with the same name
        self.start = 0x0            # Function start VA
        self.end = 0x0              # Function end VA

        # whether it's found in binary
        self.in_binary = False

        # how frequently it is executed
        self.exe_freq = 0

        # Detailed info
        self.src_dir = None         # Source directory this function belongs to
        self.src_file = None        # Source file this function belongs to
        self.ref_from = []
        self.ref_to = []

    @property
    def path(self):
        import os
        return os.path.join(self.src_dir, self.src_file)

    @property
    def size(self):
        return self.end - self.start + 1

    @property
    def demangled_name(self):
        import cxxfilt
        return cxxfilt.demangle(self.name)

    def __repr__(self):
        return ('%d (%s@%s)' % (self.fid, self.name, self.path))

class SourceFile(object):

    def __init__(self, path):
        self.path = path
        
        self.ref_from = dict()
        self.ref_from_sim_m = dict()
        self.ref_to = dict()
        self.ref_to_sim_m = dict()
        self.in_weight = 0
        self.out_weight = 0
    
    """ 
        When some function in this file is called by a function with
        `func_id` in `src_file`
    """
    def add_ref_from(self, src_file, func_id):
        if src_file not in self.ref_from:
            self.ref_from[src_file] = set()
        self.ref_from[src_file].add(func_id)
        (fname1, fname2, s) = self.get_similarity(self.path, src_file.path)
        self.ref_from_sim_m[src_file] = s
    
    """
        When some function in this file calls a function with
        `func_id` in `src_file`
    """
    def add_ref_to(self, src_file, func_id):
        if src_file not in self.ref_to:
            self.ref_to[src_file] = set()
        self.ref_to[src_file].add(func_id)
        (fname1, fname2, s) = self.get_similarity(self.path, src_file.path)
        self.ref_to_sim_m[src_file] = s
    
    # To use SourceFile object as keys of a dict, the following functions have to
    # be implemented.
    def __hash__(self):
        return hash(self.path)
    
    def __eq__(self, other):
        return self.path == other.path
    
    def __ne__(self, other):
        return not(self.path == other.path)

    def get_similarity(self, fname1, fname2):
        fname1 = ".".join(fname1.split("/")[-1].split(".")[:-1])
        fname2 = ".".join(fname2.split("/")[-1].split(".")[:-1])
        tokens1 = fname1.split("_")
        tokens2 = fname2.split("_")

        total_s = 0.0
        for t1 in tokens1:
            max_s = 0.0
            for t2 in tokens2:
                s = textdistance.hamming.normalized_similarity(t1, t2)
                if s > max_s:
                    max_s = s
            total_s += max_s

        for t1 in tokens2:
            max_s = 0.0
            for t2 in tokens1:
                s = textdistance.hamming.normalized_similarity(t1, t2)
                if s > max_s:
                    max_s = s
            total_s += max_s

        s1 = total_s / (len(tokens1) + len(tokens2))
        s2 = textdistance.hamming.normalized_similarity(fname1, fname2)

        if s1 > s2:
            return (fname1, fname2, s1)
        else:
            return (fname1, fname2, s2)

class SourceDir(object):
    
    def __init__(self, path):
        self.path = path

        self.ref_from = dict()
        self.ref_to = dict()

    """ 
        When some function in this directory is called by a function with
        `func_id` in `src_dir`
    """
    def add_ref_from(self, src_dir, func_id):
        if src_dir not in self.ref_from:
            self.ref_from[src_dir] = set()
        self.ref_from[src_dir].add(func_id)

    """
        When some function in this directory calls a function with
        `func_id` in `src_dir`
    """
    def add_ref_to(self, src_dir, func_id):
        if src_dir not in self.ref_to:
            self.ref_to[src_dir] = set()
        self.ref_to[src_dir].add(func_id)
    
    # To use SourceFile object as keys of a dict, the following functions have to
    # be implemented.
    def __hash__(self):
        return hash(self.path)
    
    def __eq__(self, other):
        return self.path == other.path
    
    def __ne__(self, other):
        return not(self.path == other.path)

class ChromeFeature(object):
    def __init__(self):
        self.id = 0x0
        self.desc = None
        self.is_feature_policy = False
        self.policy_name = None

        # Three types
        #   a) JS API: 0x0
        #   b) WebAPI: 0x1
        #   c) Other types for debloating: 0x2
        self.type = 0x0

        self.impl_paths = []
        self.functions = []

    def __repr__(self):
        feature_policy = '*' if self.is_feature_policy else ''
        return ('%d%s (%s)' % (self.id, feature_policy, self.desc))
