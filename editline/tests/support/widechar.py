#!/usr/bin/env python3
#
#  UTF-8 testing for editline/libedit
#
#  Reference: https://www.w3.org/2001/06/utf-8-test/UTF-8-demo.html
#

class Russian(object):

    # basic attributes
    бег		= 'run'
    играть	= 'play'
    Прыгать	= 'jump'
    рулон	= 'roll'
    пропускать	= 'skip'
    падение	= 'dip'
    следовать	= 'follow'
    вести	= 'lead'
    запах	= 'smell'

    # dictionary keys
    actions = {
        'бег': 1,
        'играть': 1,
        'Прыгать': 1,
        'рулон': 1,
        'пропускать': 1,
        'падение': 1,
        'следовать': 1,
        'вести': 1,
        'запах': 1
    }

class Greek(object):

    # basic attributes
    τρέξιμο	=	'run'
    παίζω	=	'play'
    άλμα	=	'jump'
    ρολό	=	'roll'
    παραλείπω	=	'skip'
    βουτιά	=	'dip'
    ακολουθηστε	=	'follow'
    οδηγω	=	'lead'
    μυρωδιά	=	'smell'

    # dictionary keys
    actions = {
        'τρέξιμο': 1,
        'παίζω': 1,
        'άλμα': 1,
        'ρολό': 1,
        'παραλείπω': 1,
        'βουτιά': 1,
        'ακολουθηστε': 1,
        'οδηγω': 1,
        'μυρωδιά': 1
    }

class Tamil(object):

    # basic attributes
    ரன்		=	'run'
    விளையாட	=	'play'
    குதிக்க	=	'jump'
    ரோல்	=	'roll'
    தவிர்க்க	=	'skip'
    டிப்		=	'dip'
    பின்பற்ற	=	'follow'
    வழிவகுக்கும்	=	'lead'
    வாசனை	=	'smell'

    # dictionary keys
    actions = {
        'ரன்': 1,
        'விளையாட': 1,
        'குதிக்க': 1,
        'ரோல்': 1,
        'தவிர்க்க': 1,
        'டிப்': 1,
        'பின்பற்ற': 1,
        'வழிவகுக்கும்': 1,
        'வாசனை': 1
    }

class Korean(object):

    # basic attributes
    운영	=	'run'
    놀이	=	'play'
    도약	=	'jump'
    롤		=	'roll'
    버킷	=	'skip'
    담그다	=	'dip'
    따르다	=	'follow'
    리드	=	'lead'
    냄새	=	'smell'

    # dictionary keys
    actions = {
        '운영': 1,
        '놀이': 1,
        '도약': 1,
        '롤': 1,
        '버킷': 1,
        '담그다': 1,
        '따르다': 1,
        '리드': 1,
        '냄새': 1
    }
