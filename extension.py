import hashlib
import os.path
import simplejson as json
import shutil
import socket
import subprocess
import time
import traceback

import config
import crawlglobs

class Extension:
    def __init__(self, logger, host='localhost',port=7055):
        """
        By default Firefox extension starts up listening on port 7055. If
        another port is desired, start the extension with defaults and use
        restart_at_port().
        """
        self.host = host
        self.port = port
        self.logger = logger

    def restart_at_port(self, port):
        """
        Restart the extension at a new port.
        """
        msg = {'command':'SET_PORT', 'args':port}
        result = self.wait_for_action(json.dumps(msg))
        self.port = port
        self.logger("msg: %s, result: %s" % (msg, result))
        return result
    
    def wait_for_action(self, msg, poll_interval=10, 
                        timeout=config.PAGE_TIMEOUT):
        """
        Retries a command at poll_interval,until timeout. Returns None if
        action failed.
        """
        wait_time = 0
        result = None
        while wait_time <= timeout and not result:
            try:
                result = self.send_and_recv(msg)
                if result: break
            except Exception, e:
                self.logger.warning("Exception in %s. Retrying until timeout.")
            time.sleep(poll_interval)
            wait_time += poll_interval
        return result
    
    def send_and_recv(self, strmsg, msglen=4096):
        """
        Sends strmsg to the socket, and returns the received data.
        """
        resultstring = ""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(180)
        sock.connect((self.host, self.port))
        sock.send(strmsg)
        if msglen != 4096:
            while len(resultstring) < msglen:
                chunk = sock.recv(4096)
                if chunk == '':
                    raise RuntimeError, 'SOCKET BROKEN'
                resultstring = resultstring + chunk
            return resultstring
        else:
            data = sock.recv(4096)
            return data

    def redirects(self):
        """
        Returns a list of the URLs seen in the address bar during navigation
        """
        redirects_len = self.msg_len('GET_REDIRECTS_LEN')
        msg = {'command': 'GET_REDIRECTS', 'args': ''}
        redirects = self.send_and_recv(json.dumps(msg), redirects_len)
        if redirects_len != len(redirects):
            raise RuntimeError('Incomplete redirects received.')
        return self.safe_decode(redirects)

    def reset(self):
        """
        Clears the lists, proxies, custom preferences and other internal 
        information in the extension. This should be used before setting the 
        URL.
        """
        msg = {'command': 'RESET', 'args': ''}
        result = self.wait_for_action(json.dumps(msg))
        return result

    def current_url(self):
        """
        Returns the current URL in the address bar, as a dictionary of url
        parts: href, host, hostname, port
        """
        msg = {'command': 'GET_URL', 'args': ''}
        data = self.send_and_recv(json.dumps(msg))
        return json.loads(data)

    def set_url(self, url):
        """
        Sets the URL in the address bar to url, changing will cause navigation,
        but can also be used to execute JS or scroll to an anchor
        """
        msg = {'command': 'SET_URL', 'args': url}
        data = self.send_and_recv(json.dumps(msg))    
        return json.loads(data)

    def set_header(self, name, value):
        """
        Sets a HTTP header for the next request. Headers are name, value 
        pairs. This can be used to overwrite existing headers.
        """
        msg = {'command': 'SET_HEADER', 'args': [name, value]}
        data = self.send_and_recv(json.dumps(msg))
        return json.loads(data)

    def headers(self):
        """
        Gets the headers for each of the URLs seen so far. This includes
        redirects as well as elements included with a src attribute (and 
        fetched with HTTP).
        headerval = headers[url][headername]
        """
        headers_len = self.msg_len('GET_HEADERS_LEN')
        if headers_len == 0:
            return None
        msg = {'command': 'GET_HEADERS', 'args':''}
        headers = self.send_and_recv(json.dumps(msg), headers_len)
        if len(headers) != headers_len:
            raise RuntimeError('Incomplete headers returned.')
        return self.safe_decode(headers)

    def set_pref(self, name, value, pref_type):
        """Sets up the preference with a given value. The arguments name, 
        value and pref_type are all strings. The extension casts the 
        value according to the type itself. Valid values: string values, 
        'true', 'false', integers.
        """
        msg = {'command': 'SET_PREF', 'args':[name, value, pref_type]}
        return json.loads(self.send_and_recv(json.dumps(msg)))

    def set_proxy(self, ip, port, proxy_type):
        """ Sets the proxy for FF to use. Type can be 'http' or 'socks'.
        IP address (string), and port is a string too.
        """
        msg = {'command': 'SET_PROXY', 'args': [proxy_type, ip, port]}
        return json.loads(self.send_and_recv(json.dumps(msg)))

    def disable_proxy(self):
        """ Turns off proxying """
        msg = {'command': 'DISABLE_PROXY', 'args':''}
        return json.loads(self.send_and_recv(json.dumps(msg)))

    def html(self):
        """
        Returns the raw HTML for the page. Note: the HTML is NOT JSON encoded.
        It's raw as it comes out of innerHTML for the body and head elements.
        """
        html_len = self.msg_len('GET_HTML_LEN')
        msg = {'command': 'GET_HTML', 'args':''}
        html = self.send_and_recv(json.dumps(msg), html_len)
        if html_len != len(html):
            raise RuntimeError('Incomplete message received.')
        return html
        
    def msg_len(self, command='GET_HTML_LEN'):
        """
        Helper method. Returns length of message that will be returned by
        the extension. 
        """
        msg = {'command': command, 'args':''}
        len_str = self.send_and_recv(json.dumps(msg))
        if len_str == "": 
            raise ValueError('Get Length returned empty string')
        msg_len = int(len_str)
        return msg_len

    def wait_for_file_creation(self, file_path, poll_interval=1, timeout=10):
        """
        Waits until timeout for file at file_path to be created.
        """
        wait_time = 0
        while wait_time <= timeout and not os.path.exists(file_path):
            time.sleep(poll_interval)
            wait_time += poll_interval
            
    def safe_decode(self, msg):
        """
        Mostly we're trying to load JSON which uses utf-8 decoding by default.
        Sometimes data can't be utf-8 decoded. Instead of trying to find
        encoding, we'll just convert encode the data into utf-8 and ignore
        characters that can't be encoded.
        """
        try:
            result = json.loads(msg)
        except UnicodeDecodeError, e:
            if str(e).find("'utf8' codec can't decode byte") != -1:
                self.logger.debug(("Unicode decode error. Changing string" +
                                  "to utf-8"))
                msg = msg.decode('utf-8', 'ignore')
                result = json.loads(msg)
        return result
            
    def file_md5(self, file_path):
        """
        Returns md5 for file at file_path. Ensure that file exists before 
        calling this functin.
        """
        md5 = hashlib.md5()
        fh = open(file_path)
        while True:
            data = fh.read()
            if not data:
                break
            md5.update(data)
        return md5.hexdigest()
        
    def response_codes(self):
        """
        Returns a dictionary of {url: response_code} 
        """
        responsecodes_len = self.msg_len('GET_RESPONSE_CODES_LEN')
        if responsecodes_len == 0:
            return None
        msg = {'command': 'GET_RESPONSE_CODES', 'args':''}
        responsecodes = self.send_and_recv(json.dumps(msg), 
                                            responsecodes_len)
        if responsecodes_len != len(responsecodes):
            raise RuntimeError('Incomplete response codes received.')
        return self.safe_decode(responsecodes)

    def screenshot_file(self, dest_dir, fname):
        """ 
        If fname is valid, it creates a file with fname in dest_dir. If fname 
        is invalid or not passed, it creates a file with file's md5. All 
        files are compressed using pngnq.
        
        Return value is a dictionary {'md5': md5, 'exists': True/False} or
        {'file': fname, 'exists': True/False}. 'exists' indicates if a file 
        with the name already existed. New file is not created in this 
        scenario. 
        """
        temp_fname = os.uname()[1] + '_' + str(self.port) + '.png'
        temp_path = os.path.join(crawlglobs.tmp_dir, temp_fname)
        nq8_temp_path = temp_path.split('.png')[0] + '-nq8.png'
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(nq8_temp_path):
            os.remove(nq8_temp_path)
        self.logger.debug("Removed temp files for screenshot")
        msg = {'command': 'SAVE_SCREENSHOT_FILE', 'args': temp_path}
        response = self.send_and_recv(json.dumps(msg))
        self.logger.debug("Result for %s: %s" % (msg, response))
        if json.loads(response)['result'] == "ERROR":
            return None
        self.wait_for_file_creation(temp_path)
        if os.path.exists(temp_path):
            compress_process_returncode = subprocess.call(['pngnq', 
                                                           temp_path])
        self.wait_for_file_creation(nq8_temp_path)
        self.logger.debug("Created compressed pngnq screenshot")
        if os.path.exists(nq8_temp_path):
            if not fname:
                md5 = self.file_md5(nq8_temp_path)
                md5_name = md5 + '.png'
                dest_path = os.path.join(dest_dir, md5_name)
            elif fname[-4:] != '.png':
                fname += '.png'
                dest_path= os.path.join(dest_dir, fname)
            else:
                dest_path = os.path.join(dest_dir, fname)
        if os.path.exists(dest_path):
            if fname:
                return {'file': fname, 'exists': True}
            else:
                return {'md5': md5, 'exists': True}
        else:
            store_tmp_path = os.path.join(dest_dir, temp_fname)
            shutil.move(nq8_temp_path, store_tmp_path)
            shutil.move(store_tmp_path, dest_path)
            if fname:
                return {'file': fname, 'exists': False}
            else:
                return {'md5':md5, 'exists':False}

    def html_file(self, dest_dir, fname):
        """
        Same as screenshot_file, except for .html files.
        """
        temp_fname = os.uname()[1] + '_' + str(self.port) + '.html'
        temp_path = os.path.join(crawlglobs.tmp_dir, temp_fname)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        msg = {'command': 'SAVE_HTML_FILE', 'args':temp_path}
        response = self.send_and_recv(json.dumps(msg))
        self.wait_for_file_creation(temp_path)
        self.logger.debug("Result for %s: %s" % (msg, response))
        if json.loads(response)['result'] == "ERROR":
            return None
        md5 = None
        if not fname:
            md5 = self.file_md5(temp_path)
            md5_name = md5 + '.html'
            dest_path = os.path.join(dest_dir, md5_name)
        else:
            if fname[-5:] != ".html": 
                fname += '.html'
            dest_path = os.path.join(dest_dir, fname)
        if os.path.exists(dest_path):
            if md5:
                return {'md5':md5, 'exists':True}
            else:
                return {'file': fname, 'exists': True}
        else:
            store_tmp_path = os.path.join(dest_dir, temp_fname)
            shutil.move(temp_path, store_tmp_path)
            shutil.move(store_tmp_path, dest_path)
            if md5:
                return {'md5': md5, 'exists': False}
            else:
                return {'file': fname, 'exists': False}

    def page_loaded(self):
        """
        Returns whether page dom has been loaded.
        """
        msg = {'command': 'HAS_PAGE_LOADED', 'args':''}
        response = json.loads(self.send_and_recv(json.dumps(msg)))
        return response['result']

    def wait_for_load(self, poll_interval=1, timeout=10, method=time.sleep):
        """
        Waits until timeout for the page to load. Gives up if the page still
        doesn't load.
        """
        test = lambda : True if self.page_loaded() == "True" else False
        waittime = 0
        while waittime <= timeout and not test():
            method(poll_interval)
            waittime += poll_interval

    def page_error(self):
        """
        Returns if the page is a FF error page.
        """
        msg = {'command':'IS_PAGE_ERROR', 'args':''}
        response = json.loads(self.send_and_recv(json.dumps(msg)))
        if response['result'] == "True":
            return True
        else:
            return False
        
    def eval_js(self, js):
        """
        Evals arbitrary js passed to the extension. Returns a JSON result of
        the eval.
        """
        msg = {'command': 'EVAL_JS', 'args': js}
        response = json.loads(self.send_and_recv(json.dumps(msg)))
        return response['result']