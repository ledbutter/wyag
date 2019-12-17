import collections

class GitObject (object):

    repo = None
    fmt = None

    def __init__(self, repo, data=None):
        self.repo=repo

        if data != None:
            self.deserialize(data)

    def serialize(self):
        """This function MUST be implemented by subclasses.
It must read the object's contents from self.data, a byte string, and do
whatever it takes to convert it into a meaningful representation.  What exactly that means depend on each subclass."""
        raise Exception("Unimplemented!")

    def deserialize(self, data):
        raise Exception("Unimplemented!")

class GitBlob(GitObject):
    fmt=b'blob'

    def serialize(self):
        return self.blobdata

    def deserialize(self, data):
        self.blobdata = data

class GitKvlm(GitObject):

    def deserialize(self, data):
        self.kvlm = self.kvlm_parse(data)

    def serialize(self):
        return self.kvlm_serialize(self.kvlm)

    # KVLM = "Key-Value List with Message", made up by original author
    def kvlm_parse(self, raw, start=0, dct=None):
        if not dct:
            # can't declare the argument as dct=OrderedDict() or all calls to the functions will endlessly grow the same dict
            dct = collections.OrderedDict()

        spaceIndex = raw.find(b' ', start)
        newlineIndex = raw.find(b'\n', start)

        # if space appears before newline, we have a keyword

        # base case
        # ================
        # If newline appears first (or there's no space at all, in which case find return -1), we assume a blank line.
        # A blank line means the remainder of the data is the message.
        if (spaceIndex < 0) or (newlineIndex < spaceIndex):
            assert(newlineIndex == start)
            dct[b''] = raw[start+1:]
            return dct

        # recursive case
        # ==================
        # we read a key-value pair and recurse for the next
        key = raw[start:spaceIndex]

        # find the end of the value, continuation lines begin with a space, so we loop uuntil we find a "\n" not followed by a space.
        end = start
        while True:
            end = raw.find(b'\n', end+1)
            if raw[end + 1] != ord(' '):
                break

        value = raw[spaceIndex+1:end].replace(b'\n ', b'\n')

        if key in dct:
            if type(dct[key]) == list:
                dct[key].append(value)
            else:
                dct[key] = [ dct[key], value ]
        else:
            dct[key] = value

        return self.kvlm_parse(raw, end + 1, dct)

    def kvlm_serialize(self, kvlm):
        ret = b''

        for k in kvlm.keys():
            if k == b'':
                continue
            val = kvlm[k]
            if type(val) != list:
                val = [val]
            
            for v in val:
                ret += k + b' ' + (v.replace(b'\n', b'\n ')) + b'\n'

        ret += b'\n' + kvlm[b'']
        
        return ret

class GitCommit(GitKvlm):
    fmt = b'commit'

class GitTreeLeaf(object):
    def __init__(self, mode, path, sha):
        self.mode = mode
        self.path = path
        self.sha = sha

    @staticmethod
    def tree_parse_one(raw, start=0):
        # Find the space terminator of the mode
        x = raw.find(b' ', start)
        assert(x-start == 5 or x-start == 6)

        # Read the mode
        mode = raw[start:x]

        # Find the NULL termatinator of the path
        y = raw.find(b'\x00', x)
        # and read the path
        path = raw[x+1:y]

        # Read the SHA and convert to a hex string
        sha = hex(int.from_bytes(raw[y+1:y+21], "big"))[2:] # hex() adds 0x in front, we don't want that

        return y+21, GitTreeLeaf(mode, path, sha)

    @staticmethod
    def tree_parse(raw):
        pos = 0
        max = len(raw)
        ret = list()
        while pos < max:
            pos, data = GitTreeLeaf.tree_parse_one(raw, pos)
            ret.append(data)

        return ret

    @staticmethod
    def tree_serialize(obj):
        #@FIXME Add serializer!
        ret = b''
        for i in obj.items:
            ret += i.mode
            ret += b' '
            ret += i.path
            ret += b'\x00'
            sha = int(i.sha, 16)
            #@FIXME Does
            ret += sha.to_bytes(20, byteorder="big")
        return ret

class GitTree(GitObject):
    fmt = b'tree'

    def deserialize(self, data):
        self.items = GitTreeLeaf.tree_parse(data)

    def serialize(self):
        return GitTreeLeaf.tree_serialize(self)

class GitTag(GitCommit):
    fmt = b'tag'
    