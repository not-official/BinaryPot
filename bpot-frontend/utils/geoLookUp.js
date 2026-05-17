// ==============================
// FILE: bpot-backend/routes/geoip.js
// ==============================

const express = require("express");
const router = express.Router();

const fs = require("fs");
const path = require("path");
const geoip = require("geoip-lite");

const LOGS_DIR = path.join(__dirname, "../logs");

// Extract IPv4 addresses
function extractIPs(text) {
  const matches = text.match(/\b(?:\d{1,3}\.){3}\d{1,3}\b/g);

  if (!matches) return [];

  return [...new Set(matches)];
}

// Ignore private/local IPs
function isPrivateIP(ip) {
  return (
    ip.startsWith("127.") ||
    ip.startsWith("10.") ||
    ip.startsWith("192.168.") ||
    ip.startsWith("172.")
  );
}

// ============================================
// GET ALL ATTACK LOCATIONS FROM LOG FILES
// ============================================

router.get("/attacks", async (req, res) => {
  try {
    const files = fs.readdirSync(LOGS_DIR);

    let attacks = [];

    for (const file of files) {
      const filePath = path.join(LOGS_DIR, file);

      if (!fs.statSync(filePath).isFile()) continue;

      const content = fs.readFileSync(filePath, "utf8");

      const ips = extractIPs(content);

      for (const ip of ips) {
        if (isPrivateIP(ip)) continue;

        const geo = geoip.lookup(ip);

        if (!geo || !geo.ll) continue;

        attacks.push({
          ip,
          city: geo.city || "Unknown",
          country: geo.country || "Unknown",
          lat: geo.ll[0],
          lon: geo.ll[1],
        });
      }
    }

    // Remove duplicate IPs
    const uniqueAttacks = Array.from(
      new Map(attacks.map((a) => [a.ip, a])).values()
    );

    res.json(uniqueAttacks);
  } catch (err) {
    console.error(err);

    res.status(500).json({
      error: "Failed to process attack logs",
    });
  }
});

// ============================================
// SINGLE IP LOOKUP
// ============================================

router.get("/lookup", async (req, res) => {
  try {
    const ip = req.query.ip;

    if (!ip) {
      return res.status(400).json({
        detail: "IP address required",
      });
    }

    const geo = geoip.lookup(ip);

    if (!geo || !geo.ll) {
      return res.status(404).json({
        detail: "GeoIP data not found",
      });
    }

    res.json({
      ip,
      city: geo.city || "Unknown",
      country_code: geo.country || "Unknown",
      country_name: geo.country || "Unknown",
      subdivision: "Unknown",
      latitude: geo.ll[0],
      longitude: geo.ll[1],
    });
  } catch (err) {
    console.error(err);

    res.status(500).json({
      detail: "GeoIP lookup failed",
    });
  }
});

module.exports = router;