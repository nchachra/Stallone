import json

"""Processes that do the actual instrumentation and visits through browser.
Any new browser addition, or new method of crawling will need to subclass
CrawlerProcess and implement the empty functions.

Author: nchachra@cs.ucsd.edu
"""

class Proxy:
    """Proxy class provides the next proxy that the browser should use, 
    depending on the scheme user has chosen. If the proxy setting for the
    URL already exists in the input file, the return value of this class,
    if any, is ignored in favor of the proxy in input file.
    This is the base class.
    """
    def __init__(self, proxy_file, proxy_scheme, logger=None):
        if logger:
            self.logger = logger
        if not proxy_file:
            self.proxy_l= None
        elif proxy_file and proxy_file[-4:] != 'json':
            self.logger.critical("ERROR: Proxy file should be .json file.")
            exit()
        else:
            fp = open(proxy_file, 'rb')
            proxy_dict = json.load(fp)
            fp.close()
            if not proxy_dict.has_key('proxies'):
                self.logger.critical("ERROR: Proxy file should \n" +
                                     "have a proxies key. See proxy_ec2.json")
                exit()
            else:
                self.proxy_l = proxy_dict["proxies"]
        if proxy_scheme == 'round-robin' or not proxy_scheme:
            self.__class__ = RoundRobin

    def next_proxy(self):
        """Returns the next (IP, port, type) proxy tuple to be used.
        """
        pass


class RoundRobin(Proxy):
    """Implements the round-robin scheme for the proxies in the proxy file.
    """
    cur_ip_index = 0
    def next_proxy(self):
        """Returns the next [IP, port, type] for making request. Returns None
        if the proxy file is missing.
        """
        if not self.proxy_l:
            return None
        if self.__class__.cur_ip_index == len(self.proxy_l):
            self.__class__.cur_ip_index = 0
        proxy = self.proxy_l[RoundRobin.cur_ip_index]
        self.__class__.cur_ip_index += 1
        return proxy
