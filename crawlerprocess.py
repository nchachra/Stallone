import multiprocessing as mp
import os
import Queue
import signal
import traceback

try:
    import re2 as re
except ImportError:
    import re

from browser import Browser
import config
import crawlglobs
import mplogging
from proxy import Proxy
"""Processes that do the actual instrumentation and visits through browser.
Any new browser addition, or new method of crawling will need to subclass
CrawlerProcess and implement the empty functions.


Author: nchachra@cs.ucsd.edu
"""

class CrawlerProcess:
    '''Base crawler thread. Run() should be used by all base classes. The 
    other functions need to be overridden. 
    '''
    def __init__(self, restart, browser, ext_port, proxy_file, proxy_scheme, 
                 log_q):
        self.restart = restart
        self.browser_name = browser
        self.browser_inst = None
        if self.browser_name == 'Firefox':
            self.__class__ = FirefoxCrawlerProcess
            # May want to just ignore ext_port for other browsers.
            self.ext_port = ext_port 
        self.logger = mplogging.setupSubProcessLogger("Crawler", log_q)
        self.proxy = Proxy(proxy_file, proxy_scheme, self.logger)
        # To make sure the process doesn't take more than 15 min to complete
        #     a single visit. Kill the process if it does.
        signal.signal(signal.SIGALRM, self.alarm_handler)
        # We would like to restart browser every so many visits.
        self.num_visits = 0


    def start_browser(self):
        pass
    
    def grab(self, url, setup, features):
        pass
    
    def alarm_handler(self, signum, frame):
        """Called when the alarm goes off. There's only 1 alarm per process.
        """
        self.logger.critical(("Alarm went off for process: %s \n. The process"+
                             " took longer than 15 min for a single visit." +
                             "This subprocess is exiting.") % 
                             mp.current_process.name())
        self.req_q.task_done()
        mp.current_process.terminate()

    def run(self, req_q, res_q):
        """If the request_q has jobs, extract one, and process it. Process
        stops looping and exits when it encounters the special item "CLEANUP"
        on request q.
        """
        self.req_q = req_q
        self.res_q = res_q
        signal.alarm(config.ALARM_TIME)
        while True:
            # One visit takes place per loop. None of the visits should ever
            #     take more than 15 minutes. Something has to have gone wrong
            #     at that point. Raise an alarm, call req_q.task_done(), put
            #     some error on res_q and raise exception (which kills this
            #     process)
            try:
                task = req_q.get()
                print "task: ", task
                if task == 'CLEANUP':
                    self.logger.info("Crawler preparing to exit.Found cleanup")
                    req_q.put(task)
                    req_q.task_done()
                    if self.browser_inst:
                        self.browser_inst.cleanup()
                    break
                (job_id, job) = task
                url = job['url']
                if job.has_key('setup'):
                    setup = job['setup']
                else:
                    setup = None
                if job.has_key('features'):
                    features = job['features']
                else:
                    self.logger.error(("No feature requested for id: %s") 
                                      % job_id)
                if job.has_key('actions'):
                    actions = job['actions']
                else:
                    actions = {}
            except Queue.Empty:
                self.logger.debug("Request q is empty. Joining.")
                if self.browser_inst:
                    self.browser_inst.cleanup()
                break
            self.logger.info("Visiting %s for features %s " % (url, features))
            print "Got item: ", url, " ", features
            if (self.browser_inst and 
                    (self.browser_inst.process.poll() is not None or 
                     self.restart or
                     self.num_visits > config.MAX_BROWSER_VISITS_PER_RESTART)
                ):
                    self.browser_inst.cleanup()
                    self.browser_inst = None
                    self.num_visits = 0
            if self.browser_inst is None and hasattr(self, "start_browser"):
                if not self.start_browser():
                    req_q.task_done()
                    req_q.put(task)
                    break
            result_list = None
            try:
                result_list = self.grab(job_id, url, setup, features, actions)
            except Exception, e:
                self.logger.error(("Error in grabbing URL %s. " +
                                   "Exception: %s") 
                                  % (url, traceback.print_exc()))
            if result_list: 
                res_q.put(result_list)
            req_q.task_done()
            self.num_visits += 1
            # Clear alarm
            signal.alarm(0)


class FirefoxCrawlerProcess(CrawlerProcess):
    """Class controlling Firefox based processes. Firefox needs extension
    support"""
    def start_browser(self):
        """The crawler process tries to start browser using this function.
        Presumably every browser needs hooks before starting. Firefox needs
        a profile and extension, set-up by this function.
        """
        self.browser_inst = Browser(self.browser_name, self.logger)
        self.extension_inst = self.browser_inst.start(self.ext_port)
        return self.extension_inst
    
    def _visit_setup(self, setup):
        """Based on the properties in setup, readies the browser and 
        extension to do a visit.
        """
        if setup and setup.has_key('ff_prefs'):
            for pref in setup['ff_prefs']:
                self.extension_inst.set_pref(pref[0], pref[1], pref[2])
        if setup and setup.has_key('headers'):
            for (header, value) in setup['headers'].iteritems():
                self.extension_inst.set_header(header, value)
        if setup and setup.has_key('proxy'):
            self.extension_inst.set_proxy(setup['proxy'][0], 
                                          setup['proxy'][1],
                                          setup['proxy'][2])
        else:
            proxy = self.proxy.next_proxy()
            if proxy:
                self.extension_inst.set_proxy(proxy[0], proxy[1], proxy[2])
            
    def _feature_destination(self, file_ext, features, feature, glob_dir):
        """Returns a tuple of (directory, fname) where a feature will be 
        saved. Returns fname as empty string in which case the file is to be 
        named with its md5.
        """
        fname = ""
        path = ""
        self.logger.debug(("Finding path and filename for %s, given args" +
                           "file_ext: %s, features: %s, glob-dir: %s") 
                          % (feature, file_ext, features, glob_dir))
        if (isinstance(features, dict) and features.has_key(feature) and 
            glob_dir and features[feature]):
                # If the feature path is absolute, ignore glob parameter.
                if os.path.isabs(features[feature]):
                    path = features[feature]
                elif glob_dir:
                    path = os.path.join(glob_dir, features[feature])
        elif glob_dir:
            path = os.path.abspath(glob_dir)
        else:
            self.logger.error(("Error finding a valid location for saving " +
                              "feature %s with arguments extension: %s " +
                              " features dictionary: %s, " +
                              "global dir option: %s") 
                              % (feature, file_ext, features, glob_dir))
            return ("", "")
        # The path found above could be full path with fname or just the 
        #    directory.
        file_ext_len = len(file_ext)
        if len(path) > file_ext_len and path[-file_ext_len:] == file_ext:
            # The path includes filename. Get the filename out and create 
            #    the rest of dir
            fname = os.path.basename(path)
            path = os.path.dirname(path) + '/'
        try:
            if path and not os.path.exists(path):
                    os.makedirs(path)
        except OSError, e:
            self.logger.error(("Excepting while creating directory for \n" +
                               "for feature %s. Maybe harmless if the dir \n" +
                               "already exists. Exception: %s") 
                              % (feature, traceback.print_exc()))
        self.logger.debug(("Returning path: %s, filename: %s for feature %s")
                          % (path, fname, feature))
        return (path, fname)  

    def grab(self, req_id, url, setup, features, actions):
        """Does the actual work of visiting a page and extracting information
        from it. Setup is done before loading a page, and features are 
        extracted after the page is loaded. Returns a list of 
        [(fname.json, dict)] tuples. The dictionary will be written in file 
        called fname.json.
        """
        # Result_list contains tuples of (fname, dict) where dict will be 
        #    written in json format to fname.
        result_list = []
        visit = []
        # Set up pre-visit features
        self.extension_inst.reset()
        self._visit_setup(setup)
        # Visit URL
        self.extension_inst.set_url(url)
        self.extension_inst.wait_for_load(5, config.PAGE_TIMEOUT)
        if not self.extension_inst.page_loaded():
            visit.append({'url': url, 'status_code': config.PAGE_TIMEOUT_ST})
        if self.extension_inst.page_error():
            visit.append({'url': url, 'status_code': config.FIREFOX_ERR_ST})
        print self.extension_inst.headers()
        html = self.extension_inst.html()
        
        all_flag = False
        dom = None
        screenshot = None
        dom_fname = ''
        img_fname = ''
        eval_result_l = []
        tags = {}
        
        if features == "all":
            all_flag = True
        if all_flag or features.has_key('dom'):
            (dom_path, dom_fname) = self._feature_destination('html', 
                                                          features,
                                                          'dom',
                                                          crawlglobs.dom_dir)
            if dom_path:
                dom = self.extension_inst.html_file(dom_path, dom_fname)
            
        if all_flag or features.has_key('screenshot'):
            (img_path, img_fname) = self._feature_destination('png', features, 
                                                          'screenshot',
                                                          crawlglobs.img_dir)
            if img_path:
                screenshot = self.extension_inst.screenshot_file(img_path, 
                                                                 img_fname)

        if actions.has_key('eval'):
            # Eval is a list of javascript snippets. Run each one.
            for exp in actions['eval']:
                eval_result_l.append(self.extension_inst.eval_js(exp))
                
        # Tagging
        if crawlglobs.tags_l:
            # We have to tag.
            for (tag_name, attrs) in crawlglobs.tags_l:
                threshold = attrs["threshold"]
                # Keep track of how many matched
                match_count = 0
                match_groups = []
                for regex in attrs["regexes"]:
                    se = regex.search(html)
                    if se: 
                        match_count += 1
                    match_groups.append(se.groups())
                    print match_groups
                if match_count >= threshold:
                    tags[tag_name] = match_groups
                        
        if all_flag or features.has_key("visitchain"):
            (vc_path, vc_fname) = self._feature_destination(
                                            'json', features, 'visitchain', 
                                            crawlglobs.visit_chain_dir)
            # Unlike screenshot and dom, we default to naming the visit chain
            #    file with the job id.
            if not vc_fname:
                vc_fname = req_id + ".json"
            if vc_path:
                vc_fname = os.path.join(vc_path, vc_fname)
                
            headers = self.extension_inst.headers()
            redirects = self.extension_inst.redirects()
            response_codes =  self.extension_inst.response_codes()
            if not response_codes:
                response_codes= {url: 'UNK'} 
            if response_codes != None and len(redirects) != 0:
                for page in redirects:
                    if page == 'about:blank': 
                        continue
                    webpage = {'url': page}
                    if page in response_codes.keys():
                        webpage['status_code'] = response_codes[page]
                    elif page + '/' in response_codes.keys():
                        webpage['status_code'] = response_codes[page + '/']
                    if headers is not None and headers.has_key(page):
                        webpage['headers'] = headers[page]
                    if headers is not None and headers.has_key(page+ '/'):
                        webpage['headers'] = headers[page + '/']
                        # Our tinyproxy is configured to return the server addr
                        #    in a special header. This shouldn't hurt anyone not
                        #    using the modified tinyproxy
                    if (webpage.has_key('headers') and 
                        webpage['headers'].has_key('X-Server-Address')):
                            webpage['server_addr'] = (
                                webpage['headers']['X-Server-Address'])
                    visit.append(webpage)
            if visit:
                visit[-1]['dom'] = dom
                visit[-1]['screenshot'] = screenshot
                if eval_result_l:
                    visit[-1]['eval_results'] = eval_result_l
                if tags:
                    visit[-1]['tags'] = tags
                result_list.append((vc_fname, visit))
            return result_list
        else:
            # Check if the fname for dom and screenshot was provided. If not,
            #    the files will be saved as md5 and visit chain is not being
            #    retrieved, so file mapping to id will be lost forever.
            if ((features.has_key("screenshot") and not img_fname) or 
                (features.has_key("dom") and not dom_fname)):
                self.logger.error(("Since visit chain file argument is " +
                                   "missing, the mapping to dom and/or " +
                                   "screenshot will be lost forever!"))
            return None
