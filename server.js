const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8000;
const ROOT_DIR = path.resolve(__dirname);
const MACRODROID_WEBHOOK_URL = 'https://trigger.macrodroid.com/fe4a4799-422f-4698-ac4e-84982b13893a/water_alert';
const MACRODROID_MESSAGE = 'CRITICAL WATER ALERT 🚨! TDS: {lv=tds} ppm | NTU: {lv=ntu} | pH: {lv=ph} | Temp: {lv=temp}°C';

function triggerMacroDroid(record) {
  if (!MACRODROID_WEBHOOK_URL || MACRODROID_WEBHOOK_URL.includes('YOUR_DEVICE_ID')) {
    return;
  }

  try {
    const url = new URL(MACRODROID_WEBHOOK_URL);
    url.searchParams.set('tds', String(record.tds));
    url.searchParams.set('ntu', String(record.ntu));
    url.searchParams.set('ph', String(record.ph));
    url.searchParams.set('temp', String(record.temp));
    url.searchParams.set('message', MACRODROID_MESSAGE);

    const request = https.get(url.toString(), (response) => {
      response.on('data', () => {});
      response.on('end', () => {});
    });

    request.on('error', (error) => {
      console.error('MacroDroid webhook failed:', error.message);
    });
  } catch (error) {
    console.error('MacroDroid trigger error:', error.message);
  }
}

const contentTypes = {
  '.html': 'text/html; charset=UTF-8',
  '.js': 'application/javascript; charset=UTF-8',
  '.css': 'text/css; charset=UTF-8',
  '.json': 'application/json; charset=UTF-8',
  '.csv': 'text/csv; charset=UTF-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
};

function sendResponse(res, statusCode, body, contentType) {
  res.writeHead(statusCode, { 'Content-Type': contentType });
  res.end(body);
}

function send404(res) {
  sendResponse(res, 404, '404 Not Found', 'text/plain; charset=UTF-8');
}

function serveStaticFile(filePath, res) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      send404(res);
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = contentTypes[ext] || 'application/octet-stream';
    sendResponse(res, 200, data, contentType);
  });
}

function parseJsonBody(req, callback) {
  let body = '';
  req.on('data', chunk => { body += chunk.toString(); });
  req.on('end', () => {
    try {
      callback(null, body ? JSON.parse(body) : {});
    } catch (err) {
      callback(err);
    }
  });
}

function analyzeWaterData({ tds, ntu, ph, temp, voltage }) {
  let status = 'unknown';
  let anomaly = false;
  let trend = 'stable';
  let prediction = 'Unable to classify water quality.';
  let confidence = 60;

  const numTds = typeof tds === 'number' ? tds : parseFloat(tds);
  const numNtu = typeof ntu === 'number' ? ntu : parseFloat(ntu);
  const numPh = typeof ph === 'number' ? ph : (ph !== undefined && ph !== null ? parseFloat(ph) : 7.0);
  const numTemp = typeof temp === 'number' ? temp : (temp !== undefined && temp !== null ? parseFloat(temp) : 25.0);

  if (isNaN(numTds) || isNaN(numNtu)) {
    return {
      status: 'error',
      anomaly: true,
      trend: 'stable',
      prediction: 'Invalid or missing physical sensor values.',
      confidence: 100
    };
  }

  const isPhUnsafe = (!isNaN(numPh) && (numPh < 6.5 || numPh > 8.5));
  const isTempHigh = (!isNaN(numTemp) && numTemp > 35);
  const isTdsHigh = (numTds > 1000);
  const isNtuHigh = (numNtu > 5);

  const isPhWarn = (!isNaN(numPh) && (numPh < 6.8 || numPh > 8.2));
  const isTempWarn = (!isNaN(numTemp) && numTemp > 30);
  const isTdsWarn = (numTds > 500);
  const isNtuWarn = (numNtu > 2);

  if (isTdsHigh || isNtuHigh || isPhUnsafe || isTempHigh) {
    status = 'danger';
    anomaly = true;
    prediction = 'Critical alert: Threshold violation on physical sensor grid.';
    const issues = [];
    if (isPhUnsafe) issues.push(`pH (${numPh.toFixed(1)}) out of WHO range (6.5-8.5)`);
    if (isTempHigh) issues.push(`Temperature (${numTemp.toFixed(1)}°C) elevated (>35°C)`);
    if (isTdsHigh) issues.push(`TDS (${numTds.toFixed(0)} ppm) exceeds 1000 ppm`);
    if (isNtuHigh) issues.push(`Turbidity (${numNtu.toFixed(1)} NTU) exceeds 5 NTU`);
    prediction += ' ' + issues.join('; ') + '.';
    confidence = 96;
  } else if (isTdsWarn || isNtuWarn || isPhWarn || isTempWarn) {
    status = 'warning';
    prediction = 'Warning: Sensor parameters approaching upper regulatory limits.';
    confidence = 88;
  } else {
    status = 'safe';
    prediction = 'All 4 hardware sensors (pH, Temperature, Turbidity, TDS) within safe WHO & BIS standards.';
    confidence = 94;
  }

  if (numTds > 800) {
    trend = 'increasing';
  } else if (numTds < 200) {
    trend = 'decreasing';
  }

  if (typeof voltage === 'number' && voltage < 3.3) {
    prediction += ' Warning: ESP32 sensor rail voltage low.';
  }

  return { status, anomaly, trend, prediction, confidence };
}

const server = http.createServer((req, res) => {
  const url = req.url;

  if (url === '/api/health') {
    sendResponse(res, 200, JSON.stringify({ status: 'ok', sensorsCount: 4, sensors: ['ph', 'temp', 'ntu', 'tds'] }), 'application/json; charset=UTF-8');
    return;
  }

  if (url === '/api/sensor-data' && req.method === 'POST') {
    parseJsonBody(req, (err, body) => {
      if (err) {
        sendResponse(res, 400, JSON.stringify({ error: 'Invalid JSON payload' }), 'application/json; charset=UTF-8');
        return;
      }

      const record = {
        timestamp: body.timestamp || Date.now(),
        tds: Number(body.tds) || 0,
        ntu: Number(body.ntu) || 0,
        ph: Number(body.ph) || 7.0,
        temp: Number(body.temp) || 25.0,
        voltage: Number(body.voltage) || 0
      };
      const csvLine = `${record.timestamp},${record.tds},${record.ntu},${record.ph},${record.temp},${record.voltage}\n`;
      const csvFile = path.join(ROOT_DIR, 'water_data.csv');

      fs.appendFile(csvFile, csvLine, err => {
        if (err) {
          sendResponse(res, 500, JSON.stringify({ error: 'Unable to save sensor data' }), 'application/json; charset=UTF-8');
          return;
        }
        if (record.tds > 1000 || record.ntu > 5 || record.ph < 6.5 || record.ph > 8.5) {
          triggerMacroDroid(record);
        }
        sendResponse(res, 200, JSON.stringify({ success: true, record }), 'application/json; charset=UTF-8');
      });
    });
    return;
  }

  if (url === '/api/analyze' && req.method === 'POST') {
    parseJsonBody(req, (err, body) => {
      if (err) {
        sendResponse(res, 400, JSON.stringify({ error: 'Invalid JSON payload' }), 'application/json; charset=UTF-8');
        return;
      }
      sendResponse(res, 200, JSON.stringify(analyzeWaterData(body)), 'application/json; charset=UTF-8');
    });
    return;
  }

  if (url === '/api/data' && req.method === 'GET') {
    const csvFile = path.join(ROOT_DIR, 'water_data.csv');
    fs.readFile(csvFile, 'utf8', (err, data) => {
      if (err) {
        sendResponse(res, 500, JSON.stringify({ error: 'Unable to read data file' }), 'application/json; charset=UTF-8');
        return;
      }

      const rows = data.trim().split('\n').slice(1).filter(Boolean).map(line => {
        const parts = line.split(',');
        return {
          timestamp: Number(parts[0]) || 0,
          tds: Number(parts[1]) || 0,
          ntu: Number(parts[2]) || 0,
          ph: Number(parts[3]) || 7.0,
          temp: Number(parts[4]) || 25.0,
          voltage: Number(parts[5]) || 0
        };
      });
      sendResponse(res, 200, JSON.stringify(rows), 'application/json; charset=UTF-8');
    });
    return;
  }

  if (url === '/api/export' && req.method === 'GET') {
    const csvFile = path.join(ROOT_DIR, 'water_data.csv');
    fs.readFile(csvFile, (err, data) => {
      if (err) {
        send404(res);
        return;
      }
      res.writeHead(200, {
        'Content-Type': 'text/csv; charset=UTF-8',
        'Content-Disposition': 'attachment; filename="water_data.csv"'
      });
      res.end(data);
    });
    return;
  }

  let requestPath = url.split('?')[0];
  if (requestPath === '/' || requestPath === '/index.html') {
    requestPath = '/index.html';
  }

  const safePath = path.normalize(decodeURIComponent(requestPath)).replace(/^\.+/, '');
  const fullPath = path.join(ROOT_DIR, safePath);

  if (!fullPath.startsWith(ROOT_DIR)) {
    send404(res);
    return;
  }

  fs.stat(fullPath, (err, stats) => {
    if (err) {
      send404(res);
      return;
    }

    if (stats.isDirectory()) {
      serveStaticFile(path.join(fullPath, 'index.html'), res);
      return;
    }

    serveStaticFile(fullPath, res);
  });
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.log(`Port ${PORT} is already in use — a HydraCure server is likely already running.`);
    console.log(`Open http://localhost:${PORT} directly, or run stop.bat first, then start again.`);
  } else {
    console.error('Server error:', err.message);
  }
  process.exit(1);
});

server.listen(PORT, () => {
  console.log(`JS server running at http://localhost:${PORT}`);
});
