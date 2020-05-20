const puppet = require("puppeteer");

async function scrape(url) {
    const browser = await puppet.launch();
    const page = await browser.newPage();
    await page.goto(url);

    var [el] = await page.$x('//input[@value="Google Search"]');
    var value = await el.getProperty("value");
    console.log(await  value.jsonValue());

    browser.close();
}

scrape("https://www.google.co.uk");