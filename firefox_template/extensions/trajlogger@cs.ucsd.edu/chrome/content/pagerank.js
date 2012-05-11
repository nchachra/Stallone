/*
 * Module for retrieving pagerank using Google Toolbar. 
 * Currently not in use, so not maintained.
 * 
 * 
 * Author: nchachra@cs.ucsd.edu
 */

TrajLogging.Pageranker = {

    gXMLHttpRequest : null,
    glastpr : null,
    gch : 0,

    init : function() {
        this.gXMLHttpRequest = null;
        this.glastpr = null;
        this.gch = 0;
        this.pagerank = -1;
    },
    hexdec : function(str) {
        return parseInt(str, 16);
    },
    zeroFill : function(a, b) {
        var z = this.hexdec(80000000);
        if(z & a) {
            a = a >> 1;
            a &= ~z;
            a |= 0x40000000;
            a = a >> (b - 1);
        } else {
            a = a >> b;
        }
        return (a);
    },
    mix : function(a, b, c) {
        a -= b;
        a -= c;
        a ^=(this.zeroFill(c, 13));
        b -= c;
        b -= a;
        b ^=(a << 8);
        c -= a;
        c -= b;
        c ^=(this.zeroFill(b, 13));
        a -= b;
        a -= c;
        a ^=(this.zeroFill(c, 12));
        b -= c;
        b -= a;
        b ^=(a << 16);
        c -= a;
        c -= b;
        c ^=(this.zeroFill(b, 5));
        a -= b;
        a -= c;
        a ^=(this.zeroFill(c, 3));
        b -= c;
        b -= a;
        b ^=(a << 10);
        c -= a;
        c -= b;
        c ^=(this.zeroFill(b, 15));
        var ret = new Array((a), (b), (c));
        return ret;
    },
    GoogleCH : function(url, length) {
        var init = 0xE6359A60;
        if(arguments.length == 1)
            length = url.length;
        var a = 0x9E3779B9;
        var b = 0x9E3779B9;
        var c = 0xE6359A60;
        var k = 0;
        var len = length;
        var mixo = new Array();
        while(len >= 12) {
            a += (url[k + 0] + (url[k + 1] << 8) + (url[k + 2] << 16) + (url[k + 3] << 24));
            b += (url[k + 4] + (url[k + 5] << 8) + (url[k + 6] << 16) + (url[k + 7] << 24));
            c += (url[k + 8] + (url[k + 9] << 8) + (url[k + 10] << 16) + (url[k + 11] << 24));
            mixo = this.mix(a, b, c);
            a = mixo[0];
            b = mixo[1];
            c = mixo[2];
            k += 12;
            len -= 12;
        }
        c += length;
        switch(len) {
            case 11:
                c += url[k + 10] << 24;
            case 10:
                c += url[k + 9] << 16;
            case 9 :
                c += url[k + 8] << 8;
            case 8 :
                b += (url[k + 7] << 24);
            case 7 :
                b += (url[k + 6] << 16);
            case 6 :
                b += (url[k + 5] << 8);
            case 5 :
                b += (url[k + 4]);
            case 4 :
                a += (url[k + 3] << 24);
            case 3 :
                a += (url[k + 2] << 16);
            case 2 :
                a += (url[k + 1] << 8);
            case 1 :
                a += (url[k + 0]);
        }
        mixo = this.mix(a, b, c);
        if(mixo[2] < 0)
            return (0x100000000 + mixo[2]);
        else
            return mixo[2];
    },
    strord : function(string) {
        var result = new Array();
        for( i = 0; i < string.length; i++) {
            result[i] = string[i].charCodeAt(0);
        }
        return result;
    },
    c32to8bit : function(arr32) {
        var arr8 = new Array();
        for( i = 0; i < arr32.length; i++) {
            for( bitOrder = i * 4; bitOrder <= i * 4 + 3; bitOrder++) {
                arr8[bitOrder] = arr32[i] & 255;
                arr32[i] = this.zeroFill(arr32[i], 8);
            }
        }
        return arr8;
    },
    myfmod : function(x, y) {
        var i = Math.floor(x / y);
        return (x - i * y);
    },
    GoogleNewCh : function(ch) {
        ch = (((ch / 7) << 2) | ((this.myfmod(ch, 13)) & 7));
        prbuf = new Array();
        prbuf[0] = ch;
        for( i = 1; i < 20; i++) {
            prbuf[i] = prbuf[i - 1] - 9;
        }
        ch = this.GoogleCH(this.c32to8bit(prbuf), 80);
        return ch;

    },
    setPagerankStatus : function() {
        that = TrajLogging.Pageranker;
        req = that.gXMLHttpRequest;
        var temp = req.responseText;
        if(temp) {
            var foo = temp.match(/Rank_.*?:.*?:(\d+)/i);
            var pr = (foo) ? foo[1] : "-1";
            foo = temp.match(/FVN_.*?:.*?:(?:Top\/)?([^\s]+)/i);
            var cat = (foo) ? foo[1] : "n/a";
            var iscat = (cat == "n/a") ? "" : "cat";
            that.glastpr = pr;

        } else {
            that.glastpr = -1;
        }
        that.pagerank = that.glastpr;
    },
    URLencode : function(sStr) {
        return encodeURIComponent(sStr).replace(/\+/g, "%2B").replace(/\//g, "%2F");
    },
    reqPagerank : function(sentURL) {
        var url = new String(sentURL);
        url = url.replace(/\?.*$/g, '?');
        var reqgr = "info:" + url;
        var reqgre = "info:" + this.URLencode(url);
        this.gch = this.GoogleCH(this.strord(reqgr));
        this.gch = "6" + this.GoogleNewCh(this.gch);
        var querystring = "http://toolbarqueries.google.com/search?client=navclient-auto&ch=" + this.gch + "&ie=UTF-8&oe=UTF-8&features=Rank:FVN&q=" + reqgre;
        this.gXMLHttpRequest = new XMLHttpRequest();

        this.gXMLHttpRequest.addEventListener("load", this.setPagerankStatus, false);
        this.gXMLHttpRequest.open("GET", querystring, true);
        this.gXMLHttpRequest.setRequestHeader("User-Agent", "Mozilla/4.0 (compatible; GoogleToolbar 2.0.114-big; Windows XP 5.1)");
        this.gXMLHttpRequest.send(null);
        return this.gXMLHttpRequest;

    },
    getPagerank : function() {
        return this.pagerank || -1;
    }
};
