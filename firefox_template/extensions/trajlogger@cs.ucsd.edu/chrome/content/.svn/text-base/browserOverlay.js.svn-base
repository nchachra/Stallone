/*
 * This initialises the TrajLogging namespace to avoid namespace pollution.
 * 
 * Author: grier@imchris.org
 *         nchachra@cs.ucsd.edu
 */


var TrajLogging = {};

(function() {
    // Registration
    var namespaces = [];

    this.ns = function(fn) {
        var ns = {};
        namespaces.push(fn, ns);
        return ns;
    };
    // Initialization
    this.initialize = function() {
        for(var i = 0; i < namespaces.length; i += 2) {
            var fn = namespaces[i];
            var ns = namespaces[i + 1];
            fn.apply(ns);
        }
        var appcontent = document.getElementById("appcontent");
        if(appcontent) {
        }
        gBrowser.addEventListener("load", TrajLogging.LIB.setPageLoaded, true);
    };
    // Clean up
    this.shutdown = function() {
        window.removeEventListener("load", TrajLogging.initialize, false);
        window.removeEventListener("unload", TrajLogging.shutdown, false);
    };
    // Register handlers to maintain extension life cycle.
    window.addEventListener("load", TrajLogging.initialize, false);
    window.addEventListener("unload", TrajLogging.shutdown, false);
}).apply(TrajLogging);

