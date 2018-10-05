const puppeteer = require('puppeteer');
const args = process.argv;

const captureScreenshots = async () => {
  const browser = await puppeteer.launch({args: ['--no-sandbox', '--disable-setuid-sandbox']});
  const page = await browser.newPage();
  await page.on('console', msg => console.log('PAGE LOG:', msg.text()));

  await page.goto(`file:///root/discordbot/ddnet-profile-card/${args[4]}.html`);
  await page.setViewport({ width: parseInt(args[2]), height: parseInt(args[3])});
  await page.emulateMedia('screen');
  await page.screenshot({ path: `/root/discordbot/ddnet-profile-card/${args[4]}.png`});

  await browser.close();
};

captureScreenshots();