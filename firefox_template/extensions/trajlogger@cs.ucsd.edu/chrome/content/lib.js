/*
 * Library module that exposes commands available for crawling.
 * 
 * 
 * Author: grier@imchris.org, 
 *         nchachra@cs.ucsd.edu
 *         dywang@cs.ucsd.edu
 */

TrajLogging.LIB = {

    /*
     * service variable for sending messages to the console.
     */
    consoleService: null,
    
    /*
     * Array of all the URLs seen through this visit. This can include 
     * redirects within the iframe of the page. Used for building the 
     * redirect chain.
     */
    redirects: [],
    
    /*
     * TODO (dywang): What is this?
     */
    redirectsHeaders: [],
    
    /*
     * What is this??? Monster of an object. Initialized like an array
     * but treated like an object?
     * 
     * ["url": ["headers": {"header":value, 
     *                      "header":"value"}, 
     *          "responsecode": responsecode
     *         ]
     * ]
     * 
     * Doesn't matter. It works.
     */
    urlInfo: [],
    
    /*
     * JSON encoded string consisting of:
     * {
     *     url: {
     *          header: value,
     *          header: value
     *      }
     * }
     */
    headerString: '',
    
    /*
     * This string is built out of redirects observed during the visit and 
     * linking them together. This is a continuous chain of redirects as much
     * as we can put together.
     */
    redirectsString: '',
    
    /*
     * Contains a JSON encoded string of: {
     *     url: responsecode,
     *     url: responsecode
     * }
     */
    responsecodesString: '',
    
    /*
     * Contains page's entire HTML.
     */
    htmlString: '',
    
    /*
     * This flag indicates whether a page has been loaded. It is set when the
     * onStateChange event is fired. See webprogress.js for event handling.
     */
    pageLoaded: false,
    
    /*
     * Firefox has about:neterror as the URI when it encounters a network
     * problem during the page visit. This variable stores if this visit
     * encountered that URI.
     */
    pageError: false,
    
    /*
     * Calculated using toolbar.google.com's API. Not in use.
     */
    pagerank: -1,
    
    /*
     * Request variable for toolbar.google.com's pagerank API.
     */
    pagerankRequest: null,
    
    /*
     * A key-value store of header: value for the headers that need to be
     * set prior to the visit.
     */
    requestHeaders: {},
    
    /*
     * Array of pref names that a user has set. Reset() clears all of these 
     * prefs.
     */
    customPrefs: [],

    /*
     * Init is the first function to be called. Any components should be
     * initialized here.
     */
    init: function() {  
        // Logging service for console.
        this.consoleService = Components
                        .classes["@mozilla.org/consoleservice;1"]
                        .getService(Components.interfaces.nsIConsoleService);
    },

    /* 
     * Takes level: either INFO or ERROR and logs to the console accordingly.
     */
    log: function(sLevel, sMsg) {
        if(sLevel === "INFO") {
            this.consoleService.logStringMessage("Trajlogger: " + sMsg);
        } else if (sLevel === "ERROR") {
            Components.utils.reportError("Trajlogger: " + sMsg);
        }
    },

    /* 
     * Call cleans up the memory to ready for making a new visit.
     */
    reset: function()
    {
        this.log("INFO", "Resetting");
        this.redirects = [];
        this.redirectsHeaders = [];
        this.urlInfo = [];
        this.headerString = '';
        this.redirectsString = "";
        this.responsecodesString = "";
        this.htmlString = "";
        this.pageLoaded = false;
        this.pageError = false;
        this.pagerank = -1;
        this.pagerankRequest = null;
        this.requestHeaders = {};

        TrajLogging.Pageranker.init();
        // Custom prefs need to be cleared before the array can be reset.
        this.clearCustomPrefs();
        this.customPrefs = [];
        
        this.handleCommand("DISABLE_PROXY");
    },

    /*
     * Takes a message string and returns a JSON encoded string of the form:
     * '{"result": "ERROR", "message": aMessage}'
     */
    getErrorJSONString : function(aMessage) {
        obj = {};
        obj["result"] = "ERROR";
        obj["message"] = aMessage;
        return JSON.stringify(obj);
    },
    
    /* Sets prefName preference to prefValue. The prefType can either be 
     * string/str/int/integer/bool/boolean. The corresponding values will be 
     * cast accordingly before setting. If the type is boolean, the valid 
     * values are 'true' and 'false'.
     * Returns the string that extension should return.
     */
    setPrefs: function(prefName, prefValue, prefType) {
        var prefs = Components.classes["@mozilla.org/preferences-service;1"]
                            .getService(Components.interfaces.nsIPrefBranch);
        if(prefType.toLowerCase() === "int" || 
           prefType.toLowerCase() === "integer") {
            try {
                // We need to keep track of what's set to reset it later.
                this.customPrefs.push(prefName);
                prefs.setIntPref(prefName, parseInt(prefValue));
            } catch(e) {
                var errorMsg = "Invalid pref: " + prefName + ": " + prefValue;
                this.log("ERROR", errorMsg);
                return this.getErrorJSONString(errorMsg);
            }
        } else if(prefType.toLowerCase() === "string" || 
                  prefType.toLowerCase() === "str") {
            try {
                this.customPrefs.push(prefName);
                prefs.setCharPref(prefName, prefValue);
            } catch(e) {
                var errorMsg = "Invalid pref: " + prefName + ": " + prefValue;
                this.log("ERROR", errorMsg);
                return this.getErrorJSONString(errorMsg);
            }
        } else if((prefType.toLowerCase() === "bool" || 
                  prefType.toLowerCase() === "boolean") && 
                  (prefValue.toLowerCase() === "true" || 
                  prefType.toLowerCase() === "false")) {
            try {
                this.customPrefs.push(prefName);
                value = false;
                if(prefType.toLowerCase() === "true") {
                    value = true;
                }
                prefs.setBoolPref(prefName, value)
            } catch(e) {
                var errorMsg = "Invalid pref: " + prefName + ": " + prefValue;
                this.log("ERROR", errorMsg);
                return this.getErrorJSONString(errorMsg);
            }
        } else {
            var errorMsg = "Invalid pref: " + prefName + ": " + prefValue;
            this.log("ERROR", errorMsg);
            return this.getErrorJSONString(errorMsg);
        }
        return '{"result":"DONE"}';
    },

    /*
     * Clears prefs contained in this.customPrefs. customPrefs is a list of
     * lists [[prefname, prefvalue, preftype],...].
     */
    clearCustomPrefs: function() {
        var prefs = Components.classes["@mozilla.org/preferences-service;1"]
                            .getService(Components.interfaces.nsIPrefBranch);
        for(pref in this.customPrefs) {
            prefs.clearUserPref(pref);
        }
    },

    /*
     * Initializes the urlInfo object for a URL seen during a visit.
     * WTF is this object? It's being used as an object but initialized
     * as an array. JavaScript confuses!
     * Doesn't matter, it works.
     */
    initUrlInfo: function(url)
    {
        var hasUrl = false;
        var i;
        for(i in this.urlInfo) {
            if(i === url) {
                hasUrl = true;
                break;
            }
        }
        if(!hasUrl) 
        {
            this.urlInfo[url] = new Array();
        }
    },

    /*
     * Takes a url as an argument and inserts it into the redirects list.
     */
    addRedirect: function(url)
    {
        if (this.redirects.indexOf(url) == -1)
        {
            this.redirects.push(url);
        }
    },

    /*
     * Builds and returns the list of all redirects including the address
     * bar changes and 302 redirects. Uses headers to link all the redirects
     * in a single continuous chain.
     */
    buildRedirectsString: function() {
        chain = [];
        redirLen = this.redirects.length;
        for (i = 0; i < redirLen; i++) {
            tail = this.redirects[i];
            // Find any header redirect chains that should be appended
            redirHeaderLen = this.redirectsHeaders.length;
            for (j = 0; j < redirHeaderLen; j++) {
                redirectHeader = this.redirectsHeaders[j];
                if (redirectHeader.tail == tail) {
                    // Add urls seen in header redirect chain to the super 
                    //  chain
                    for (k = 0; k < redirectHeader.chain.length; k++) {
                        url = redirectHeader.chain[k];
                        chain.push(url);
                    }
                    break;
                }
            }
            // Add tail to super chain
            chain.push(tail);
        }
        return JSON.stringify(chain);
    },

    /*
     * Firefox displays a custom page with URI about:neterror if it fails
     * to reach a page due to network errors. This function checks for this
     * condition and updates the this.pageError variable. 
     */
    getPageError: function() {
        if(content.document.documentURI.substr(0,14)=="about:neterror") {
            this.pageError = true;
        } else {
            this.pageError = false;
        }
    },

    /*
     * Updates the pageLoaded variable when "load" event is fired. See 
     * browserOverlay.js
     */
    setPageLoaded: function(e) {
        if (e.originalTarget instanceof HTMLDocument) {
            TrajLogging.LIB.log("INFO", "Setting page loaded to true");
            TrajLogging.LIB.pageLoaded = true;
        }
    },

    /*
     * Adds the headerdict object to urlInfo[url]. The headerdict object is 
     * a key-value store for header:value that the extension retreived for URL.
     */
    addHeaders: function(url, headerdict)
    {
        this.initUrlInfo(url);
        this.urlInfo[url]['headers'] = {}
        for(var x in headerdict)
        {
            this.urlInfo[url]['headers'][x] = headerdict[x];
        }
    },

    /*
     * Adds a response code for the url in the urlInfo object.
     */
    addResponseStatus:function(url, statuscode)
    {
        this.initUrlInfo(url);
        this.urlInfo[url]['responsecode'] = statuscode.toString();
    },
    
    /*
     * Takes a command string and arguments and performs the appropriate 
     * function. Returns JSON encoded values appropriately as indicated. 
     * In case of error, returns the standard format:
     * '{"result": "ERROR", "message": "some error message"}'
     * 
     * For commands that don't expect special return values, the format is
     * standard:
     * '{"result": "DONE"}'
     */
    handleCommand: function(cmd, args)
    {
        switch(cmd)
        {
            case "SET_PORT":
                this.log("INFO", "Setting port to " + args);
                TrajLogging.Command.serverUsePort(args);
                return '{"result":"DONE"}'; 
                
            case "RESET":
                this.log("INFO", "Resetting");
                this.reset();
                return '{"result":"DONE"}';

            case "GET_REDIRECTS":
                // Returns JSON encoded list of redirects.
                if (this.redirectsString === "") {
                    this.redirectsString = this.buildRedirectsString();
                }
                return this.redirectsString;

            case "GET_REDIRECTS_LEN":
                this.redirectsString = this.buildRedirectsString();
                return this.redirectsString.length.toString();

            case "GET_URL":
                var loc = {};
                loc["href"] = content.document.location;
                return JSON.stringify(loc);
                
            case "SET_URL":
                gBrowser.stop();
                this.pageError = false;
                this.pageLoaded = false;
                content.document.location = args;
                return '{"result":"DONE"}';
                
            case "GET_HEADERS_LEN":
                // Returns the length of header string. See get_headers for
                //  string description.
                if(this.headerString == '') {
                    var urlHeaderObj = {};
                    for(var url in this.urlInfo) {
                        urlHeaderObj[url] = this.urlInfo[url]["headers"];
                    }
                    this.headerString = JSON.stringify(urlHeaderObj);
                }
                return this.headerString.length.toString();

            case "GET_HEADERS":
                // Returns a JSON encoded header string. The JSON object is a 
                //  mapping of {url: {header: value, 
                //                    header: value 
                //                    }
                //             }
                if(this.headerString == '') {
                    var urlHeaderObj = {};
                    for(var url in this.urlInfo) {
                        urlHeaderObj[url] = this.urlInfo[url]["headers"];
                    }
                    this.headerString = JSON.stringify(urlHeaderObj);
                }
                return this.headerString;

            case "GET_HTML":
                 // Returns HTML string. 
                 if (this.htmlString == '') {
                    var serializer = new XMLSerializer();
                    this.htmlString = serializer.serializeToString(
                                                   content.document);
                    var frames = content.document
                                        .getElementsByTagName('frame');
                    var len = frames.length;
                    for(var i=0; i < len; i++) {
                        var srcVal = serializer.serializeToString(frames[i]
                                                                  .src)
                        //get and add source name.
                        this.htmlString += '\n\n\n ' +
                                        '<!--Added for Trajectory. Src: ' + 
                                        srcVal + '--> \n\n\n';
                    }
                    var iframes = content.document
                                        .getElementsByTagName('iframe');
                    
                    len = iframes.length;
                    for(var i=0; i < len; i++) {
                        var srcVal = iframes[i].contentDocument
                                                .documentElement
                                                .innerHTML
                        //get and add source name.
                        this.htmlString +=  '\n\n\n ' + 
                                            '<!--Added by Stallone. Src: ' + 
                                            '--> \n\n\n' + srcVal;
                    }
                 }
                 if (!this.htmlString) {
                        var errorMsg = "Document has no inner HTML.";
                        this.log("ERROR", errorMsg);
                        return this.getErrorJSONString(errorMsg);
                 }
                 return this.htmlString;

            case "SAVE_HTML_FILE":
                 // Takes a filename as an argument and saves the HTML to 
                 // to the file.
                 if (!this.htmlString && 
                     !content.document.documentElement.innerHTML) {
                        var errorMsg = "Document has no inner HTML.";
                        this.log("ERROR", errorMsg);
                        return this.getErrorJSONString(errorMsg);
                 }
                 if (this.htmlString == '') {
                    this.htmlString = this.handleCommand("GET_HTML", "");
                 }
                 var file = Components.classes["@mozilla.org/file/local;1"]
                                      .createInstance(Components.interfaces
                                                      .nsILocalFile);
                 file.initWithPath(args);
                 file.create(Components.interfaces.nsIFile.NORMAL_FILE_TYPE, 
                             0666);
                 var foStream = Components
                        .classes["@mozilla.org/network/file-output-stream;1"]
                        .createInstance(Components.interfaces
                        .nsIFileOutputStream);
                 foStream.init(file, 0x02 | 0x10|0x20, 0666, 0);
                 var converter = Components
                        .classes["@mozilla.org/intl/converter-output-stream;1"]
                        .createInstance(Components.interfaces
                        .nsIConverterOutputStream);
                 converter.init(foStream, "UTF-8", 0, 0);
                 converter.writeString(this.htmlString, 
                                       this.htmlString.length);
                 converter.close(); 
                 return '{"result":"DONE"}';
  
             case "GET_HTML_LEN":
                 // Returns a string encoded length of the HTML.
                 if (!this.htmlString && 
                     !content.document.documentElement.innerHTML) {
                        var errorMsg = "Document has no inner HTML.";
                        this.log("ERROR", errorMsg);
                        return this.getErrorJSONString(errorMsg);
                 }             
                 if (this.htmlString == '') { 
                    this.htmlString = this.handleCommand("GET_HTML", "");
                 }
                 return this.htmlString.length.toString();
                             
             case "SET_HEADER":
                 // Expects 2 arguments: the name and value of the header to 
                 // be set in that order.
                 this.requestHeaders[args[0]] = args[1];
                 return '{"result":"DONE"}';
                 
            case "SET_PREF":
                /*
                 * Sets the user preference. Expects 3 string arguments. The
                 * arguments are prefName, prefValue and prefType in that 
                 * order. See setPrefs() for further notes on valid argument
                 * values.
                 */
                return this.setPrefs(args[0], args[1], args[2]);

            case "SET_PROXY":
                /*
                 * Takes a list of arguments [proxyType, ip, port]. All values
                 * are string and type is either "http", "socks".
                 */
                //network.proxy.type = 1 (manual configuration)
                //network.proxy.http = ipaddr
                //network.proxy.http_port = port
                //network.proxy.socks = ipaddr
                //network.proxy.socks_port = port
                //network.proxy.socks_version = 5           
                var prefs = Components
                            .classes["@mozilla.org/preferences-service;1"]
                            .getService(Components.interfaces.nsIPrefBranch);
                port = parseInt(args[2])
                prefs.setIntPref("network.proxy.type", 1);
                if(args[0] == "http") {
                     prefs.setCharPref("network.proxy.http", args[1]);
                     prefs.setIntPref("network.proxy.http_port", port);
                } else if(args[0] == "socks") {
                     prefs.setCharPref("network.proxy.socks", args[1]);
                     prefs.setIntPref("network.proxy.socks_port", port);
                     prefs.setIntPref("network.proxy.socks_version", 5);
                } else {
                    var errorMsg = "Proxy type unknown: " + args[0];
                    this.log("ERROR", errorMsg);
                    return this.getErrorJSONString(errorMsg);
                }
                return '{"result":"DONE"}';
                 
             case "DISABLE_PROXY":
                 var prefs = Components
                            .classes["@mozilla.org/preferences-service;1"]
                            .getService(Components.interfaces.nsIPrefBranch);
                 // Proxy value 0 means no proxy.
                 prefs.setIntPref("network.proxy.type", 0);
                 return '{"result":"DONE"}';
                 
             case "SAVE_SCREENSHOT_FILE":
                /*
                 * Takes filepath as the args and saves the screenshot
                 * as that file. Shamelessly refuses to save in any other
                 * format but .png so filepath must end in .png.
                 */
                var filePath = args;
                try {
                    var canvas = TrajLogging.Screenshooter.grab();
                    if (canvas) {
                        TrajLogging.Screenshooter.save(canvas, filePath);
                    } else {
                        var errorMsg = "Screenshooting no canvas";
                        this.log("ERROR", errorMsg);
                        return this.getErrorJSONString(errorMsg);
                    }
                } catch(e) {
                    var errorMsg = "Screenshotting error: " + e.toString();
                    this.log("ERROR", errorMsg);
                    return this.getErrorJSONString(errorMsg);
                }
                return '{"result":"DONE"}';

             case "GET_RESPONSE_CODES":
                /*
                 * Returns a JSON encoded string of
                 * {
                 *     url: responseCode,
                 *     url: responseCode
                 * }
                 */
                if(!this.responsecodesString) {
                    var tempObj = {};
                    for(var url in this.urlInfo) {
                        tempObj[url] = this.urlInfo[url]["responsecode"];
                    }
                    this.responsecodesString = JSON.stringify(tempObj);
                }
                return this.responsecodesString;

             case "GET_RESPONSE_CODES_LEN":
                if(this.responsecodesString == "") {
                    this.responsecodesString = 
                                this.handleCommand("GET_RESPONSE_CODES", "");
                }
                return this.responsecodesString.length.toString();

             case "HAS_PAGE_LOADED":
                if(this.pageLoaded)
                    return '{"result":"True"}';
                else
                    return '{"result":"False"}';

             case "IS_PAGE_ERROR": 
                var error = this.getPageError();
                if (error) {
                    return '{"result":"True"}';
                } else {
                    return '{"result":"False"}';
                }

             case "GET_PAGERANK":
                /*
                 * Returns pagerank calculated using google toolbar. Not in 
                 * use so not being maintained.
                 */
                try {
                    if(!this.pagerankRequest) {
                        this.pagerankRequest = TrajLogging.Pageranker
                                               .reqPagerank(content.document
                                               .location);
                    }
                    this.pagerank = TrajLogging.Pageranker.getPagerank();
                } catch(e) {
                    return '{"result":"ERROR", "message": "' +
                            e.toString() + '"}';
                }
                return '{"result":"' + this.pagerank.toString() + '"}';
             
             case "EVAL_JS":
                /*
                 * Evals the argument passed, and returns the result. 
                 */  
                result_obj = {};
                try {
                    result = eval(args);
                    this.log("INFO", "eval results: " + result);
                    if (!result) {
                    	result = "";
                    } 
                    result_obj['result'] = result;
                } catch(e) {
                    result_obj['result'] = e.toString();
                }
                this.log("INFO", "stringified: " + JSON.stringify(result_obj));
                return JSON.stringify(result_obj);
        }
        }
};
