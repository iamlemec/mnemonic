// Copyright (c) 2012 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Event listner for clicks on links in a browser action popup.
// Open the link in a new tab of the current window.
function onAnchorClick(event) {
    chrome.tabs.create({
        selected: true,
        url: event.srcElement.href
    });
    return false;
}

// Given an array of URLs, build a DOM list of those URLs in the
// browser action popup.
function buildPopupDom(divName, data) {
    var popupDiv = document.getElementById(divName);

    var ul = document.createElement('ul');
    popupDiv.appendChild(ul);

    for (var i = 0, ie = data.length; i < ie; ++i) {
        var a = document.createElement('a');
        a.href = data[i];
        a.appendChild(document.createTextNode(data[i]));
        a.addEventListener('click', onAnchorClick);

        var li = document.createElement('li');
        li.appendChild(a);

        ul.appendChild(li);
    }
}

// Search history to find up to ten links that a user has typed in,
// and show those links in a popup.
function buildTypedUrlList(divName) {
    // To look for history items visited in the last week,
    // subtract a week of microseconds from the current time.
    var microsecondsPerWeek = 1000 * 60 * 60 * 24 * 7;
    var oneWeekAgo = (new Date).getTime() - microsecondsPerWeek;

    // to display
    chrome.history.search({
        'text': '',              // Return every history item....
        'startTime': oneWeekAgo  // that was accessed less than one week ago.
    }, function(historyItems) {
        var urlArray = [];
        for (var i = 0; i < historyItems.length; ++i) {
            var url = historyItems[i].url;
            if (/^https?:\/\/[a-z]{2}\.wikipedia\.org/g.test(url)) {
                urlArray.push(url);
            }
        }
        buildPopupDom(divName, urlArray.slice(0, 10));
    });
}

chrome.webNavigation.onCommitted.addListener(function (e) {
    var url = e.url;
    var timestamp = e.timeStamp;
    console.log(url);
    if (/^https?:\/\/[a-z]{2}\.wikipedia\.org/g.test(url)) {
        var xmlhttp = new XMLHttpRequest();
        xmlhttp.open("POST", "http://dohan.dyndns.org:9001/store");
        xmlhttp.onreadystatechange = function() {
            if (xmlhttp.readyState == XMLHttpRequest.DONE) {
                if(xmlhttp.status == 200){
                    console.log("Response: " + xmlhttp.responseText);
                } else {
                    console.log("Error: " + xmlhttp.statusText);
                }
            }
        }
        xmlhttp.send(JSON.stringify({
            url: url,
            timestamp: timestamp
        }));
    }
});
