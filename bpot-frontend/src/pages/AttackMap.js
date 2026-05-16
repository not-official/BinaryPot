import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { message } from "antd";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
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

const API_BASE =
  process.env.REACT_APP_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

const defaultCenter = [20, 0];

const mapBounds = [
  [-85, -180],
  [85, 180],
];

const MapFlyTo = ({ coords }) => {
  const map = useMap();

  useEffect(() => {
    if (coords) {
      map.flyTo(coords, 5, { duration: 1.1 });
    }
  }, [coords, map]);

  return null;
};

function AttackMap() {
  const [collapsed, setCollapsed] = useState(false);
  const [ipAddress, setIpAddress] = useState("");
  const [lookupResult, setLookupResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const token = sessionStorage.getItem("token");

  const api = useMemo(() => {
    const instance = axios.create({
      baseURL: API_BASE,
      headers: { "Content-Type": "application/json" },
    });

    instance.interceptors.request.use((config) => {
      if (token) config.headers.Authorization = `Bearer ${token}`;
      return config;
    });

    return instance;
  }, [token]);

  const handleLogout = () => {
    sessionStorage.removeItem("token");
    window.location.href = "/login";
  };

  const runLookup = async (event) => {
    event.preventDefault();

    const value = ipAddress.trim();
    if (!value) {
      message.warning("Enter an IP address first.");
      return;
    }

    setLoading(true);
    try {
      const response = await api.get("/api/geoip/lookup", { params: { ip: value } });
      setLookupResult(response.data);
      message.success(`Resolved ${value}`);
    } catch (error) {
      setLookupResult(null);
      message.error(error?.response?.data?.detail || "GeoIP lookup failed");
    } finally {
      setLoading(false);
    }
  };

  const markerCoords =
    lookupResult?.latitude != null && lookupResult?.longitude != null
      ? [lookupResult.latitude, lookupResult.longitude]
      : null;

  return (
    <div style={{ display: "flex" }}>
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />

      <div
        className="attackMapPage"
        style={{
          marginLeft: collapsed ? "70px" : "220px",
          transition: "margin-left 0.25s ease",
          width: "100%",
        }}
      >
        <Topbar
          section="Monitor"
          page="Attack Map"
          statusText="GEOIP ONLINE"
          onLogout={handleLogout}
        />

        <div className="attackMapShell">
          <div className="attackMapHeader">
            <div>
              <div className="mapEyebrow">REAL-TIME ATTACK ORIGINS</div>
              <h1>Attack Map</h1>
              <p>
                Enter an IP address to resolve its approximate location and plot it on the global
                map using the GeoLite2 database.
              </p>
            </div>

            <form className="lookupCard" onSubmit={runLookup}>
              <label htmlFor="ipAddress">IP address</label>
              <div className="lookupRow">
                <input
                  id="ipAddress"
                  type="text"
                  placeholder="e.g. 8.8.8.8"
                  value={ipAddress}
                  onChange={(e) => setIpAddress(e.target.value)}
                />
                <button type="submit" className="lookupBtn" disabled={loading}>
                  {loading ? "LOOKING UP..." : "LOOK UP"}
                </button>
              </div>
              <div className="lookupHint">Lookup is powered by /api/geoip/lookup on the backend.</div>
            </form>
          </div>

          <div className="attackMapGrid">
            <div className="mapPanel">
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
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <MapFlyTo coords={markerCoords} />
                {markerCoords && (
                  <Marker position={markerCoords}>
                    <Popup>
                      <div className="popupContent">
                        <strong>{lookupResult.ip}</strong>
                        <div>
                          {lookupResult.city || "Unknown city"}
                          {lookupResult.subdivision ? `, ${lookupResult.subdivision}` : ""}
                        </div>
                        <div>{lookupResult.country_name || lookupResult.country_code || "Unknown country"}</div>
                        <div>
                          {lookupResult.latitude?.toFixed(4)}, {lookupResult.longitude?.toFixed(4)}
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                )}
              </MapContainer>
            </div>

            <div className="detailsPanel">
              <div className="detailsCard">
                <div className="detailsTitle">Location summary</div>
                {lookupResult ? (
                  <div className="detailsList">
                    <div><span>IP</span><strong>{lookupResult.ip}</strong></div>
                    <div><span>Latitude</span><strong>{lookupResult.latitude ?? "-"}</strong></div>
                    <div><span>Longitude</span><strong>{lookupResult.longitude ?? "-"}</strong></div>
                    <div><span>Country</span><strong>{lookupResult.country_name || lookupResult.country_code || "-"}</strong></div>
                    <div><span>City</span><strong>{lookupResult.city || "-"}</strong></div>
                    <div><span>Region</span><strong>{lookupResult.subdivision || "-"}</strong></div>
                  </div>
                ) : (
                  <div className="emptyState">
                    Resolve an IP to pin the attack origin and inspect the geolocation result.
                  </div>
                )}
              </div>

              <div className="detailsCard detailsAccent">
                <div className="detailsTitle">Notes</div>
                <div className="notesText">
                  This page uses the local GeoLite2 database, so lookups do not depend on an external
                  geolocation service.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AttackMap;