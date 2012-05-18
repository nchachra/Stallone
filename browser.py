'''Provides browser controls for starting and stopping. Browser is the base 
class.
'''

import config
import os
import shutil
import subprocess

import crawlglobs
import extension


class Browser:
    '''Template for making browser subclasses'''
    def __init__(self, name, logger):
        self.process = None
        self.logger = logger
        if name == 'Firefox':
            self.__class__ = Firefox

    def start(self):
        '''Starts the browser.'''
        pass

    def stop(self):
        '''Stops the browser.'''
        if self.process and self.process.poll() is None:
            self.process.kill()

class Firefox(Browser):
    '''Firefox process controls.'''
    def start(self, extension_port):
        '''Starts Firefox at extension_port. If start up fails, it cleans up 
        and returns False, otherwise returns the associated extension 
        instance.
        '''
        profile_path = os.path.join(crawlglobs.tmp_dir, config.PROFILE_DIR, 
                                    "ff_" + str(extension_port))
        self.profile(profile_path, extension_port)
        if not os.path.isdir(self.profile_dir):
            raise Exception('No profile')
        self.process = subprocess.Popen(['firefox', '-no-remote', '-profile',
                                        self.profile_dir])
        self.logger.debug("Starting extention.")
        ext = extension.Extension(self.logger, port=extension_port)
        if not ext.reset():
            self.logger.error(("Extension could not be restarted for " +
                               "Firefox instance at port %s. \n Cleaning up " +
                               "that instance.") % extension_port)
            self.cleanup()
            return False
        return ext

    def profile(self, dir_name, extension_port):
        '''Create a firefox profile with dir_name if there isn't one already.
        It uses the extension port to change the server port in extension.
        '''
        self.logger.debug("Creating FF profile if there isn't one already.")
        if not hasattr(Firefox, 'profile_dir'):
            self.profile_dir = None
        if self.profile_dir is None: 
            if not os.path.isdir(dir_name):
                # Since there are read-only .svn files, use -f
                self.logger.info("Creating Firefox profile.")
                # Exclude .svn files when creating profile. The .svn files
                #     are write protected, and aren't deleted by the removedir
                #     call.
                shutil.copytree(os.getcwd() + '/firefox_template',
                                dir_name, 
                                ignore=shutil.ignore_patterns('*.svn'))
                self.profile_dir = dir_name
                self.logger.debug("Created profile at %s" % dir_name)
                # TODO: Replace the server port with extension_port.Ideally, this
                # should be a custom pref or some such.
                fp = open((self.profile_dir + 
                           '/extensions/trajlogger@cs.ucsd.edu/chrome/' +
                           'content/commandsocket.js'), 'r')
                orig_contents = fp.read()
                fp.close()
                new_contents = orig_contents.replace("7055", 
                                                     str(extension_port))
                fp = open((self.profile_dir + 
                           '/extensions/trajlogger@cs.ucsd.edu/chrome/' +
                           'content/commandsocket.js'), 'w')
                fp.write(new_contents)
                fp.close()
                # File's not very big. Read all contents into memory.
            else:
                self.profile_dir = dir_name
        else:
            self.logger.debug("Profile already exists.")
        
    def cleanup(self):
        '''Kills Firefox, and removes its template directory.'''
        self.logger.info("Stopping browser")
        self.stop()
        self.logger.info("Removing Firefox profile")
        if self.profile_dir and os.path.isdir(self.profile_dir):
            shutil.rmtree(self.profile_dir)
