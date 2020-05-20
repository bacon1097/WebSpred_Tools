//------------------------------------------------------------------------------------//
// Modules
//------------------------------------------------------------------------------------//

const express = require('express')
var cors = require('cors');
const app = express();
const puppet = require("puppeteer");

//------------------------------------------------------------------------------------//
// Config
//------------------------------------------------------------------------------------//

app.use(cors({
  origin: "*"
  // origin: "http://webspred.co.uk"
}));

app.set('json spaces', 4);

//------------------------------------------------------------------------------------//
// Server calls
//------------------------------------------------------------------------------------//

app.get("/", async (req, res) => {
  var jsonResponse = {status: "success"};
  var searchTerm = req.query.searchTerm;
  var time = req.query.recentIndex;
  var num = req.query.num;

  if (!searchTerm) {
    res.json({status: "failed", body: {}});
    return;
  }

  var googleSearchString = `https://www.google.com/search?q=${searchTerm}`;

  if (time === "d" || time === "w" || time === "m") {   // Show google indexes within the past 24 hours | 7 days | 1 month
    googleSearchString += `&as_qdr=${time}`;
  }

  if (num) {
    googleSearchString += `&num=${num}`;
  }
  else {
    googleSearchString += `&num=100`;   // By default return the max of 100 results
  }

  var links = [];
  try {
    links = await SearchGoogle(googleSearchString);
    if (links.status === "failed" || !links.body) {
      res.json({status: "failed", body: {}});
      return;
    }
  }
  catch (err) {
    console.log(err);
    res.json({status: "failed", body: {}});
    return;
  }

  var json = [];
  for (var link of links.body) {
    try {
      var result = await CreateJsonInfo(link)
      if (result === "failed") {
        res.json({status: "failed", body: {}});
        return;
      }
      json.push(result.body);
    }
    catch (err) {
      console.log(err);
      continue;
    }
  }
  console.log(json);
});

app.listen(8889, () => {
  console.log('Example app listening on port 8889!');
});

//------------------------------------------------------------------------------------//
// Server functions
//------------------------------------------------------------------------------------//

function SearchGoogle(url) {
  return new Promise(async (resolve, reject) => {
    var jsonResponse = {status: "success", body: {}};

    const browser = await puppet.launch();
    const page = await browser.newPage();
    await page.goto(url).catch(err => {
      console.log(err);
      return({status: "failed", body: {}});
    });

    var results = await page.$x('//h3/../../a');
    var links = [];
    if (results) {
      for (var elem of results) {
        var link = await elem.getProperty("href");
        link = await link.jsonValue();
        console.log(link);
        if (link !== undefined && link != "") {
          links.push(link);
        }
      };
    }

    browser.close();

    jsonResponse.body = links;
    resolve(jsonResponse);
  }).catch(err => {
    console.log(err);
    return({status: "failed", body: {}});
  });
}

function CreateJsonInfo(link) {
  return new Promise(async (resolve, reject) => {
    var jsonResponse = {status: "success", body: {}};

    var json = {};
    var link = link.replace(/((\.com)|(\.co\.uk)|(\.org(\.uk)?)|(\.uk)).*/, "");    // Replace everything after the .com identifier
    var identifier = link.replace(/^.*?\/\//, "");    // Replace everything up to the first //
    var identifier = identifier.replace(/^.*?www\./, "");   // Replace the first www.
    var identifier = identifier.replace(/\..*$/, "");   // Replace everything after the first dot
    json.identifier = identifier;

    var result = {};
    try {
      result = await GetInfo(link);
      if (result.status === "failed" || !result.body) {
        return({status: "failed", body: {}});
      }
    }
    catch (err) {
      console.log(err);
      return({status: "failed", body: {}});
    }

    json = {...json, ...result.body}

    jsonResponse.body = json;
    resolve(jsonResponse);
  }).catch(err => {
    console.log(err);
    return({status: "failed", body: {}});
  });
}

function GetInfo(link) {
  return new Promise(async (resolve, reject) => {
    var jsonResponse = {status: "success", body: {}};

    var info = {};

    const browser = await puppet.launch();
    const page = await browser.newPage();
    await page.goto(link);

    var [facebook] = await page.$x('//a[contains(@href, "facebook.com") and not(contains(@href, "sharer"))]');
    if (facebook) {
      var href = await (await facebook.getProperty("href")).jsonValue();
      info.facebookPage.link = href;
      info.facebookPage.status = "success";
    }

    var [twitter] = await page.$x('//a[contains(@href, "twitter.com") and not(contains(@href, "intent"))]');
    if (twitter) {
      var href = await (await twitter.getProperty("href")).jsonValue();
      info.twitterPage.link = href;
      info.twitterPage.status = "success"
    }

    var [instagram] = await page.$x('//a[contains(@href, "instagram.com")]');
    if (instagram) {
      var href = await (await instagram.getProperty("href")).jsonValue();
      info.instagramPage.link = href;
      info.instagramPage.status = "success";
    }

    var [contactPage] = await page.$x('//a[contains(lower-case(text()), "contact")]');
    if (contactPage) {
      var contactLink = link + "/" + (await (await contactPage.getProperty("href")).jsonValue()).replace(/((.*?)\/\/(.*?)\/)|^\//, "");
      info.contactPage.link = contactLink;
      await GetContactInfo(contactLink);
    }

    jsonResponse.body = info;
    resolve(jsonResponse);
  }).catch(err => {
    console.log(err);
    return({status: "failed"});
  });
}

function GetContactInfo(link) {
  return new Promise((resolve, reject) => {
    var jsonResponse = {status: "success", body: {}};

    const browser = await puppet.launch();
    const page = await browser.newPage();
    await page.goto(link);

    
  }).catch(err => {
    console.log(err);
    return({status: "failed", body: {}});
  });
}