//------------------------------------------------------------------------------------//
// Modules
//------------------------------------------------------------------------------------//

'use strict';
const express = require('express');
const cors = require('cors');
const fetch = require("node-fetch");
const cheerio = require("cheerio");
const fs = require('fs');
const serverless = require('serverless-http');
const path = require('path');
const bodyParser = require('body-parser');

//------------------------------------------------------------------------------------//
// Config
//------------------------------------------------------------------------------------//

require('events').EventEmitter.defaultMaxListeners = 15;

const app = express();
const router = express.Router();

// app.use(cors({
//   origin: "*"
//   // origin: "http://webspred.co.uk"    // Allows a certain URL to use this server
// }));

app.set('json spaces', 4);

//------------------------------------------------------------------------------------//
// Server calls
//------------------------------------------------------------------------------------//

router.get("/", async (req, res) => {
  var jsonResponse = {status: "success", body: {results: []}};
  var searchTerm = req.query.searchTerm;
  var time = req.query.recentIndex;
  var num = req.query.num;

  if (!searchTerm) {
    res.json({status: "failed", body: {}, msg: "Provide a search term with 'searchTerm=query'"});
    return;
  }

  var googleSearchString = `https://www.google.com/search?q=${searchTerm}&num=100`;

  if (time === "d" || time === "w" || time === "m") {   // Show google indexes within the past 24 hours | 7 days | 1 month
    googleSearchString += `&as_qdr=${time}`;
  }

  var searchGoogle = CheckGoogleBotLock();

  if (!searchGoogle) {    // If we haven't waited at least an hour, dont search
    res.json({status: "failed", body: {results: [], msg: "Please wait 1 hour till searching again"}});
    return;
  }

  var links = await SearchGoogle(googleSearchString);
  if (links.status === "failed") {
    res.json({status: "failed", body: {results: [], msg: links.body.msg}});
    return;
  }

  links = GetUnique(links.body);
  if (num <= 100) {
    links = links.slice(0, num);
  }
  else {
    res.json({status: "failed", body: {results: [], msg: "Cannot return more than 100 websites"}})
    return;
  }

  for (var link of links) {
      console.log(`Getting info on: ${link}`);
      var result = await CreateJsonInfo(link);
      if (result.status === "success") {
        jsonResponse.body.results.push(result.body);
      }
  }

  res.json(jsonResponse);
  console.log("Responded");
});

app.use(bodyParser.json());
app.use('/.netlify/functions/server', router);  // path must route to lambda
app.use('/', (req, res) => res.sendFile(path.join(__dirname, '../index.html')));

module.exports = app;
module.exports.handler = serverless(app);

//------------------------------------------------------------------------------------//
// Server functions
//------------------------------------------------------------------------------------//

/*
Gets results from a google search. This will return a list of links bases on the search
results with the provided options. The links returned are sorted in order of the search
results but are not weeded for duplicates.
*/
function SearchGoogle(link) {
  return new Promise(async (resolve, reject) => {
    var jsonResponse = {status: "success", body: {}};

    console.log("Getting google searches: " + link);
    // Get HTML of website
    var html, $;
    try {
      html = await (await fetch(link, {
        method: "GET",
        mode: "*cors",
        cache: "no-cache",
        credentials: "same-origin",
        headers: {
          "Content-Type": "text/html"
        },
        redirect: "follow",
        referrerPolicy: "no-referrer"
      })).text();
      $ = cheerio.load(html);
    }
    catch (e) {
      reject({status: "failed", body: {msg: "Could not get google searches for: " + link + "\n" + e}});
    }

    var botDetection = $("#infoDiv");   // Check for Google's bot detection
    if (botDetection) {
      var text = botDetection.text();
      if (text.match(/This page appears when Google automatically detects requests/)) {
        fs.writeFileSync("GoogleBotLock", new Date(new Date().getTime()));    // Write current time and date to file
        reject({status: "failed", body: {msg: "Google detected bot detection"}});
      }
    }

    var links = [];

    var results = $("div[role=heading]").parent().parent().find("a");   // Get the results from the page
    if (results) {
      results.each((i, elem) => {
        var href = $(elem).attr("href");
        if (href) {
          href = href.replace(/^.*?q=/, "");    // Replace the rubbish at the beginning
          links.push(href);
        }
      });
    }
    else {
      reject({status: "failed", body: {msg: "Could not get search results"}});
    }

    jsonResponse.body = links;
    resolve(jsonResponse);
  }).catch(err => {
    console.log(err);
    return({status: "failed", body: {msg: err}});
  });
}

/*
This function will look through an array of links and remove the duplicates based on the
domain.
*/
function GetUnique(links) {
  var correctedArray = [];
  for (var link of links) {
    link = link.replace(/((\.com)|(\.co\.uk)|(\.org(\.uk)?)|(\.uk)|(\.co)).*/, "$1");    // Replace everything after the .com identifier
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
    var identifier = identifier.replace(/^.*?((www)|(uk)|(en))\./, "");   // Replace the first www. or other identifiers
    var identifier = identifier.replace(/\..*$/, "");   // Replace everything after the first "."

    json[identifier] = {    // Create the initial template for information
      website: link,
      facebookPage: {},
      twitterPage: {},
      instagramPage: {},
      contactPage: {}
    };

    // Get HTML of website
    var html, $;
    try {
      html = await (await fetch(link)).text();
      $ = cheerio.load(html);
    }
    catch {
      reject({status: "failed", body: {msg: "Could not get html data of: " + link}});
    }

    var hrefs = $("a[href]");   // Get all hrefs


    // Get Facebook details
    var facebook = (hrefs.filter((i, elem) => {
        return $(elem).attr("href").match(/facebook\.com\/(?!sharer)/);
    })).first();

    if (facebook) {
      var href = facebook.attr("href");
      if (href) {
        json[identifier].facebookPage.link = href.replace(/(\.com\/.*?)\/.*/, "$1");    // Replace everything after the identifier
        json[identifier].facebookPage.status = "success";
      }
    }

    // Get Twitter details
    var twitter = (hrefs.filter((i, elem) => {
      return $(elem).attr("href").match(/twitter\.com\/(?!intent)/);
    })).first();

    if (twitter) {
      var href = twitter.attr("href");
      if (href) {
        json[identifier].twitterPage.link = href.replace(/(\.com\/.*?)\/.*/, "$1");   // Replace everything after the identifier
        json[identifier].twitterPage.status = "success"
      }
    }

    // Get Instagram details
    var instagram = (hrefs.filter((i, elem) => {
      return $(elem).attr("href").match(/instagram\.com\/.*/);
    })).first();

    if (instagram) {
      var href = instagram.attr("href");
      if (href) {
        json[identifier].instagramPage.link = href.replace(/(\.com\/.*?)\/.*/, "$1");   // Replace everything after the identifier
        json[identifier].instagramPage.status = "success"
      }
    }

    // Get Contact details
    var contactPageElem = (hrefs.filter((i, elem) => {
      var link = $(elem).attr("href").replace(/(.*?\/\/.*?\/)|(^\/)/, "");    // Regex out the domain but keep page identifier
      return link.match(/contact/i);
    })).first();

    if (contactPageElem) {
      var contactPage = contactPageElem.attr("href");
      if (contactPage) {
        contactPage = contactPage.replace(/(.*?\/\/.*?\/)|(^\/)/, "");
        contactPage = `${link}/${contactPage}`;
        json[identifier].contactPage.link = contactPage;
        var contactInfo = await GetContactInfo(contactPage);
        if (contactInfo.status === "success") {
          json[identifier].contactPage = {...json[identifier].contactPage, ...contactInfo.body};
        }
      }
    }

    jsonResponse.body = json;
    resolve(jsonResponse);
  }).catch(err => {
    console.log(err);
    return({status: "failed", body: {msg: "Error thrown in CreateJsonInfo Promise"}});
  });
}

/*
This function returns the contact number found in a link provided. Provide a
contact page link for the best result.
*/
function GetContactInfo(link) {
  return new Promise(async (resolve, reject) => {
    var jsonResponse = {status: "success", body: {
      number: "",
      email: ""
    }};

    // Get HTML of website
    var html, $;
    try {
      html = await (await fetch(link)).text();
      $ = cheerio.load(html);
    }
    catch {
      reject({status: "failed", body: {numer: "", email: "", msg: "Failed to get contact page HTML for: " + link}});
    }

    var textElems = $("body *").filter((i, elem) => {   // Get all text elements
      return $(elem).text();
    });

    // Get contact number
    var contactNumberElem = (textElems.filter((i, elem) => {    // Get all numbers that match 11 digits
      if ($(elem).text().match(/.*\d[\d\s]{10,12}.*/)) {
        var number = $(elem).text().replace(/\D/, "");
        return number.length == 11;
      }
    })).first();

    if (contactNumberElem) {
      var contactNumber = $(contactNumberElem).text().replace(/\D/, "");
      if (contactNumber) {
        jsonResponse.body.number = contactNumber;
      }
    }

    // Get contact email
    var emailElem = (textElems.filter((i, elem) => {
      return $(elem).text().match(/\s\w+@\w+[\.\w]+\s/);
    })).first();

    if (emailElem) {
      var email = $(emailElem).text();
      if (email) {
        jsonResponse.body.email = email.match(/\s(\w+@\w+[\.\w]+)\s/)[1];
      }
    }

    resolve(jsonResponse);
  }).catch(err => {
    console.log(err);
    return({status: "failed", body: {number: "", email: "", msg: "Error thrown in GetContactInfo Promise"}});
  });
}

function CheckGoogleBotLock() {
  var lock = "GoogleBotLock";
  if (fs.existsSync(lock)) {    // If file exists
    var time = fs.readFileSync(lock, "utf8");
    if ((Date.parse(time) + (60*60000)) <= new Date().getTime()) {    // If 1 hour has passed
      fs.unlinkSync(lock);
      return true;    // Allow for searching by returning true
    }
    return false;   // If 1 hour hasn't passed then don't allow searching
  }
  return true;    // If file doesn't exist then allow for searching
}