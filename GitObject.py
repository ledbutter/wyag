import collections

class GitObject (object):

    repo = None

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

    fmt = None

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

    # def deserialize(self, data):
    #     self.kvlm = GitCommands.kvlm_parse(data)

    # def serialize(self):
    #     return GitCommands.kvlm_serialize(self.kvlm)

