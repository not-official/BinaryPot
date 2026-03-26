import React, { useState } from "react";
import { Link } from "react-router-dom";
import Sidebar from "../components/Sidebar";
import HeroTerminal from "../components/HeroTerminal";
import "./Portal.css";

const Portal = () => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div style={{ display: "flex" }}>
      {/* SIDEBAR */}
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />

      {/* MAIN CONTENT */}
      <div
        className="portalPage"
        style={{
          marginLeft: collapsed ? "70px" : "220px",
          transition: "margin-left 0.25s ease",
          width: "100%",
        }}
      >
        <div className="portalShell">
          {/* HERO */}
          <div className="landingHero">
            <div className="heroText">
              <div className="portalTag">THREAT INTELLIGENCE PORTAL</div>

              <h1>
                Binary<span>Pot</span>
              </h1>

              <p>
                An interactive SSH honeypot powered by LLMs. Captures attacker
                behavior with a realistic simulated Linux terminal — keeping
                attackers engaged longer for richer threat intelligence.
              </p>

              <div className="heroCta">
                <Link to="/dashboard" className="btnPrimary">
                  → Live Dashboard
                </Link>
                <Link to="/map" className="btnSecondary">
                  Attack Map
                </Link>
                <Link to="/docs" className="btnSecondary">
                  Docs
                </Link>
              </div>
            </div>

            <div className="heroTerminalWrap">
              <HeroTerminal />
            </div>
          </div>

          {/* SECTION */}
          <div className="sectionLabel">// quick access</div>

          {/* HUB */}
          <div className="navHub">
            <HubCard
              to="/dashboard"
              icon="▥"
              title="Live Dashboard"
              desc="Real-time Kibana-style metrics, charts, and attacker tables"
            />

            <HubCard
              to="/map"
              icon="◎"
              title="Attack Map"
              desc="Live global visualization of attack origins and patterns"
            />

            <HubCard
              to="/sessions"
              icon="≡"
              title="Sessions Browser"
              desc="Browse, filter, and replay attacker terminal sessions"
            />

            <HubCard
              to="/research"
              icon="⚗️"
              title="Research Tools"
              desc="IP intel, payload decoder, LLM-powered command analyzer"
            />

            <HubCard
              to="/docs"
              icon="◫"
              title="Documentation"
              desc="Setup, API reference, architecture diagrams, and guides"
            />

            <div className="hubCard hubStatus">
              <div className="hubArrow hubStatusDot">●</div>
              <div className="hubIcon">⬡</div>
              <div className="hubTitle">System Status</div>
              <div className="hubDesc">
                All services operational · LLM engine online · SSH listener
                active
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const HubCard = ({ to, icon, title, desc }) => {
  return (
    <Link to={to} className="hubCard">
      <div className="hubArrow">→</div>
      <div className="hubIcon">{icon}</div>
      <div className="hubTitle">{title}</div>
      <div className="hubDesc">{desc}</div>
    </Link>
  );
};

export default Portal;
