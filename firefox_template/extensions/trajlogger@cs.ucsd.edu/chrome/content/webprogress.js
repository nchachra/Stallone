/*
 * Tracks a page's progress, handling events appropriately.
 *
 *
 * Author: grier@imchris.org
 * Author: nchachra@cs.ucsd.edu
 */

TrajLogging.ns(function() {

    TrajLogging.WebProgress = {
        
        STATE_IS_DOCUMENT : Components.interfaces.nsIWebProgressListener
                            .STATE_IS_DOCUMENT,

        STATE_STOP : Components.interfaces.nsIWebProgressListener.STATE_STOP,

        srcLoggerWebListener : {
            QueryInterface : function(aIID) {
                if(aIID.equals(Components.interfaces.nsIWebProgressListener) ||
                 aIID.equals(Components.interfaces.nsISupportsWeakReference) ||
                 aIID.equals(Components.interfaces.nsISupports))
                    return this;
                throw Components.results.NS_NOINTERFACE;
            },
           
            onStateChange : function(aProgress, aRequest, aFlag, aStatus) {
                if((aFlag & this.STATE_STOP) && 
                    (aFlag & this.STATE_IS_DOCUMENT)) {
                }
                return 0;
            },
            
            onLocationChange : function(aProgress, aRequest, aURI) {
                if(aURI.asciiSpec == content.document.location) {
                    TrajLogging.LIB.addRedirect(aURI.asciiSpec);
                }
                return 0;
            },
            
            onProgressChange : function(aProgress, aRequest, curSelfProgress, 
                    maxSelfProgress, curTotalProgress, maxTotalProgress) {
                return 0;
            },
            
            onStatusChange : function(aProgress, aRequest, stat, message) {
                return 0;
            },
            
            onSecurityChange : function() {
                return 0;
            },
            
            onLinkIconAvailable : function() {
                return 0;
            }
        },

        init : function(aEvent) {
            var progress = Components
                .classes["@mozilla.org/docloaderservice;1"]
                .getService(Components.interfaces.nsIWebProgress);
            progress.addProgressListener(this.srcLoggerWebListener, 
                   Components.interfaces.nsIWebProgress.NOTIFY_LOCATION);
            getBrowser().addEventListener('DOMContentLoaded', function(aEvent){
                    if(aEvent.target.nodeName == '#document') {
                        //TODO: If DOMWillOpenModalDialog fires, set a flag to 
                        // true. Soon after, if this event is fired, the 
                        // nodename is #document, find it's corresponding
                        // window, and close it. Modal dialogs like server
                        // authentications are not closed by firefox 
                        // properties, even though the preventDefault below
                        // alleviates the problem.
                }
            }, false);
            getBrowser().addEventListener('DOMWillOpenModalDialog', 
                    function(aEvent) {
                       aEvent.preventDefault();
                    }, false);
        },
        
        uninit : function() {
            var progress = Components
                            .classes["@mozilla.org/docloaderservice;1"]
                            .getService(Components.interfaces.nsIWebProgress);
            progress.removeProgressListener(this.srcLoggerWebListener);
        }
    }
});
