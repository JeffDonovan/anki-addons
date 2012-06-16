# -*- mode: python ; coding: utf-8 -*-
# Copyright © 2012 Roland Sieker
# Based on deurl-files.py by  Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#

"""Rename files that have MD5ish names

Rename files with Anki <1.2-ish MD5 names with names derived from the
note content.

"""

import re
import os

import romaji
import kana_kanji
from progress import progress

from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, showText, askUser
from anki.utils import ids2str, stripHTML

name_source_fields = ['Reading', 'Expression', 'Kanji' ]

## Try to separate kanji and kana from the string to use. Convert
## something like 「お 父[とう]さん」 into “お父さん_おとうさん”. This
## should be harmless for most non-Japanese data. If your data uses
## square brackets for other purposes, consider setting this to False.
split_reading = True
# split_reading = False

## When split_reading is True, use a reading, even when the katakana
## version of the reading is identical to the expression.
reading_for_katakana = False
# reading_for_katakana = True

## To avoid too long syncs of data when only the names have changed,
## provide a way to rename just the files on another computer with a
## batch or shell script file.
batch_name = 'rename_hash-name_files.bat'
script_name = 'rename_hash-name_files.sh'


hash_name_pat = '(?:\[sound:|src *= *")([a-z0-9]{32})'\
    '(\.[a-zA-Z0-9]{1,5})(?:]|")'



def _exists_lc(path, name):
    """
    Test if file name clashes with name of extant file.
    
    On Windows and Mac OS X, simply check if the file exists.
    On (other) POSIX systems, check if the name clashes with an
    existing file's name that is the same or differs only in
    capitalization.
    
    """
    # The point is tha like this syncing from Linux to
    # Macs/Windows should work savely.
    if isWin or isMac:
        return os.path.exist(os.path.join(path, name))
    # We actually return a list with the offending file names. But
    # doing simple checks like if _exists_lc(...): will work as
    # expected. If this is not acceptable, a 'not not' can be
    # added before the opening '[' to return a Boolean.
    return [fname for fname in os.listdir(path)
            if fname.lower() == name.lower()]



def katakanaize(hiragana):
    """
    Return katakana
    
    Transform a hiragana string to katakana through the circuitous
    route of converting it to rōmaji, then to uppercase, than to
    kana again.
    
    """
    return romaji.kana(romaji.roma(hiragana).upper())


def mangle_reading(nbn):
    """Try to separate Japanese kanji and reading out of a string """
    # Variable names and comments here assume the text is
    # Japanese. When it is not, nothing bad should happen.

    # TODO
    kana = kana_kanji.kana(nbn)
    kanji = kana_kanji.kanji(nbn)
    if kana and not kanji:
        # Quick save
        kanji = kana
    # Now the tricky bit: decide when to use the split values.
    if kana and kanji and kanji != kana:
        if reading_for_katakana or \
                katakanaize(kanji) != katakanaize(kana):
            return kanji + u'_' + kana
        else:
            return kanji
    # Still here: i guess don’t use the split after all.
    return nbn



def new_name_base(old_base, note):
    """
    Get the base of a new file name
    
    Look at the information on the card and use the data to create
    a base new name.
    """
    def find_field(note, old_base):
        """
        Compare the  candidate fields and the notes fields.
            
        Look through the two lists, name_source_fields and the
        note’s items, to find the field we should use. Put in
        function so we can break out of nested loops.
        
        """
        for sf in name_source_fields:
            for name, value in note.items():
                if name == sf:
                    value = stripHTML(value)
                    # Check here if we have something left. So we
                    # can keep on looking when we have a candidate
                    # field but it’s empty.
                    if value and not old_base in value:
                        # Avoid the field we got the name from
                        # (i.e. the audio, image field).
                        return name, value
        # We got here: no match.
        return None, None

    # Several tries. First, look through the list.
    name, value = find_field(note, old_base)
    if value and not old_base in value:
        return value
    # Still here, next try the sort field.
    name, value = note.items()[mw.col.models.sortIdx(note.model())]
    value = stripHTML(value)
    if value and not old_base in value:
        return value
    for name, value in note.items():
        # Last resort: go through the fields and grab the first
        # non-empty one, except the one with the file.
        value = stripHTML(value)
        if value and not old_base in value:
            return value
    # Well, shoot. Looks like the only field with anything interesting
    # is the one with the file. (Almost reasonable. One-side cards to
    # just listen to something and decide without further info if you
    # recoginze that.)
    raise ValueError(u'No data for new name found')




class Dehashilator(object):

    """Class to rename files that have MD5ish names

    Rename files with Anki <1.2-ish MD5 names with names derived from the
    note content.
    
    """

    def __init__(self):
        # Dictionary to keep track of the standard cases where we have
        # to move the file and change the info in the field.
        self.move_rename_files = {}
        # Cases where one file is referenced a second time. Here we
        # have to just change the field content.
        self.just_fix_fields = {}
        # Test string. Information shown to the usser of what we want
        # to do.
        self.test_string = u''
        self.media_list = []
        
    def new_name(self, old_base, old_end, note):
        """
        Get a file name for a new 

        Make sure the desired name doesn’t clash with other names.
        Return a file name that doesn’t clash with existing files,
        doing parts by hand to avoid issues with case-sensitive and
        non-case-sensitive file systems.
        
        This means we also have to add a version of the name to a
        list, so the next card won't use this name.
        """
        nbn = new_name_base(old_base, note)
        if split_reading:
            nbn = mangle_reading(nbn)
        # remove any dangerous characters
        # First replace [,] with (, )
        nbn = nbn.replace('[', '(')
        nbn = nbn.replace(']', ')')
        # Then delete a string of other characters
        nbn = re.sub(r"[][<>:/\\&?\"\|]", "", nbn)

        # Now we should check for duplicate names.

        self.media_list.append((nbn + old_end).lower())
        return nbn + old_end

    def build_media_list(self):
        """
        Fill self.media_list.

        Fill self.media_list with lower-case versions of all media
        file names. The list is used so we avoid all problems with
        duplicate names after a sync.

        """
        pass

    def dehashilate(self):
        """Go through the collection and clean up MD5-ish names

        Search the cards for sounds or images with file names that
        look like MD5 hashes, rename the files and change the notes.
        
        """
        self.build_media_list()
        nids = mw.col.db.list("select id from notes")
        for nid in progress(nids, "Dehashilating", "This is all wrong!"):
            n = mw.col.getNote(nid)
            for (name, value) in n.items():
                rs =  re.search(hash_name_pat, value)
                if None == rs:
                    continue
                old_name_ = '{0}.{1}'.format(rs.group(1), rs.group(2))
                try:
                    (other_nid, other_old_name, other_new_name)  = self.move_rename_files[rs.group(1)]
                except KeyError:
                    other_nid = None
                if other_nid:
                    self.just_fix_fields[rs.group(1)] = (nid, other_old_name, other_new_name)
                    continue
                new_name_ = self.new_name(rs.group(1), rs.group(2), n)
                self.test_string += u'{0} → {1}\n'.format(old_name_, new_name_)
                self.move_rename_files[rs.group(1)] = (nid, old_name_, new_name_)
        showText(self.test_string)

