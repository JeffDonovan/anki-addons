# -*- mode: python; coding: utf-8 -*-
#
# Copyright © 2012 Roland Sieker, ospalh@gmail.com
# Inspiration and source of the URL: Tymon Warecki
#
# License: GNU AGPL, version 3 or later; http://www.gnu.org/copyleft/agpl.html


'''
Download pronunciations from GoogleTTS
'''

import os
import urllib
import urllib2


from .blacklist import get_hash
from .exists import free_media_name
from .language import default_audio_language_code

download_file_extension = u'.mp3'

url_gtts = 'http://translate.google.com/translate_tts?'

user_agent_string = 'Mozilla/5.0'


def get_word_from_google(source, language=None):
    if not source:
        raise ValueError('Nothing to download')
    get_url = build_query_url(source, language)
    # This may throw an exception
    request = urllib2.Request(get_url)
    request.add_header('User-agent', user_agent_string)
    response = urllib2.urlopen(request)
    if 200 != response.code:
        raise ValueError(str(response.code) + ': ' + response.msg)
    extras = dict(source='GoogleTTS')
    audio_file_name = free_media_name(source, download_file_extension)
    audio_file = open(audio_file_name, 'wb')
    audio_file.write(response.read())
    audio_file.close()
    try:
        file_hash = get_hash(audio_file.name)
    except ValueError:
        os.remove(audio_file_name)
        raise
    return audio_file_name, file_hash, extras


def build_query_url(source, language=None):
        qdict = {}
        if not language:
            language = default_audio_language_code
        qdict['tl'] = language.encode('utf-8')
        qdict['q'] = source.encode('utf-8')
        return url_gtts + urllib.urlencode(qdict)
