//------------------------------------------------------------------------------------//
// Modules
//------------------------------------------------------------------------------------//

const express = require('express');
const cors = require('cors');
const app = express();
const puppet = require("puppeteer");

//------------------------------------------------------------------------------------//
// Config
//------------------------------------------------------------------------------------//

require('events').EventEmitter.defaultMaxListeners = 15;

app.use(cors({
  origin: "*"
  // origin: "http://webspred.co.uk"    // Allows a certain URL to use this server
}));

app.set('json spaces', 4);

//------------------------------------------------------------------------------------//
// Server calls
//------------------------------------------------------------------------------------//

app.get("/", async (req, res) => {
  var jsonResponse = {status: "success", body: {results: []}};
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

  links = GetUnique(links.body);

  for (var link of links) {
    try {
      console.log(`Getting info on: ${link}`);
      var result = await CreateJsonInfo(link)
      if (result === "failed" || !result.body) {
        res.json({status: "failed", body: {}});
        return;
      }
      jsonResponse.body.results.push(result.body);
    }
    catch (err) {
      console.log(err);
      continue;
    }
  }

  res.json(jsonResponse);
});

app.listen(8889, () => {
  console.log('Example app listening on port 8889!');
});

//------------------------------------------------------------------------------------//
// Server functions
//------------------------------------------------------------------------------------//

/*
Gets results from a google search. This will return a list of links bases on the search
results with the provided options. The links returned are sorted in order of the search
results but are not weeded for duplicates.
*/
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

/*
This function will look through an array of links and remove the duplicates based on the
domain.
*/
function GetUnique(links) {
  var correctedArray = [];
  for (var link of links) {
    link = link.replace(/((\.com)|(\.co\.uk)|(\.org(\.uk)?)|(\.uk)).*/, "$1");    // Replace everything after the .com identifier
    correctedArray.push(link);
  }
  correctedArray = [...new Set(correctedArray)];
  return correctedArray;
}

/*
This function will return information such as contact info and social media stats and links.
This function is the parent function that calls other functions to get the specific data
from social media sites.
*/
function CreateJsonInfo(link) {
  return new Promise(async (resolve, reject) => {
    var jsonResponse = {status: "success", body: {}};

    var json = {};
    var identifier = link.replace(/^.*?\/\//, "");    // Replace everything up to the first //
    var identifier = identifier.replace(/^.*?www\./, "");   // Replace the first www.
    var identifier = identifier.replace(/\..*$/, "");   // Replace everything after the first "."

    json[identifier] = {    // Create the initial template for information
      facebookPage: {},
      twitterPage: {},
      instagramPage: {},
      contactPage: {}
    };

    const browser = await puppet.launch();
    const page = await browser.newPage();
    await page.goto(link);    // Get HTML of link

    // Get Facebook details
    var [facebook] = await page.$x('//a[contains(@href, "facebook.com") and not(contains(@href, "sharer"))]');
    if (facebook) {
      var href = await (await facebook.getProperty("href")).jsonValue();
      json[identifier].facebookPage.link = href;
      json[identifier].facebookPage.status = "success";
    }

    // Get Twitter details
    var [twitter] = await page.$x('//a[contains(@href, "twitter.com") and not(contains(@href, "intent"))]');
    if (twitter) {
      var href = await (await twitter.getProperty("href")).jsonValue();
      json[identifier].twitterPage.link = href;
      json[identifier].twitterPage.status = "success"
    }

    // Get Instagram details
    var [instagram] = await page.$x('//a[contains(@href, "instagram.com")]');
    if (instagram) {
      var href = await (await instagram.getProperty("href")).jsonValue();
      json[identifier].instagramPage.link = href;
      json[identifier].instagramPage.status = "success";
    }

    // Get contact details
    var contactPageLinks = await page.$x('//a');
    var contactPage;
    for (var tempPage of contactPageLinks) {
      try {
        var tempLink = (await (await tempPage.getProperty("href")).jsonValue()).replace(/((.*?)\/\/(.*?)\/)|^\//, "");
        if (tempLink.match(/contact/i)) {
          contactPage = tempLink;
        }
      }
      catch (err) {}
    }

    if (contactPage) {
      contactPage = `${link}/${contactPage}`;
      json[identifier].contactPage.link = contactPage;
      try {
        var contactInfo = await GetContactInfo(contactPage);
        if (contactInfo.status === "failed" || !contactInfo.body) {
          return ({status: "failed", body: {}});
        }
        json[identifier].contactPage = {...json[identifier].contactPage, ...contactInfo.body};
      }
      catch (err) {
        console.log(err);
        return({status: "failed", body: {}});
      }
    }

    jsonResponse.body =  json;
    resolve(jsonResponse);
  }).catch(err => {
    console.log(err);
    return({status: "failed", body: {}});
  });
}

/*
This function returns the contact number found in a link provided. Provide a
contact page link for the best result.
*/
function GetContactInfo(link) {
  return new Promise(async (resolve, reject) => {
    var jsonResponse = {status: "success", body: {}};

    const browser = await puppet.launch();
    const page = await browser.newPage();
    await page.goto(link);

    resolve(jsonResponse);
  }).catch(err => {
    console.log(err);
    return({status: "failed", body: {}});
  });
}