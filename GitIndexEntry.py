class GitIndexEntry(object):
    ctime = None
    """The last time a file's metadata changed. This is a tuple (seconds, nanoseconds)"""

    mtime = None
    """The last time a file's data changed. This is a tuple (seconds, nanoseconds)"""

    dev = None
    """The ID of device containing this file"""

    ino = None
    """The file's inode number"""

    mode_type = None
    """The object type, either b1000 (regular), b1010 (symlink), b1110 (gitlink)."""

    mode_perms = None
    """The object permissions, an integer."""

    uid = None
    """User ID of owner"""

    gid = None
    """Group ID of owner"""

    size = None
    """Size of this object, in bytes"""

    obj = None
    """The object's hash as a hex string"""

    flag_assume_valid = None
    flag_extended = None
    flag_stage = None
    flag_name_length = None
    """Length of the name if < 0xFFF (yes, three Fs), -1 otherwise"""

    name = None
