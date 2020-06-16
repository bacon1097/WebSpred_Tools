#!/usr/bin/env node
//------------------------------------------------------------------------------------//
// Modules
//------------------------------------------------------------------------------------//

'use strict';
const fetch = require("node-fetch");
const cheerio = require("cheerio");
const fs = require('fs');
const args = require('yargs').argv;

//------------------------------------------------------------------------------------//
// Config
//------------------------------------------------------------------------------------//

require('events').EventEmitter.defaultMaxListeners = 15;
var fail = false;
if (!args.searchTerm) {
  console.log("Please provide a search term for google with '--searchTerm'");
  fail = true;
}
if (!args.results || !(args.results > 0 && args.results <= 100)) {
  console.log("Please a number (above 0 and below 101) of results to return with '--results'");
  fail = true;
}
try {
  parseInt(args.results);
}
catch {
  console.log("Please pass an integer to --results");
  fail = true;
}
if (fail) {
  return;
}

//------------------------------------------------------------------------------------//
// Functions
//------------------------------------------------------------------------------------//

/*
This function calls the other functions to get information on websites that google
responds with.
*/
async function GetProspects(searchTerm, results, time) {
  var jsonResponse = {status: "success", body: {results: []}};

  if (!searchTerm) {
    console.log(JSON.stringify({status: "failed", body: {msg: "Provide a search term with 'searchTerm=query'"}}, null, 2));
    return;
  }

  var googleSearchString = `https://www.google.com/search?q=${searchTerm}&num=100`;

  if (time === "d" || time === "w" || time === "m") {   // Show google indexes within the past 24 hours | 7 days | 1 month
    googleSearchString += `&as_qdr=${time}`;
  }

  var searchGoogle = CheckGoogleBotLock();

  if (!searchGoogle) {    // If we haven't waited at least an hour, dont search
    console.log(JSON.stringify({status: "failed", body: {msg: "Please wait 1 hour till searching again"}}, null, 2));
    return;
  }

  console.log("Getting google searches: " + googleSearchString);
  var links = await SearchGoogle(googleSearchString);
  if (links.status === "failed") {
    console.log(JSON.stringify({status: "failed", body: {msg: links.body.msg}}, null, 2));
    return;
  }

  links = GetUnique(links.body);
  if (results <= 100) {
    links = links.slice(0, results);
  }
  else {
    console.log(JSON.stringify({status: "failed", body: {msg: "Cannot return more than 100 websites"}}, null, 2))
    return;
  }

  if (links.length > 0) {
    for (var link of links) {
        console.log(`Getting info on: ${link}`);
        var result = await CreateJsonInfo(link);
        if (result.status === "success") {
          jsonResponse.body.results.push(result.body);
        }
    }
  }
  else {
    jsonResponse.body.msg = "Could not find any links";
    console.log(JSON.stringify(jsonResponse, null, 2));
    return;
  }

  console.log(JSON.stringify(jsonResponse, null, 2));
}

/*
Gets results from a google search. This will return a list of links bases on the search
results with the provided options. The links returned are sorted in order of the search
results but are not weeded for duplicates.
*/
function SearchGoogle(link) {
  return new Promise(async (resolve, reject) => {
    var jsonResponse = {status: "success", body: {}};

    // Get HTML of website
    var html, $;
    try {
      html = await (await fetch(link)).text();
      $ = cheerio.load(html);
    }
    catch (err) {
      reject({status: "failed", body: {msg: err}});
    }

    var botDetection = $("#infoDiv");   // Check for Google's bot detection
    if (botDetection.length) {
      var text = botDetection.text();
      if (text.match(/This page appears when Google automatically detects requests/)) {
        fs.writeFileSync("GoogleBotLock", new Date(new Date().getTime()));    // Write current time and date to file
        reject({status: "failed", body: {msg: "Google detected bot detection"}});
      }
    }

    var links = [];

    var results = $("h3").parent("a");   // Get the results from the page
    if (results.length) {
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

    if (links.length > 0) {
      jsonResponse.body = links;
      resolve(jsonResponse);
    }
    else {
      reject({status: "failed", body: {msg: "No results found"}});
    }
  }).catch(err => {
    console.log(err);
    return({status: "failed", body: {msg: err.body.msg}});
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
    var promises = [];    // List of promises to wait on

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
    catch (err) {
      reject({status: "failed", body: {msg: err}});
    }

    var hrefs = $("a[href]");   // Get all hrefs


    // Get Facebook details
    var facebook = (hrefs.filter((i, elem) => {
        return $(elem).attr("href").match(/facebook\.com\/(?!sharer)/);
    })).first();

    if (facebook.length) {
      var href = facebook.attr("href");
      if (href) {
        json[identifier].facebookPage.link = href.replace(/(\.com\/.*?)\/.*/, "$1");    // Replace everything after the identifier
        json[identifier].facebookPage.status = "success";
        promises.push(CheckFacebook(json[identifier].facebookPage.link));
      }
    }

    // Get Twitter details
    var twitter = (hrefs.filter((i, elem) => {
      return $(elem).attr("href").match(/twitter\.com\/(?!intent)/);
    })).first();

    if (twitter.length) {
      var href = twitter.attr("href");
      if (href) {
        json[identifier].twitterPage.link = href.replace(/(\.com\/.*?)\/.*/, "$1");   // Replace everything after the identifier
        json[identifier].twitterPage.status = "success"
        promises.push(CheckTwitter(json[identifier].twitterPage.link));
      }
    }

    // Get Instagram details
    var instagram = (hrefs.filter((i, elem) => {
      return $(elem).attr("href").match(/instagram\.com\/.*/);
    })).first();

    if (instagram.length) {
      var href = instagram.attr("href");
      if (href) {
        json[identifier].instagramPage.link = href.replace(/(\.com\/.*?)\/.*/, "$1");   // Replace everything after the identifier
        json[identifier].instagramPage.status = "success"
        promises.push(CheckInsta(json[identifier].instagramPage.link));
      }
    }

    // Get Contact details
    var contactPageElem = (hrefs.filter((i, elem) => {
      var link = $(elem).attr("href").replace(/(.*?\/\/.*?\/)|(^\/)/, "");    // Regex out the domain but keep page identifier
      return link.match(/contact/i);
    })).first();

    if (contactPageElem.length) {
      var contactPage = contactPageElem.attr("href");
      if (contactPage) {
        json[identifier].contactPage.link = link + "/" + contactPage.replace(/(.*?\/\/.*?\/)|(^\/)/, "");
        promises.push(GetContactInfo(json[identifier].contactPage.link));
      }
    }

    var contactInfo = await Promise.all(promises);
    if (contactInfo.length == 4) {
      if (contactInfo[0].status === "success") {
        json[identifier].facebookPage = {...json[identifier].facebookPage, ...contactInfo[0].body};
      }

      if (contactInfo[1].status === "success") {
        json[identifier].twitterPage = {...json[identifier].twitterPage, ...contactInfo[1].body};
      }

      if (contactInfo[2].status === "success") {
        json[identifier].instagramPage = {...json[identifier].instagramPage, ...contactInfo[2].body};
      }

      if (contactInfo[3].status === "success") {
        json[identifier].contactPage = {...json[identifier].contactPage, ...contactInfo[3].body};
      }

      json[identifier].facebookPage.status = contactInfo[0].status;
      json[identifier].twitterPage.status = contactInfo[1].status;
      json[identifier].instagramPage.status = contactInfo[2].status;
      json[identifier].contactPage.status = contactInfo[3].status;
    }

    jsonResponse.body = json;
    resolve(jsonResponse);
  }).catch(err => {
    console.log(err);
    return({status: "failed", body: {msg: err.body.msg}});
  });
}

/*
This function returns the contact number found in a link provided. Provide a
contact page link for the best result.
*/
function GetContactInfo(link) {
  return new Promise(async (resolve, reject) => {
    var jsonResponse = {status: "success", body: {}};

    // Get HTML of website
    var html, $;
    try {
      html = await (await fetch(link)).text();
      $ = cheerio.load(html);
    }
    catch (err) {
      reject({status: "failed", body: {msg: err}});
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

    if (contactNumberElem.length) {
      var contactNumber = $(contactNumberElem).text().replace(/\D/, "");
      if (contactNumber) {
        jsonResponse.body.number = contactNumber;
      }
    }

    // Get contact email
    var emailElem = (textElems.filter((i, elem) => {
      return $(elem).text().match(/\s\w+@\w+[\.\w]+\s/);
    })).first();

    if (emailElem.length) {
      var email = $(emailElem).text();
      if (email) {
        jsonResponse.body.email = email.match(/\s(\w+@\w+[\.\w]+)\s/)[1];
      }
    }

    resolve(jsonResponse);
  }).catch(err => {
    console.log(err);
    return({status: "failed", body: {msg: err.body.msg}});
  });
}

/*
Get information on a Facebook page.
*/
function CheckFacebook(link) {
  return new Promise(async (resolve, reject) => {
    var jsonResponse = {status: "success", body: {
      likes: 0,
      followers: 0,
      pageTitle: ""
    }};

    // Get HTML of website
    var html, $;
    try {
      html = await (await fetch(link)).text();
      $ = cheerio.load(html);
    }
    catch (err) {
      reject({status: "failed", body: {msg: err}});
    }

    var textElems = $("body *").filter((i, elem) => {
      return $(elem).text();
    });

    // Getting the likes of the Facebook page
    var likes = (textElems.filter((i, elem) => {
      if ($(elem).is("div")) {
        return $(elem).text().match(/people like this/);
      }
      else {
        return false;
      }
    })).last();
    if (likes.length) {
      likes = $(likes).text().replace(/\D/g, "");
      jsonResponse.body.likes = parseInt(likes);
    }

    // Getting the followers of the Facebook page
    var followers = (textElems.filter((i, elem) => {
      if ($(elem).is("div")) {
        return $(elem).text().match(/people follow this/);
      }
      else {
        return false;
      }
    })).last();
    if (followers.length) {
      followers = $(followers).text().replace(/\D/g, "");
      jsonResponse.body.followers = parseInt(followers);
    }

    // Getting the name of the Facebook page
    var title = ($("h1 > span").filter((i, elem) => {
      return $(elem).text();
    })).first();
    if (title.length) {
      jsonResponse.body.pageTitle = title.text();
    }

    resolve(jsonResponse);
  }).catch(err => {
    console.log(err);
    return({status: "failed", body: {msg: err.body.msg}});
  })
}

/*
Get information on a Twitter page.
*/
function CheckTwitter(link) {
  return new Promise(async (resolve, reject) => {
    var jsonResponse = {status: "success", body: {
      followers: 0,
      following: 0
    }};

    // Get HTML of website
    console.log(link);
    var html, $;
    try {
      html = await (await fetch(link)).text();    // Twitter is rejecting request
      $ = cheerio.load(html);
    }
    catch (err) {
      reject({status: "failed", body: {msg: err}});
    }

    // Get all anchor tags
    var anchors = $("a");

    // Get 'following' anchor tags
    var followingTags = $(anchors).filter((i, elem) => {
      if ($(elem).attr("href")) {
        return $(elem).attr("href").match(/following/);
      }
      else {
        return false;
      }
    });

    // Get following
    var following;
    if (followingTags.length) {
      following = $(followingTags).find("span");
      if (following.length) {
        following = $(following).filter((i, elem) => {
          return $(elem).attr("data-count");
        })
      }
    }

    if (following) {
      jsonResponse.body.following = following;
    }

    // Get 'followers' anchor tags
    var followerTags = $(anchors).filter((i, elem) => {
      if ($(elem).attr("href")) {
        return $(elem).attr("href").match(/followers/);
      }
      else {
        return false;
      }
    });

    // Get followers
    var followers;
    if (followerTags.length) {
      followers = $(followerTags).find("span");
      if (followers.length) {
        followers = $(followers).filter((i, elem) => {
          return $(elem).attr("data-count");
        })
      }
    }

    if (followers) {
      jsonResponse.body.followers = followers;
    }

    resolve(jsonResponse);
  }).catch(err => {
    console.log(err);
    return({status: "failed", body: {msg: err.body.msg}});
  })
}

/*
Get information on an Instagram page.
*/
function CheckInsta(link) {
  return new Promise(async (resolve, reject) => {
    var jsonResponse = {status: "success", body: {
      followers: 0,
      following: 0
    }};

    // Get HTML of website
    var html, $;
    try {
      html = await (await fetch(link)).text();
      $ = cheerio.load(html);
    }
    catch (err) {
      reject({status: "failed", body: {msg: err}});
    }

    resolve(jsonResponse);
  }).catch(err => {
    console.log(err);
    return({status: "failed", body: {msg: err.body.msg}});
  })
}

/*
Check to see if Google has temporarily banned anymore google searches
*/
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

//------------------------------------------------------------------------------------//
// Structure
//------------------------------------------------------------------------------------//

GetProspects(args.searchTerm, args.results, args.time);