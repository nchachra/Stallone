"""Utilities for Stallone.
"""

import os
import random
import shutil
import string
import subprocess
import sys

import config
import crawlglobs

def cleanup(logger):
    """Does a final cleanup. Stops Xvfb and deletes the directory with all 
    firefox templates. 
    """
    if crawlglobs.display is not None:
        logger.info("Stopping XVFB")
        crawlglobs.display.stop()
    profile_dir = os.path.join(crawlglobs.tmp_dir, config.PROFILE_DIR)
    if os.path.isdir(profile_dir):
        logger.debug("Deleting profiles in temp")
        shutil.rmtree(profile_dir)

def default_tmp_location(size=6, chars=string.ascii_letters + string.digits):
    """If a default tmp location for this execution doesn't exist, create and
    return it.
    """
    print "Setting up a tmp directory"
    if crawlglobs.tmp_dir:
        return crawlglobs.tmp_dir
    while True:
        path = "/tmp/stallone_" + ''.join(random.choice(chars) 
                                                        for i in range(size))
        if not os.path.exists(path):
            crawlglobs.tmp_dir = path
            break
    return path

def installed(process_name, logger):
    """Checks if a package is installed. If not, it prints a message and exits.
    """
    devnull = open(os.devnull, 'w')
    retval = subprocess.Popen(['dpkg', '-s', process_name],
                              stdout=devnull,
                              stderr=subprocess.PIPE).communicate()
    devnull.close()
    if retval[1]:
        logger.critical("Please install %s " % process_name)
        sys.exit(1)