//------------------------------------------------------------------------------------//
// Modules
//------------------------------------------------------------------------------------//

const express = require('express');
const cors = require('cors');
const app = express();
const fetch = require("node-fetch");
const cheerio = require("cheerio");

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
    res.json({status: "failed", body: {}, msg: "Provide a search term with 'searchTerm=query'"});
    return;
  }

  var googleSearchString = `https://www.google.com/search?q=${searchTerm}&num=100`;

  if (time === "d" || time === "w" || time === "m") {   // Show google indexes within the past 24 hours | 7 days | 1 month
    googleSearchString += `&as_qdr=${time}`;
  }

  var links = [];
  try {
    links = await SearchGoogle(googleSearchString);
    if (links.status === "failed" || !links.body) {
      res.json({status: "failed", body: {results: [], msg: "Failed when trying to get Google Searches"}});
      return;
    }
  }
  catch (err) {
    console.log(err);
    res.json({status: "failed", body: {results: [], msg: "Failed when trying to get Google Searches"}});
    return;
  }

  links = GetUnique(links.body);
  if (num <= 100) {
    links = links.slice(0, num);
  }
  else {
    res.json({status: "failed", body: {results: [], msg: "Cannot return more than 100 websites"}})
  }

  for (var link of links) {
    try {
      console.log(`Getting info on: ${link}`);
      var result = await CreateJsonInfo(link)
      if (result === "failed" || !result.body) {
        res.json({status: "failed", body: {results: [], msg: "Failed when creating/finding JSON info for results"}});
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
  console.log("Responded");
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
function SearchGoogle(link) {
  return new Promise(async (resolve, reject) => {
    var jsonResponse = {status: "success", body: {}};

    var html = await (await fetch(link)).text();
    var $ = cheerio.load(html);

    var links = [];

    var results = $("div[role=heading]").parent().parent().find("a");   // Get the results from the page
    results.each((i, elem) => {
      var href = $(elem).attr("href");
      if (href) {
        href = href.replace(/^.*?q=/, "");    // Replace the rubbish at the beginning
        links.push(href);
      }
    });

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
    var identifier = identifier.replace(/^.*?www\./, "");   // Replace the first www.
    var identifier = identifier.replace(/\..*$/, "");   // Replace everything after the first "."

    json[identifier] = {    // Create the initial template for information
      website: link,
      facebookPage: {},
      twitterPage: {},
      instagramPage: {},
      contactPage: {}
    };

    // Get HTML of website
    var html = await (await fetch(link)).text();
    var $ = cheerio.load(html);

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

    // Get HTML of website
    var html = await (await fetch(link)).text();
    var $ = cheerio.load(html);

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
    return({status: "failed", body: {}});
  });
}