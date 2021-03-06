__copyright__ = "Copyright 2016, Netflix, Inc."
__license__ = "Apache, Version 2.0"

import sys
import os

def get_stdout_logger():
    import logging
    logger = logging.getLogger()
    handler = logging.StreamHandler(stream=sys.stdout)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger

def close_logger(logger):
    for handler in logger.handlers:
        handler.close()
        logger.removeHandler(handler)

def get_file_name_without_extension(path):
    """

    >>> get_file_name_without_extension('yuv/src01_hrc01.yuv')
    'src01_hrc01'
    >>> get_file_name_without_extension('yuv/src01_hrc01')
    'src01_hrc01'
    >>> get_file_name_without_extension('abc/xyz/src01_hrc01.yuv')
    'src01_hrc01'

    """
    return os.path.splitext(path.split("/")[-1])[0]

def get_file_name_with_extension(path):
    """

    >>> get_file_name_with_extension('yuv/src01_hrc01.yuv')
    'src01_hrc01.yuv'
    >>> get_file_name_with_extension('src01_hrc01.yuv')
    'src01_hrc01.yuv'
    >>> get_file_name_with_extension('abc/xyz/src01_hrc01.yuv')
    'src01_hrc01.yuv'

    """
    return path.split("/")[-1]

def get_dir_without_last_slash(path):
    """

    >>> get_dir_without_last_slash('abc/src01_hrc01.yuv')
    'abc'
    >>> get_dir_without_last_slash('src01_hrc01.yuv')
    ''
    >>> get_dir_without_last_slash('abc/xyz/src01_hrc01.yuv')
    'abc/xyz'

    """
    return "/".join(path.split("/")[:-1])

def make_parent_dirs_if_nonexist(path):
    dst_dir = get_dir_without_last_slash(path)
    # create dir if not exist yet
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)

def delete_dir_if_exists(dir):
    if os.path.isdir(dir):
        os.rmdir(dir)

def get_unique_str_from_recursive_dict(d):
    """
    String representation with sorted keys and values
    >>> get_unique_str_from_recursive_dict({'a':1, 'b':2, 'c':{'x':'0', 'y':'1'}})
    '{"a": 1, "b": 2, "c": {"x": "0", "y": "1"}}'
    >>> get_unique_str_from_recursive_dict({'a':1, 'c':2, 'b':{'y':'1', 'x':'0', }})
    '{"a": 1, "b": {"x": "0", "y": "1"}, "c": 2}'
    """
    from collections import OrderedDict
    import json
    def to_ordered_dict_recursively(d):
        if isinstance(d, dict):
            return OrderedDict(map(
                                    lambda (k,v): (to_ordered_dict_recursively(k),
                                                   to_ordered_dict_recursively(v)),
                                    sorted(d.items())
                                   )
                              )
        else:
            return d
    return json.dumps(to_ordered_dict_recursively(d))

def indices(a, func):
    """
    Get indices of elements in an array which satisfies func
    >>> indices([1, 2, 3, 4], lambda x: x>2)
    [2, 3]
    >>> indices([1, 2, 3, 4], lambda x: x==2.5)
    []
    >>> indices([1, 2, 3, 4], lambda x: x>1 and x<=3)
    [1, 2]
    >>> indices([1, 2, 3, 4], lambda x: x in [2, 4])
    [1, 3]
    """
    return [i for (i, val) in enumerate(a) if func(val)]

def import_python_file(filepath):
    """
    Import a python file as a module.
    :param filepath:
    :return:
    """
    import imp
    filename = get_file_name_without_extension(filepath)
    ret = imp.load_source(filename, filepath)

    return ret

def make_absolute_path(path, current_dir):
    '''

    >>> make_absolute_path('abc/cde.fg', '/xyz/')
    '/xyz/abc/cde.fg'
    >>> make_absolute_path('/abc/cde.fg', '/xyz/')
    '/abc/cde.fg'

    '''
    if path[0] == '/':
        return path
    else:
        return current_dir + path

def empty_object():
    return type('', (), {})()

def get_cmd_option(argv, begin, end, option):
    '''

    >>> get_cmd_option(['a', 'b', 'c', '--xyz', '123'], 3, 5, '--xyz')
    '123'
    >>> get_cmd_option(['a', 'b', 'c', '--xyz', '123'], 0, 5, '--xyz')
    '123'
    >>> get_cmd_option(['a', 'b', 'c', '--xyz', '123'], 4, 5, '--xyz')
    >>> get_cmd_option(['a', 'b', 'c', '--xyz', '123'], 5, 5, '--xyz')
    >>> get_cmd_option(['a', 'b', 'c', '--xyz', '123'], 6, 5, '--xyz')
    >>> get_cmd_option(['a', 'b', 'c', '--xyz', '123'], 0, 5, 'a')
    'b'
    >>> get_cmd_option(['a', 'b', 'c', '--xyz', '123'], 0, 5, 'b')
    'c'

    '''
    itr = None
    for itr in range(begin, end):
        if argv[itr] == option:
            break
    if itr is not None and itr != end and (itr + 1) != end:
        return argv[itr + 1]
    return None

def cmd_option_exists(argv, begin, end, option):
    '''

    >>> cmd_option_exists(['a', 'b', 'c', 'd'], 2, 4, 'c')
    True
    >>> cmd_option_exists(['a', 'b', 'c', 'd'], 3, 4, 'c')
    False
    >>> cmd_option_exists(['a', 'b', 'c', 'd'], 3, 4, 'd')
    True
    >>> cmd_option_exists(['a', 'b', 'c', 'd'], 2, 4, 'a')
    False
    >>> cmd_option_exists(['a', 'b', 'c', 'd'], 2, 4, 'b')
    False

    '''
    found = False
    for itr in range(begin, end):
        if argv[itr] == option:
            found = True
            break
    return found

def index_and_value_of_min(l):
    '''

    >>> index_and_value_of_min([2, 0, 3])
    (1, 0)

    '''
    return min(enumerate(l), key=lambda x: x[1])

if __name__ == '__main__':
    import doctest
    doctest.testmod()


