"""
 Track versioning.

"""

VERSION_INFO = [ 2, 0, 0 ]

def version():
    """Return the version number of this module.

    Args:
        None

    Returns:
        String containing the major, minor, micro version number.

    """
    return '{}.{}.{}'.format(VERSION_INFO[0], VERSION_INFO[1], VERSION_INFO[2])
