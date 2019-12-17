import os
import configparser
import GitRepository
import zlib
import hashlib
import GitObject
import collections
import re

def repo_create(path):
    """Create a new repository at path."""

    return GitRepository.GitRepository(path)

def repo_find(path=".", required=True):
    # @FIXME: memoize this (except for ".")
    realPath = os.path.realpath(path)

    if os.path.isdir(os.path.join(realPath, ".git")):
        return GitRepository.GitRepository(realPath)

    # If we haven't returned, recurse to parent
    parent = os.path.realpath(os.path.join(realPath, ".."))

    if parent == realPath:
        # Bottom case
        # os.path.join("/", "..") == "/":
        # If parent==path, then path is root.
        if required:
            raise Exception("No git directory found in %s hierarchy" % path)
        else:
            return None

    return repo_find(parent, required)

def object_read(repo, sha):
    """Read object object_id from Git repository repo.  Return a
    GitObject whose exact type depends on the object."""

    path = repo.repo_file("objects", sha[0:2], sha[2:])

    with open (path, "rb") as f:
        raw = zlib.decompress(f.read())

        # Read object type
        x = raw.find(b' ')
        fmt = raw[0:x]

        # Read and validate object size
        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode("ascii"))
        if size != len(raw)-y-1:
            raise Exception("Malformed object {0}: bad length".format(sha))

        # Pick constructor
        if   fmt==b'commit' : c=GitObject.GitCommit
        elif fmt==b'tree'   : c=GitObject.GitTree
        elif fmt==b'tag'    : c=GitObject.GitTag
        elif fmt==b'blob'   : c=GitObject.GitBlob
        else:
            raise Exception("Unknown type {0} for object {1}".format(fmt.decode("ascii"), sha))

        # Call constructor and return object
        return c(repo, raw[y+1:])

def object_find(repo, name, fmt=None, follow=True):
    sha = object_resolve(repo, name)

    if not sha:
        raise Exception("No such reference {0}.".format(name))

    if len(sha) > 1:
        raise Exception("Ambiguous reference {0}: Candidates are:\n - {1}".format(name, "\n - ".join(sha)))

    sha = sha[0]

    if not fmt:
        return sha

    while True:
        obj = object_read(repo, sha)
        if obj.fmt == fmt:
            return sha
        
        if not follow:
            return None
        
        # Follow tags
        if obj.fmt == b'tag':
            sha = obj.kvlm[b'object'].decode("ascii")
        elif obj.fmt == b'commit' and fmt == b'tree':
            sha = obj.kvlm[b'tree'].decode("ascii")
        else:
            return None

def object_write(obj, actually_write=True):
    # Serialize object data
    data = obj.serialize()
    # Add header
    result = obj.fmt + b' ' + str(len(data)).encode() + b'\x00' + data
    # Compute hash
    sha = hashlib.sha1(result).hexdigest()

    if actually_write:
        # Compute path
        path = obj.repo.repo_file("objects", sha[0:2], sha[2:], mkdir=actually_write)

        with open(path, 'wb') as f:
            # Compress and write
            f.write(zlib.compress(result))

    return sha
    
def object_hash(fd, fmt, repo=None):
    data = fd.read()

    # Choose constructor depending on
    # object type found in header.
    if   fmt==b'commit' : obj=GitObject.GitCommit(repo, data)
    elif fmt==b'tree'   : obj=GitObject.GitTree(repo, data)
    elif fmt==b'tag'    : obj=GitObject.GitTag(repo, data)
    elif fmt==b'blob'   : obj=GitObject.GitBlob(repo, data)
    else:
        raise Exception("Unknown type %s!" % fmt)

    return object_write(obj, repo)

def ref_resolve(repo, ref):
    with open(repo.repo_file(ref), 'r') as fp:
        data = fp.read()[:-1]
        # Drop final \n ^^^^^
    if data.startswith("ref: "):
        return ref_resolve(repo, data[5:])
    else:
        return data

def ref_list(repo, path=None):
    if not path:
        path = repo.repo_dir("refs")
    ret = collections.OrderedDict()
    # Git shows refs sorted. To do the same, we use an OrderedDict and sort the output of listdir
    for f in sorted(os.listdir(path)):
        can = os.path.join(path, f)
        if os.path.isdir(can):
            ret[f] = ref_list(repo, can)
        else:
            ret[f] = ref_resolve(repo, can)
    
    return ret

def object_resolve(repo, name):
    """Resolve name to an object hash in repo.

    This function is aware of:

    - the HEAD literal
    - short and long hashes
    - tags
    - branches
    - remote branches"""

    if not name.strip():
        return None

    if name == "HEAD":
        return [ ref_resolve(repo, "HEAD")]

    candidates = list()
    hashRE = re.compile(r"^[0-9A-Fa-f]{40}$")
    smallHashRE = re.compile(r"^[0-9A-Fa-f]{4,39}$")

    if hashRE.match(name):
        # complete hash
        return [ name.lower() ]
    elif smallHashRE.match(name):
        # small hash, minimum length is 4 as documented in git-rev-parse
        smallHash = name.lower()
        prefix = smallHash[0:2]
        path = repo.repo_dir("objects", prefix, mkdir=False)
        if path:
            rem = smallHash[2:]
            for f in os.listdir(path):
                if f.startswith(rem):
                    candidates.append(prefix + f)
    
    return candidates