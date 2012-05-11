/*
 * Server that listens for TCP connections.
 *
 *
 * Author: grier@imchris.org
 *         nchachra@cs.ucsd.edu
 */

TrajLogging.ns(function() {
    TrajLogging.Command = {
        _serverSocket : 0,
        _serverPort : 7055,

        serverStart : function() {
            var lib = TrajLogging.LIB;
            // Listener for performing actions when a connection is
            // established.
            var listener = {
                onSocketAccepted : function(socket, transport) {
                    try {
                        var outputStream = transport.openOutputStream(0, 0, 0);

                        var inputStream = transport.openInputStream(0, 0, 0);
                        var instream = Components
                              .classes["@mozilla.org/scriptableinputstream;1"]
                              .createInstance(Components.interfaces
                              .nsIScriptableInputStream);
                        instream.init(inputStream);

                        var inputString = "";
                        while(inputString == "") {
                            inputString += instream.read(instream.available());
                        }
                        // the input command should be JSON
                        lib.log("INFO", "Received: " + inputString);
                        var command = JSON.parse(inputString);

                        // handle the command
                        lib.log("INFO", "Handing " + command);
                        var outputString =lib.handleCommand(command['command'],
                                                              command['args']);
                        // report the results
                        lib.log("INFO", "Sending: " + outputString);
                        tot = 0;
                        len = outputString.length;
                        while(tot < len) {
                            try {
                                n = outputStream.write(outputString
                                                .substring(tot), (len - tot));
                                tot += n;
                            } catch(e) {
                                if(e.name == "NS_BASE_STREAM_WOULD_BLOCK") {
                                    lib.log("ERROR", 
                                                   "Blocking exc, continuing");
                                } else {
                                    lib.log("ERROR", 
                                            "Unknown exc: " + e.name + 
                                            " Message: " + e.toString());
                                    //throw e;
                                }
                            }
                        }
                        outputStream.close();
                    } catch(ex2) {
                        TrajLogging.LIB.log("ERROR", "Exception: " + 
                                            ex2.name + " Message: " + 
                                            e.toString());
                    }
                },
                onStopListening : function(socket, status) {
                }
            };

            // Start the server.
            try {
                this._serverSocket = Components
                            .classes["@mozilla.org/network/server-socket;1"]
                            .createInstance(Components.interfaces
                            .nsIServerSocket);
                this._serverSocket.init(this._serverPort, false, -1);
                this._serverSocket.asyncListen(listener);
            } catch(ex) {
                Components.utils.reportError(ex);
            }
        },
        /*
         * Closes the socket.
         */
        serverStop : function() {
            if(this._serverSocket)
                this._serverSocket.close();
        },
        /*
         * Starts server on portnum.
         */
        serverUsePort : function(portnum) {
            this.serverStop();
            this._serverPort = parseInt(portnum);
            this.serverStart();
        },
        init : function() {
            this.serverStart();
        },
        uninit : function() {
            TrajLogging.LIB.log("INFO", "Server stopped.");
            this.serverStop();
        }
    }
});
