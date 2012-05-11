/*
 * Tools for observing and manipulating HTTP traffic.
 * 
 * 
 * Author: grier@imchris.org
 *         dywang@cs.ucsd.edu
 */

TrajLogging.ns(function() {
        TrajLogging.HTTPObserver = {

            HttpObserver : {
                setHeaders : [],

                headerVisitor : {
                    // The headers from this visit.
                    theHeaders : {},

                    visitHeader : function(aHeader, aValue) {
                        this.theHeaders[aHeader] = aValue;
                    },
                    
                    getheaders : function() {
                        return this.theHeaders;
                    },
                    
                    clearheaders : function() {
                        this.theHeaders = {};
                    },
                },

                observe : function(subject, topic, data) {
                    var lib = TrajLogging.LIB;
                    if(!(subject instanceof 
                                    Components.interfaces.nsIHttpChannel)) {
                        lib.log("ERROR", 'Non-http request ' + subject.name);
                        return;
                    }

                    if((topic == "http-on-examine-response") || 
                        (topic == "http-on-examine-cached-response")) {
                        subject.QueryInterface(Components.interfaces
                                               .nsIHttpChannel);
                        lib.addResponseStatus(subject.name, 
                                              subject.responseStatus);

                        // Handle 30X headers
                        response = String(subject.responseStatus);

                        if(response.search(/30\d/) != -1) {
                            // Parse request uri (head) and response uri (tail)
                            head = subject.name;

                            try {
                                tail = subject.getResponseHeader('Location');
                            } catch (e) {
                                if (e.name == "NS_ERROR_NOT_AVAILABLE") {
                                    tail = null;
                                }
                            }

                            // Update header redirect chain
                            if(tail != null) {
                                // Find an existing header redirect chain
                                found = false;
                                for( i = 0; 
                                    i < lib.redirectsHeaders.length; i++) {
                                     redirectHeader = lib.redirectsHeaders[i];
                                    if(redirectHeader.tail == head) {
                                        redirectHeader.chain
                                                    .push(redirectHeader.tail);
                                        redirectHeader.tail = tail;
                                        found = true;
                                        break;
                                    }
                                }
                                // Not found
                                if(!found) {
                                    redirectHeader = new Object();
                                    redirectHeader.tail = tail;
                                    redirectHeader.chain = [head];

                                    TrajLogging.LIB.redirectsHeaders
                                                        .push(redirectHeader);
                                }
                            }
                        }

                        subject.visitResponseHeaders(this.headerVisitor);
                        lib.addHeaders(subject.name, 
                                       this.headerVisitor.theHeaders);
                        this.headerVisitor.clearheaders();
                    } else if(topic == "http-on-modify-request") {
                        for(var i in lib.requestHeaders) {
                            subject.setRequestHeader(i, lib.requestHeaders[i], 
                                                    false);
                        }
                    }
                },

                register : function() {
                    var observerService = Components
                            .classes["@mozilla.org/observer-service;1"]
                            .getService(Components.interfaces
                            .nsIObserverService);
                    observerService.addObserver(this, 
                                      "http-on-modify-request", false);
                    observerService.addObserver(this, 
                                     "http-on-examine-response", false);
                    observerService.addObserver(this, 
                                     "http-on-examine-cached-response", false);
                },
                
                unregister : function() {
                    var observerService = Components
                                .classes["@mozilla.org/observer-service;1"]
                                .getService(Components.interfaces
                                .nsIObserverService);
                    observerService.removeObserver(this, 
                                             "http-on-modify-request");
                    observerService.removeObserver(this, 
                                            "http-on-examine-response");
                    observerService.removeObserver(this, 
                                            "http-on-examine-cached-response");
                },
            },
            
            init : function() {
                TrajLogging.LIB.log("INFO", 'httpobserver startup');
                this.HttpObserver.register();
            },
            
            uninit : function() {
                log("INFO", 'httpobserver shutdown');
                this.HttpObserver.unregister();
            }
        }
});
