#
#  Specific testing data structures 
#

#
#  Multi Dimension Lists
#

two_d_list = [
    [ 1,  2,  3,  4,  5,  6,  7,  8],
    [11, 12, 13, 14, 15, 16, 17, 18],
    [21, 22, 23, 24, 25, 26, 27, 28],
    [31, 32, 33, 34, 35, 36, 37, 38],
]

three_d_list = [
    [
        [  1,  2,  3,  4,  5],
        [ 11, 12, 13, 14, 15],
        [ 21, 22, 23, 24, 25],
        [ 31, 32, 33, 34, 35]
    ],
    [
        [ 41, 42, 43, 44, 45],
        [ 51, 52, 53, 54, 55],
        [ 61, 62, 63, 64, 65],
        [ 71, 72, 73, 74, 75]
    ],
    [
        [  81,  82,  83,  84,  85],
        [  91,  92,  93,  94,  95],
        [ 101, 102, 103, 104, 105],
        [ 111, 112, 113, 114, 115]
    ]
]

#
#  Multi-Dimension Dictionaries
#
two_d_dict = {
    'zero': {
        "zero_zero":  0x00,
        "zero_one":   0x01,
        "zero_two":   0x02,
        "zero_three": 0x03,
        "zero_four":  0x04
    },
    'one': {
        "one_zero":  0x10,
        "one_one":   0x11,
        "one_two":   0x12,
        "one_three": 0x13,
        "one_four":  0x14
    },
    'two': {
        "two_zero":  0x20,
        "two_one":   0x21,
        "two_two":   0x22,
        "two_three": 0x23,
        "two_four":  0x24
    },
    'three': {
        "three_zero":  0x30,
        "three_one":   0x31,
        "three_two":   0x32,
        "three_three": 0x33,
        "three_four":  0x34
    }
}

three_d_dict = {
    'zero': {
        'zero_zero': {
            'zero_zero_zero':  0x000,
            'zero_zero_one':   0x001,
            'zero_zero_two':   0x002,
            'zero_zero_three': 0x003,
        },
        'zero_one': {
            'zero_one_zero':  0x010,
            'zero_one_one':   0x011,
            'zero_one_two':   0x012,
            'zero_one_three': 0x013,
        },
        'zero_two': {
            'zero_two_zero':  0x020,
            'zero_two_one':   0x021,
            'zero_two_two':   0x022,
            'zero_two_three': 0x023,
        }
    },
    'one': {
        'one_zero': {
            'one_zero_zero':  0x100,
            'one_zero_one':   0x101,
            'one_zero_two':   0x102,
            'one_zero_three': 0x103,
        },
        'one_one': {
            'one_one_zero':  0x110,
            'one_one_one':   0x111,
            'one_one_two':   0x112,
            'one_one_three': 0x113,
        },
        'one_two': {
            'one_two_zero':  0x120,
            'one_two_one':   0x121,
            'one_two_two':   0x122,
            'one_two_three': 0x123,
        }
    },
    'two': {
        'two_zero': {
            'two_zero_zero':  0x200,
            'two_zero_one':   0x201,
            'two_zero_two':   0x202,
            'two_zero_three': 0x203,
        },
        'two_one': {
            'two_one_zero':  0x210,
            'two_one_one':   0x211,
            'two_one_two':   0x212,
            'two_one_three': 0x213,
        },
        'two_two': {
            'two_two_zero':  0x220,
            'two_two_one':   0x221,
            'two_two_two':   0x222,
            'two_two_three': 0x223,
        }
    },
    'three': {
        'three_zero': {
            'three_zero_zero':  0x300,
            'three_zero_one':   0x301,
            'three_zero_two':   0x302,
            'three_zero_three': 0x303,
        },
        'three_one': {
            'three_one_zero':  0x310,
            'three_one_one':   0x311,
            'three_one_two':   0x312,
            'three_one_three': 0x313,
        },
        'three_two': {
            'three_two_zero':  0x320,
            'three_two_one':   0x321,
            'three_two_two':   0x322,
            'three_two_three': 0x323,
        }
    }
}

#
#  Opposites
#

list_of_dicts = [
    {
        'zero':  0x00,
        'one':   0x01,
        'two':   0x02,
        'three': 0x03,
        'four':  0x04,
    },
    {
        'zero':  0x10,
        'one':   0x11,
        'two':   0x12,
        'three': 0x13,
        'four':  0x14,
    },
    {
        'zero':  0x20,
        'one':   0x21,
        'two':   0x22,
        'three': 0x23,
        'four':  0x24,
    },
    {
        'zero':  0x30,
        'one':   0x31,
        'two':   0x32,
        'three': 0x33,
        'four':  0x34,
    }
]

dict_of_lists = {
    'zero':  [ 0x00, 0x01, 0x02, 0x03, 0x04 ],
    'one':   [ 0x10, 0x11, 0x12, 0x13, 0x14 ],
    'two':   [ 0x20, 0x21, 0x22, 0x23, 0x24 ],
    'three': [ 0x30, 0x31, 0x32, 0x33, 0x34 ],
    'four':  [ 0x40, 0x41, 0x42, 0x43, 0x44 ],
}
