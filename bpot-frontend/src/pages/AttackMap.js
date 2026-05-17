// ==============================
// FILE: bpot-frontend/pages/AttackMap.js
// FULL UPDATED VERSION
// ==============================

import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { message } from "antd";

import {
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";

import L from "leaflet";

import "leaflet/dist/leaflet.css";

import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";

import "./AttackMap.css";

import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const redAttackIcon = L.divIcon({
  className: "attack-marker-icon",
  html: `
    <span class="attack-marker-pulse"></span>
    <span class="attack-marker-pin"></span>
  `,
  iconSize: [24, 34],
  iconAnchor: [12, 34],
  popupAnchor: [0, -30],
});

const API_BASE =
  process.env.REACT_APP_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

const defaultCenter = [20, 0];

const mapBounds = [
  [-85, -180],
  [85, 180],
];

const MapFlyTo = ({ coords }) => {
  const map = useMap();

  useEffect(() => {
    if (coords) {
      map.flyTo(coords, 5, {
        duration: 1.1,
      });
    }
  }, [coords, map]);

  return null;
};

function AttackMap() {
  const [collapsed, setCollapsed] = useState(false);

  const [ipAddress, setIpAddress] = useState("");

  const [lookupResult, setLookupResult] = useState(null);

  const [showLookupModal, setShowLookupModal] = useState(false);

  const [loading, setLoading] = useState(false);

  const [attacks, setAttacks] = useState([]);

  const token = sessionStorage.getItem("token");

  const api = useMemo(() => {
    const instance = axios.create({
      baseURL: API_BASE,
      headers: {
        "Content-Type": "application/json",
      },
    });

    instance.interceptors.request.use((config) => {
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      return config;
    });

    return instance;
  }, [token]);

  // ======================================
  // FETCH ATTACKS FROM BACKEND
  // ======================================

  useEffect(() => {
    const fetchAttacks = async () => {
      try {
        const response = await api.get("/api/geoip/attacks");

        setAttacks(response.data);
      } catch (err) {
        console.error(err);

        message.error("Failed to load attack data");
      }
    };

    fetchAttacks();

    // Refresh every 15 seconds
    const interval = setInterval(fetchAttacks, 15000);

    return () => clearInterval(interval);
  }, [api]);

  const handleLogout = () => {
    sessionStorage.removeItem("token");

    window.location.href = "/login";
  };

  // ======================================
  // MANUAL LOOKUP
  // ======================================

  const runLookup = async (event) => {
    event.preventDefault();

    const value = ipAddress.trim();

    if (!value) {
      message.warning("Enter an IP address first.");
      return;
    }

    setLoading(true);

    try {
      const response = await api.get("/api/geoip/lookup", {
        params: {
          ip: value,
        },
      });

      setLookupResult(response.data);

      setShowLookupModal(true);

      message.success(`Resolved ${value}`);
    } catch (error) {
      console.error(error);

      setLookupResult(null);

      setShowLookupModal(false);

      message.error(
        error?.response?.data?.detail || "GeoIP lookup failed"
      );
    } finally {
      setLoading(false);
    }
  };

  const markerCoords =
    lookupResult?.latitude != null &&
    lookupResult?.longitude != null
      ? [lookupResult.latitude, lookupResult.longitude]
      : null;

  return (
    <div className="attackMapLayout">
      <Sidebar
        collapsed={collapsed}
        setCollapsed={setCollapsed}
      />

      <main
        className="attackMapPage"
        style={{
          marginLeft: collapsed ? "70px" : "220px",
        }}
      >
        <Topbar
          section="Monitor"
          page="Attack Map"
          statusText="GEOIP ONLINE"
          onLogout={handleLogout}
        />

        <div className="attackMapShell">

          {/* HEADER */}

          <section className="attackMapHeaderCard">

            <div className="attackMapIntro">
              <div className="mapEyebrow">
                REAL-TIME ATTACK ORIGINS
              </div>

              <h1>Attack Map</h1>

              <p>
                Resolve suspicious IP addresses,
                plot their approximate location,
                and inspect GeoIP details.
              </p>
            </div>

            {/* LOOKUP FORM */}

            <form
              className="lookupCard"
              onSubmit={runLookup}
            >
              <label htmlFor="ipAddress">
                IP LOOKUP
              </label>

              <div className="lookupRow">

                <input
                  id="ipAddress"
                  type="text"
                  placeholder="Enter IP e.g. 8.8.8.8"
                  value={ipAddress}
                  onChange={(e) =>
                    setIpAddress(e.target.value)
                  }
                />

                <button
                  type="submit"
                  className="lookupBtn"
                  disabled={loading}
                >
                  {loading
                    ? "LOOKING..."
                    : "LOOK UP"}
                </button>
              </div>

              <div className="lookupHint">
                Source:
                <span> GeoLite Database</span>
              </div>
            </form>
          </section>

          {/* STATS */}

          <section className="attackStatsGrid">

            <div className="attackStatCard">
              <div className="attackStatLabel">
                ATTACKERS
              </div>

              <div className="attackStatValue">
                {attacks.length}
              </div>

              <div className="attackStatMeta">
                unique IPs
              </div>
            </div>

            <div className="attackStatCard">
              <div className="attackStatLabel">
                LOOKUP RESULT
              </div>

              <div className="attackStatValue">
                {lookupResult ? "READY" : "NONE"}
              </div>

              <div className="attackStatMeta">
                current query
              </div>
            </div>

            <div className="attackStatCard">
              <div className="attackStatLabel">
                GEO ENGINE
              </div>

              <div className="attackStatValue">
                ON
              </div>

              <div className="attackStatMeta">
                live processing
              </div>
            </div>
          </section>

          {/* MAP */}

          <section className="attackMapContentGrid">

            <div className="mapPanel">

              <div className="mapPanelHeader">
                <div>
                  <div className="chartTitle">
                    GLOBAL ATTACK MAP
                  </div>

                  <div className="smallMuted">
                    Live attacker locations
                  </div>
                </div>

                <div className="chartBadge live">
                  LIVE
                </div>
              </div>

              <div className="mapFrame">

                <MapContainer
                  center={defaultCenter}
                  zoom={2}
                  minZoom={2}
                  maxBounds={mapBounds}
                  maxBoundsViscosity={1}
                  scrollWheelZoom
                  className="leafletMap"
                >

                  <TileLayer
                    attribution='&copy; OpenStreetMap'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />

                  <MapFlyTo coords={markerCoords} />

                  {/* LIVE ATTACKS */}

                  {attacks.map((attack) => (
                    <Marker
                      key={attack.ip}
                      position={[
                        attack.lat,
                        attack.lon,
                      ]}
                      icon={redAttackIcon}
                    >
                      <Popup>
                        <div className="popupContent">
                          <strong>{attack.ip}</strong>

                          <span>{attack.city}</span>

                          <span>{attack.country}</span>
                        </div>
                      </Popup>
                    </Marker>
                  ))}

                  {/* MANUAL LOOKUP */}

                  {markerCoords && (
                    <Marker
                      position={markerCoords}
                      icon={redAttackIcon}
                    >
                      <Popup>
                        <div className="popupContent">
                          <strong>
                            {lookupResult.ip}
                          </strong>

                          <span>
                            {lookupResult.city}
                          </span>

                          <span>
                            {lookupResult.country_name}
                          </span>
                        </div>
                      </Popup>
                    </Marker>
                  )}

                </MapContainer>
              </div>
            </div>
          </section>
        </div>
      </main>

      {/* LOOKUP MODAL */}

      {showLookupModal && lookupResult && (
        <div
          className="lookupModalOverlay"
          onClick={() =>
            setShowLookupModal(false)
          }
        >
          <div
            className="lookupModal"
            onClick={(e) => e.stopPropagation()}
          >

            <div className="lookupModalHeader">

              <div>
                <div className="modalEyebrow">
                  MMDB GEOIP RESULT
                </div>

                <h2>{lookupResult.ip}</h2>
              </div>

              <button
                type="button"
                className="modalCloseBtn"
                onClick={() =>
                  setShowLookupModal(false)
                }
              >
                ×
              </button>
            </div>

            <div className="lookupModalGrid">

              <div>
                <span>Country</span>

                <strong>
                  {lookupResult.country_name}
                </strong>
              </div>

              <div>
                <span>City</span>

                <strong>
                  {lookupResult.city}
                </strong>
              </div>

              <div>
                <span>Latitude</span>

                <strong>
                  {lookupResult.latitude}
                </strong>
              </div>

              <div>
                <span>Longitude</span>

                <strong>
                  {lookupResult.longitude}
                </strong>
              </div>
            </div>

            <div className="lookupModalFooter">

              <button
                type="button"
                className="lookupBtn modalActionBtn"
                onClick={() =>
                  setShowLookupModal(false)
                }
              >
                CLOSE
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AttackMap;