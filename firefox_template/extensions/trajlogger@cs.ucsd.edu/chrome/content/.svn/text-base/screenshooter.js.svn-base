/*
 * Module for capturing screenshot. Code based on ScreenGrab extension.
 * 
 * Author: nchachra@cs.ucsd.edu
 */

TrajLogging.Screenshooter = {
    
    /*
     * Returns a canvas with a screenshot of the current page.
     */
    grab : function() {
        var browser = gBrowser.selectedBrowser;
        var win = browser.contentWindow;
        var windowBorder = (window.outerWidth - window.innerWidth) / 2;
        var w = win.innerWidth;
        var h = win.innerHeight;
        var document = content.document;
        var documentElement = document.documentElement;
        var canvas = document.getElementById('trajlogger-screenshot-canvas');
        if(canvas == null) {
            canvas = document.createElementNS("http://www.w3.org/1999/xhtml", 
                                              "canvas");
            canvas.id = 'trajlogger-screenshot-canvas';
            if(canvas.style) {
                canvas.style.display = 'none';
            }
            documentElement.appendChild(canvas);
        }
        var width = null;
        var height = null;
        if(document.body) {
            if(document.body.scrollWidth) {
                width = Math.max(documentElement.scrollWidth, 
                                 document.body.scrollWidth);
            }
            if(document.body.scrollHeight) {
                height = Math.max(documentElement.scrollHeight, 
                                  document.body.scrollHeight);
            }
        }
        if(width) {
            canvas.width = width;
        } else {
            canvas.width = 1500;
        }
        if(height) {
            canvas.height = height;
        } else {
            canvas.height = 2000;
        }
        fudge = win.scrollMaxY;
        
        var context = canvas.getContext('2d');
        context.clearRect(0, 0, width, height);
        context.save();
        context.drawWindow(win, 0, 0, width, height + fudge, 
                           "rgb(255,255,255)");
        context.restore();
        return canvas;
    },

    /*
     * Saves the canvas to a .png file.
     */
    save : function(canvas, filepath) {
        var cc = Components.classes;
        var ci = Components.interfaces;
        var dataUrl = canvas.toDataURL('image/png');
        var ioService = cc['@mozilla.org/network/io-service;1']
                            .getService(ci.nsIIOService);
        var dataUri = ioService.newURI(dataUrl, 'UTF-8', null);
        var channel = ioService.newChannelFromURI(dataUri);
        var file = cc['@mozilla.org/file/local;1']
                            .createInstance(ci.nsILocalFile);
        file.initWithPath(filepath);
        var inputStream = channel.open();
        var binaryInputStream = cc['@mozilla.org/binaryinputstream;1']
                                    .createInstance(ci.nsIBinaryInputStream);
        binaryInputStream.setInputStream(inputStream);
        var fileOutputStream = 
                        cc['@mozilla.org/network/safe-file-output-stream;1']
                        .createInstance(ci.nsIFileOutputStream);
        fileOutputStream.init(file, -1, -1, null);
        var n = binaryInputStream.available();
        var bytes = binaryInputStream.readBytes(n);
        fileOutputStream.write(bytes, n);
        if( fileOutputStream instanceof ci.nsISafeOutputStream) {
            fileOutputStream.finish();
        } else {
            fileOutputStream.close();
        }
    }
}