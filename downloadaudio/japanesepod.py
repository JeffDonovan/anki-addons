# -*- mode: python; coding: utf-8 -*-
#
# Copyright © 2012 Roland Sieker, ospalh@gmail.com
# Inspiration and source of the URL: Tymon Warecki
#
# License: AGNU GPL, version 3 or later; http://www.gnu.org/copyleft/agpl.html


'''
Download Japanese pronunciations from Japanesepod
'''


import os
import urllib
import urllib2


from .blacklist import get_hash
from .exists import free_media_name

download_file_extension = u'.mp3'

url_jdict = \
    'http://assets.languagepod101.com/dictionary/japanese/audiomp3.php?'


def get_word_from_jpod(kanji, kana):
    """
    Download audio from kanji and kana from japanesepod.
    """
    base_name = build_base_name(kanji, kana)
    get_url = build_query_url(kanji, kana)
    # This may throw an exception
    request = urllib2.Request(get_url)
    response = urllib2.urlopen(request)
    if 200 != response.code:
        raise ValueError(str(response.code) + ': ' + response.msg)
    extras = dict(source='Japanesepod')
    audio_file_name = free_media_name(base_name, download_file_extension)
    with open(audio_file_name, 'wb') as audio_file:
        audio_file.write(response.read())
    try:
        file_hash = get_hash(audio_file.name)
    except ValueError:
        os.remove(audio_file_name)
        raise
    return audio_file_name, file_hash, extras


def build_query_url(kanji, kana):
        qdict = {}
        if kanji:
            qdict['kanji'] = kanji.encode('utf-8')
        if kana:
            qdict['kana'] = kana.encode('utf-8')
        return url_jdict + urllib.urlencode(qdict)


def build_base_name(kanji, kana):
    """Base of the file name to come."""
    base_name = kanji
    if kana:
        base_name += u'_' + kana
    return base_name
