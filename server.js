const express = require('express')
const {spawn} = require('child_process');
var cors = require('cors');
const app = express();
app.use(cors({
    origin: "*"
    // origin: "http://webspred.co.uk"
}));

app.set('json spaces', 4);

app.get('/', (req, res) => {
    var searchTerm = req.query.searchTerm;
    var output;

    // Spawn new child process to call the python script
    const python = spawn('python', ['Prospect_Searcher.py', `-s ${searchTerm}`]);

    // Collect data from script
    python.stdout.on('data', function (data) {
        console.log('Pipe data from python script ...');
        output = data.toString();
    });

    // In close event we are sure that stream from child process is closed
    python.on('close', (code) => {
        console.log(`child process close all stdio with code ${code}`);
        // Send data to browser
        var json = [];
        if (output !== undefined) {
            var lines = output.split("\n");
            var jsonElem = {};
            lines.forEach((line) => {
                if (line.trim() === "") {
                    if (Object.keys(jsonElem).length != 0) {
                        json.push(jsonElem);
                        jsonElem = {};
                    }
                    return;
                }

                var title = line.match(/^(.*?):/);
                if (title) {
                    title = title[1].trim();
                    jsonElem[title] = {};
                }
                else {
                    title = "";
                }

                var website = line.match(/(http.*?)\s/);
                if (website) {
                    jsonElem.website = website[1];
                }
                else {
                    website = "";
                }

                if (title === "Facebook Page") {
                    var likes = line.match(/([\d,]+) likes/);
                    if (likes) {
                        likes = likes[1].replace(",", "");
                    }
                    else {
                        likes = 0;
                    }

                    var followers = line.match(/([\d,]+) followers/);
                    if (followers) {
                        followers = followers[1].replace(",", "");
                    }
                    else {
                        followers = 0;
                    }

                    jsonElem[title] = {
                        likes: likes,
                        followers: followers
                    }
                }
                else if (title === "Contact Number") {
                    var phoneNumber = line.match(/\(([\d\s]+)\)/);
                    if (phoneNumber) {
                        phoneNumber = phoneNumber[1];
                    }
                    else {
                        phoneNumber = 0;
                    }
                    jsonElem[title] = phoneNumber;
                }

                var website = line.match(/\((http.*?)[)\s]/);
                if (website) {
                    website = website[1];
                }
                else {
                    website = "";
                }
                jsonElem[title]["website"] = website;
            });
        }
        res.json(json);
    });
});

app.listen(8889, () => {
  console.log('Example app listening on port 8889!');
});