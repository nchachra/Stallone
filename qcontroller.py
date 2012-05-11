import simplejson as json
import multiprocessing as mp
# Slightly retarded. We need Queue only for the Full and Empty exception,
#    even though we are actually using multiprocessing.JoinableQueue
import Queue
import time

import config
import mplogging

'''The Queue Controller classes control filling and emptying request and
result queue. 

Author: nchachra@cs.ucsd.edu
'''

class QController:
    '''Base class for queue controller classes. The run() function is 
    executed as a separate process. Direct objects of this class wont work. 
    empty_q() and fill_q() are implemented by subclasses. In order to 
    implement empty and fill functions using database, this will need to be
    extended.
    '''
    def __init__(self, log_q):
        """log_q is the multiprocessing queue that we place records on for
        logging. These are processed by LogQueueReader thread in mplogging.
        """
        self.cleanup = False
        self.logger = mplogging.setupSubProcessLogger("QController", log_q)
        
    
    def run(self, req_q, res_q):
        """Runs until the cleanup flag is set. Waits for request and result 
        queues to join before exiting. Loops and fills the request queue when 
        it is less than a half full and empties result queue when it is over 
        half full. The fill_q and empty_q functions are implemented by 
        subclasses.
        """
        while True:
            self.logger.debug("In QController's run()")
            if self.cleanup: 
                # Wait for all jobs in req_q to finish
                self.logger.debug(("Cleanup flag set."))
                self.logger.debug("Emptying result queue")
                self.empty_q(res_q)
                self.logger.debug("Waiting for result queue to join")
            if res_q.qsize() > config.RESULT_Q_SIZE/2:
                self.logger.info("Emptying queue")
                self.empty_q(res_q)
            else: 
                self.logger.info("Result q size: %s" % res_q.qsize())
            if req_q.qsize() < config.REQUEST_Q_SIZE/2:
                self.logger.info("Filling queue")
                self.fill_q(req_q)
            else: 
                self.logger.info("request_q size: %s" % req_q.qsize())
            if req_q.qsize() == 0 and res_q.qsize() == 0 and self.cleanup:
                req_q.join()
                res_q.join()
                self.logger.debug("req_q and res_q joined.")
                self.logger.info("Terminating q manager")
                break
            time.sleep(10)

    def fill_q(self, res_q):
        raise NotImplementedError('Subclass must implement fill_q method.')

    def empty_q(self, req_q):
        raise NotImplementedError('Subclass must implement empty_q method.')

class FileQController(QController):
    """Handles input queue for crawler based on input and output json files. A 
    database based crawler will need similar classes for handling request 
    and result queues.
    """
    def __init__(self, req_file_list, num_browser, log_q):
        QController.__init__(self, log_q)
        self.req_file_list = req_file_list
        # Keep track of items currently unprocessed. These are obtained from
        #    the json file. Whenever the queue has a slot, the items are added
        #    to it.
        self.jobs = []

    def fill_q(self, req_q):
        """ Creates and maintains a jobs list using the input files. Uses
        the jobs list to fill the request queue. When no input files or jobs
        are left, it inserts a special item "CLEANUP". This item works to 
        synchronize the crawler processes that join on encountering "CLEANUP"
        item.
        """
        if not self.jobs and self.req_file_list:
            # Note that pop() gets the last element in the list.
            self.logger.debug("jobs list has 0 jobs. Adding some.")
            fh = file(self.req_file_list.pop())
            obj = json.load(fh)
            self.jobs.extend(obj.iteritems())
            self.logger.debug("Jobs in queue: %s" % self.jobs)
        if self.jobs:
            self.logger.info("Adding jobs to request q from jobs list")
            # Pop elements from self.job and put them into request q.
            while self.jobs:
                job = self.jobs.pop()
                try:
                    req_q.put_nowait(job)
                    print job
                except Queue.Full:
                    self.logger.debug("Request queue is full")
                    # Add the job back to the self list and leave.
                    self.jobs.append(job)
                    break
        else:
            self.logger.info(("No more input files or request urls left.\n"))
            # The queue will have a special entry called "CLEANUP". This 
            #    serves as a flag to cleanup and avoids needless inter-process
            #    communication.
            if not self.cleanup:
                self.logger.info("Setting CLEANUP flag.")
                req_q.put("CLEANUP")
                self.cleanup = True
        
    def empty_q(self, res_q):
        """Grabs entries from result q and writes them to file.
        """
        self.logger.debug("Writing results to file")
        while True:
            try:
                result_list = res_q.get_nowait()
                self.write_to_file(result_list)
                res_q.task_done()
            except Queue.Empty:
                self.logger.debug("Emptied results to file.")
                break
            
    def write_to_file(self, result_list):
        """Writes the visit to filename fname in json format.
        """
        for (fname, result_dict) in result_list:
            fh = open(fname, "w")
            json.dump(result_dict, fh, indent=4)
            fh.close()