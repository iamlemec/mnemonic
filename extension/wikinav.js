// send wikipedia info back to home base

storeURL = "http://dohan.dyndns.org:9001/store";

// custom store URL
/*
storeURL = null;
browser.storage.sync.get("nemonicStoreURL")
    .then((storedSettings) => {
        if (storedSettings.nemonicStoreURL) {
            storeURL = storedSettings.nemonicStoreURL;
            console.log('loaded:', storeURL);
        }
    })
    .catch(() => {
        console.log("Error retrieving stored settings!");
    })

browser.storage.onChanged.addListener((newSettings) => {
    storeURL = newSettings.nemonicStoreURL;
    console.log('changed:', storeURL);
});
*/

// hook for going to Wikipedia
browser.webNavigation.onCommitted.addListener((e) => {
    /*
    if (storeURL == null) {
        console.log("No store URL!");
        return;
    }
    */
    var url = e.url;
    var timestamp = e.timeStamp;
    console.log(url);
    if (/^https?:\/\/[a-z]{2}\.wikipedia\.org/g.test(url)) {
        var xmlhttp = new XMLHttpRequest();
        xmlhttp.open("POST", storeURL);
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
