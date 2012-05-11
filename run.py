"""Entry point for crawler.

Run as:
python run.py [arguments]

For documentation, see: 
python run.py -h 


Author: nchachra@cs.ucsd.edu
"""

# Standard
import logging
import logging.handlers
import multiprocessing as mp
import os
import simplejson as json
import subprocess
import sys
import time
import traceback

# Installed
try:
    import argparse
except ImportError:
    print ("Please install python-argparse module:\n" +
           "[sudo] apt-get install python-argparse")
    sys.exit(1)
try:
    from pyvirtualdisplay import Display
except ImportError:
    print ("Please install pyvirtualdisplay using: \n" +
           "[sudo] apt-get install python-setuptools \n" +
           "[sudo] pip install pyvirtualdisplay")
    sys.exit(1)
    
try:
    import re2 as re
except ImportError:
    print("re2 not found. Falling back on re. \n" +
          "re2 is significantly faster. To install, first install re2 \n" +
          "followed by pyre2 as follows: \n" +
          "hg clone https://re2.googlecode.com/hg re2 \n" +
          "cd re2 \n" +
          "make test \n" +
          "make install \n" +
          "make testinstall \n " +
          "\n" +
          "git clone git://github.com/axiak/pyre2.git \n" +
          "cd pyre2 \n" +
          "[sudo] python setup.py install")
    import re

# Stallone specific
import config
from crawlerprocess import CrawlerProcess
import crawlglobs
import mplogging
from qcontroller import FileQController
import utils

def setup_args():
    """Creates all the arguments for the code alongwith the defaults. Returns
    the parsed arguments for use.
    """
    # Get a default for log directory.
    default_log_dir = os.path.join(utils.default_tmp_location(), 
                                   config.LOG_DIR)
    description = ('This script instruments a browser to collect information' +
                    ' about a web page.')
    parser = argparse.ArgumentParser(
                        description=description, 
                        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-x', '--no-xvfb', action='store_true', 
            default=False,
            help='Give this option to turn XVFB (X Virtual Frame Buffer) \n' + 
                 'off. It is useful for debugging. XVFB is enabled by \n' +
                 'default. Crawler uses XVFB default screen 0 and display:99.')
    # Output Directories
    parser.add_argument('--screenshot-dir',
            help='Base directory for storing screenshots. The crawler \n' + 
                 'determines the directory and filename based on this \n' +
                 'option combined with the "screenshot" specification in \n' +
                 'visit request in the input file. \n' +
                 'Directory to save file in: \n' +
                 '------------------------- \n' +
                 'The optional --screenshot-dir argument specifies the \n' +
                 'base directory to store all the screenshots in. The path \n'+
                 'in input file is appended to this base dir path to form \n' +
                 'the full directory path. Any directories that do not \n' +
                 'already exist in the path will be automatically created. \n'+
                 'For example, if the crawler is started with: \n' +
                 '    python run.py --screenshot-dir /hdfs/pic \n' + 
                 'and a visit has entry: \n' +
                 '    "screenshot": "nchachra/recrawling/pic1.png" \n' +
                 'the file is stored as: \n' +
                 '     /hdfs/pic/nchachra/recrawling/pic1.png \n' +
                 'Alternatively, if --screenshot-dir argument is missing, \n' +
                 'the file is stored in the current directory as, \n' +
                 '    ./nchachra/recrawling/pic1.png \n' +
                 'If the visit specified the path as: \n' +
                 '    "screenshot": "/nchachra/recawling/pic1.png" \n' +
                 'and the --screenshot-dir argument is missing, the file \n' +
                 'is stored as /nchachra/recrawling/pic1.png \n' +
                 'If both the --screenshot-dir argument, and per visit \n' +
                 'screenshot file is missing: \n' +
                 '    "screenshot":"" \n' +
                 'the file is stored in the current directory. \n' +
                 'Filename to save file with: \n' +
                 '--------------------------- \n' +
                 'If the full-path formed above ends with ".png", the \n' +
                 'file is stored with the user-specified name. For example \n'+
                 'for the path /hdfs/pic/nchachra/recrawling/pic1.png, \n ' +
                 'the file is stored as: pic1.png. \n' +
                 'If the file extension is not ".png", the path is assumed \n'+
                 'to be all directories. For example, if the .png is \n' +
                 'omitted above: /hdfs/pic/nchachra/recrawling/pic1, the \n'+
                 'file is stored in pic1 directory as <md5>.png \n' +
                 'If a filename is not specified, the file is named with \n' +
                 'its md5 hash. \n\n' +
                 'The mapping of id->filename can be found \n' +
                 'in the optional visit-chain file. Note that it is the \n' +
                 'user\'s responsibility to maintain unique url-ids for \n' +
                 'unique id->filename mappings.'
                )
    parser.add_argument('--dom-dir',  
            help='Directory for storing DOMs. Works like --screenshot-dir \n' +
                 'argument, except the file extensions are .html')
    parser.add_argument('--visit-chain-dir', 
            help='Directory for storing the visit chains. A visit chain \n' +
                 'consists of all the URLs in encountered in the visit, \n' +
                 'their headers, server addresses, dom files and \n' +
                 'file mapping, the node the URL was crawled from, \n' +
                 'the timestamp and proxy used. The argument works like \n' +
                 '--screenshot-dir argument, except the file extension is \n' +
                 '.json. \n ' +
                 'NOTE: If valid screenshot/dom filenames are not provided \n'+
                 'in the input files, then the files will be saved as their\n'+
                 ' md5.extension. If visit chains are not being saved, the \n'+
                 'mapping of feature:filename will be lost.')
    parser.add_argument('-i', '--input-file', action='append',
            help='Input file/directory containing URLs. Either specify \n'+
                 'any number of input files or a single input directory \n'+
                 'containing the input files. For example: \n' +
                 '    python run.py -i input1.json -i input2.json \n' +
                 'or \n' +
                 '    python run.py -i /path/to/input/directory \n',
            required=True)
    parser.add_argument('-n', '--num_browser', type=int, 
            help='Maximum number of browser instances to run in parallel. \n'+
                 'A single browser instance visits only a single URL at a \n'+
                 'time.', 
            required=True)
    parser.add_argument('--ext-start-port', default=4000, type=int, 
            help='This script communicates with Firefox extension \n' +
                 'over TCP sockets. <num-browser> number of ports, \n' +
                 'starting from this one will be used, if Firefox is used.\n'+
                 'Default value is %(default)s.')
    parser.add_argument('--restart-browser', action='store_true', 
            default=False,
            help='Giving this argument forces browser restart for every \n' +
                 'visit. While this will provide sanity, the browser \n' +
                 'typically takes up to 5 seconds to be set up so for \n' +
                 'efficiency, this option is disabled by default')
    parser.add_argument('--version', action='version', version='Stallone 0.1',
            help='displays the crawler version.')
    parser.add_argument('-b', '--browser', choices=['Firefox'],
            help='browser to be used. Default: %(default)s', default='Firefox')
    parser.add_argument('--proxy-file', 
            help='Proxy file contains lists of the form \n' +
            '[host, port, type]. See proxy_sample.json for example. The \n' +
            'crawler does not set up access to the proxy, that must be \n' +
            'done by the user. One can also directly specify proxy ip and\n' +
            'port in the input file, on a per-url basis, in which case \n' +
            'the input file options are given preference.')
    parser.add_argument('--proxy-scheme', choices=['round-robin'], 
            default='round-robin', 
            help='If the proxy information is not specified in the input \n' +
            'for every URL, a general policy can be used. \n' + 
            'Default: %(default)s')
    parser.add_argument('-v', '--verbosity', 
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            help='Anything at the log level and above will be logged. \n' +
            'CRITICAL > INFO. Default: %(default)s', default='WARNING')
    parser.add_argument('--log-dir', default=default_log_dir,
            help='Logs are stored in this directory. Default is \n' + 
            '%(default)s directory in current directory.')
    parser.add_argument('--suppress-stdout', action='store_true', 
            default=False, 
            help="By default the logs are shown on stdout and sent to the \n"+
            "the log files. Use this option to suppress output on stdout.")
    parser.add_argument('--tags-file', type=file, 
            help="JSON file with dictionaries of tags:\n" +
            '{ \n' +
            '    "tag_name_1": { \n' +
            '                       "threshold": some_int, \n' +
            '                       "regexes": [regex1, regex2,...]\n' +
            '                  }\n'+
            '}\n' +
            'See sample_tags.json for example. <tag_name> is applied \n' +
            'if <threshold> number of <regexes> match.\n' +
            'Note that only a single tagging file can be supplied. As \n'+
            'long as this argument is used, all pages will be tagged. \n' +
            'This includes URLs for which user has not requested DOMs for.')
    '''
    parser.add_argument('-r', '--report-recipient', 
            help='Email address to send crawl summary. The summary is \n' +
            'also saved in the log folder.')
    parser.add_argument('--proxy-url', help='Same as --proxy-file except the \
            file will be fetched from the URL when the crawler reboots. This is\
            ideal if a service maintains a list of available proxies that is \
            refreshed frequently.')
    parser.add_argument('-e', '--email_errors', help='Email the errors that \
            cause the crawler to crash to this recipient. The crash summary is\
            also saved in log folder.')
    '''
    return parser.parse_args()

def setup_logging(args):
    """Sets up logging. The logger is stored in crawlglobs.logger.
    Returns the logger. Also sets up a log queue for multiprocess logging.
    """
        # Set up logging directory and start logger
    level = getattr(logging, args.verbosity.upper(), None)
    if args.log_dir and not os.path.exists(args.log_dir):
        print "Setting up logging"
        try:
            os.makedirs(args.log_dir)
        except:
            print ("Failed to create logging path %s. Exception: %s \n" 
                   % (args.log_dir, traceback.print_exc()))
            exit(1)
    elif args.log_dir: 
        print ("Not creating %s since path already exists." % args.log_dir)
    print "Logging output will now go to %s at level %s " % (args.log_dir, 
                                                             level)
    crawlglobs.log_level = level
    crawlglobs.log_q = mp.Queue()
    logger = logging.getLogger(config.MAIN_LOGGER_NAME)
    handler = logging.handlers.TimedRotatingFileHandler(
                    args.log_dir + '/' + config.LOG_FILENAME, 'H', 1, 100)
    handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
    logger.addHandler(handler)
    # Attach streamhandler if desired.
    if not args.suppress_stdout:
        handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(handler)
    logger.setLevel(level)
    
    # Set up logging for subprocesses. This is needlessly complex.
    log_q = mp.Queue()
    log_q_reader = mplogging.LogQueueReader(log_q)
    log_q_reader.start()
    crawlglobs.logger  = logger
    return logger

def display(args, logger):
    """Sets up Xvfb if necessary.
    """
    # Display
    if not args.no_xvfb:
        logger.info("Checking if Xvfb is installed")        
        utils.installed('xvfb', logger)
        logger.debug("Xvfb found, starting it")
        crawlglobs.display = Display(backend='xvfb', visible=False)
        crawlglobs.display.start()
    else: 
        logger.info("Not using Xvfb")

def prep_firefox(args, logger):
    """Checks if a supported version of firefox is installed. Exits with 
    error message if it isn't. Finally creates a directory to store
    firefox profiles.
    """
    utils.installed('firefox', logger)
    logger.info("Checking Firefox version compatibility")
    fh = open("firefox_template/extensions/trajlogger@cs.ucsd.edu/" +
                  "install.rdf", "r")
    data = fh.read()
    fh.close()
    match = re.search('maxVersion="((\d+\.\d+)\.?.*)"', data)
    if match:
        crawler_ff_version = float(match.group(2))
        logger.debug("Expected maximum firefox version: %s " 
                         % crawler_ff_version)
    ff_version_output = subprocess.Popen(["firefox", "--version"], 
                                    stdout=subprocess.PIPE).communicate()[0]
    match = re.search('Mozilla Firefox (\d+\.\d+).*', ff_version_output)
    if match:
        system_ff_version = float(match.group(1))
        logger.debug("System's firefox version: %s" % system_ff_version)
    if system_ff_version > crawler_ff_version:
        logger.critical(("Crawler only supports Firefox up to \n" +
                   "%.1f. The crawler extension needs to be updated. \n"+ 
                   "Updating the maxVersion in install.rdf file in \n" +
                   "trajlogger@cs.ucsd.edu to the system firefox version \n" +
                   "might work. \nExiting.") % crawler_ff_version)
        exit(1)
    # Create tmp directory for storing firefox profiles.
    profile_dir = os.path.join(utils.default_tmp_location(), 
                               config.PROFILE_DIR)
    if not os.path.exists(profile_dir):
        logger.info("Creating directory for firefox profiles")
        os.makedirs(profile_dir)
    else:
        logger.error("Firefox profile directory already exists. Something's"+
                     "wrong. Please file a bug.")

def run():
    args = setup_args()
    logger = setup_logging(args)
    display(args, logger)
    # Check if pngnq is installed.
    utils.installed('pngnq', logger)
    if args.browser and args.browser == 'Firefox':
        # Check firefox installation and version.
        prep_firefox(args, logger)
    # Set up global variables.
    if args.screenshot_dir: 
        crawlglobs.img_dir = args.screenshot_dir
    if args.dom_dir: 
        crawlglobs.dom_dir = args.dom_dir
    if args.visit_chain_dir:
        crawlglobs.visit_chain_dir = args.visit_chain_dir
    if args.proxy_file:
        crawlglobs.proxy_file = args.proxy_file
    if args.proxy_scheme:
        crawlglobs.proxy_scheme = args.proxy_scheme
        
    # Get all files given as input.
    input_file = args.input_file
    # Check if the input file is a directory.
    if os.path.isdir(args.input_file[0]):
        logger.info(("All .json files in %s will be crawled") 
                     % args.input_file[0])
        input_file = [args.input_file[0] + "/" + f 
                      for f in os.listdir(args.input_file[0]) 
                                        if f[-5:] == '.json']
    if args.tags_file:
        logger.debug("Tag file supplied. Loading tags.")
        # Create a tags list with [(tag_name, {"threshold": value, "regexes":
        #    [compiled regexes]}
        try:
            crawlglobs.tags_l = []
            for (tag_name, attrs) in json.load(args.tags_file).iteritems():
                temp_obj = {"threshold": attrs["threshold"]}
                temp_obj["regexes"] = [re.compile(regex) 
                                       for regex in attrs["regexes"]]
                crawlglobs.tags_l.append((tag_name, temp_obj))
        except Exception, e:
            logger.critical("Error loading tags file: %s" %  e.message)
            exit()
            

    # Spawn process to parse input request URLs.
    logger.debug("Creating queues and starting queue controller process")
    queue_cc = FileQController(input_file, args.num_browser, crawlglobs.log_q)
    request_q = mp.JoinableQueue(config.REQUEST_Q_SIZE)
    result_q = mp.JoinableQueue(config.RESULT_Q_SIZE)
    queue_cc_p = mp.Process(target=FileQController.run, 
                            args=(queue_cc, request_q, result_q)).start()
    logger.info("Starting browser and visiting URLs")
    # Spawn CrawlerController processes.
    ext_port = args.ext_start_port
    for i in range(args.num_browser):
        crawler = CrawlerProcess(restart = args.restart_browser, 
                                browser = args.browser, 
                                ext_port = ext_port,
                                proxy_file = args.proxy_file,
                                proxy_scheme = args.proxy_scheme,
                                log_q = crawlglobs.log_q)
        logger.debug(("Starting crawler process on Firefox port: %s")
                     % ext_port)
        crawler_p = mp.Process(target=CrawlerProcess.run, 
                               args=(crawler, request_q, result_q)).start()
        ext_port += 1
        
    # Wait for all children to die. Exit when they are all done. This is also
    #     important because the dead children will only join() when this is
    #     called. 
    # TODO (nchachra): This should be called in case of exceptions in main too.
    while len(mp.active_children()) != 0:
        logger.info("Request q size: %s" % request_q.qsize())
        logger.info("Result q size: %s" % result_q.qsize())
        if (len(mp.active_children()) == 1 and request_q.qsize() == 1 
                and result_q.qsize() == 0):
            task = request_q.get()
            if task == "CLEANUP":
                # Removing this final task will cause the qcontroller process
                #    to join. Finally there will be 0 child processes left, 
                #    and main will join as well.
                logger.info("Only the q manager seems to be attempting " +
                            "to join q. Joining in main and exiting.")
                request_q.task_done()
        logger.debug("Active processes: %s " % mp.active_children())
        time.sleep(10)
    logger.critical("Final cleanup.")
    utils.cleanup(logger)
    logger.critical("Byebye!")


if __name__== '__main__':
    run()
