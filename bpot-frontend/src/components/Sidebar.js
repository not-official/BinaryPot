import React from "react";
import { NavLink } from "react-router-dom";
import "./Sidebar.css";

const Sidebar = ({ collapsed, setCollapsed }) => {
  return (
    <nav className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebarTop">
        <div className="sidebarLogo">
          <div className="logoIcon">⬡</div>

          {!collapsed && (
            <div className="logoTextWrap">
              <div className="logoText">BinaryPot</div>
              <span className="logoVer">SSH HONEYPOT v1.0</span>
            </div>
          )}
        </div>

        <button
          type="button"
          className="sidebarToggle"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? "→" : "←"}
        </button>
      </div>

      {!collapsed && (
        <div className="sidebarStatus">
          <div className="statusDot"></div>
          <span>LISTENING · port 22</span>
        </div>
      )}

      <div className="sidebarNav">
        {!collapsed && <div className="navSection">Main</div>}

        <NavLink
          to="/portal"
          className={({ isActive }) => (isActive ? "navItem active" : "navItem")}
        >
          <span className="navIcon">⊞</span>
          {!collapsed && <span>Portal Home</span>}
        </NavLink>

        {!collapsed && <div className="navSection">Monitor</div>}

        <NavLink
          to="/dashboard"
          className={({ isActive }) => (isActive ? "navItem active" : "navItem")}
        >
          <span className="navIcon">▥</span>
          {!collapsed && <span>Live Dashboard</span>}
        </NavLink>

        <NavLink
          to="/map"
          className={({ isActive }) => (isActive ? "navItem active" : "navItem")}
        >
          <span className="navIcon">◎</span>
          {!collapsed && <span>Attack Map</span>}
        </NavLink>

        <NavLink
          to="/sessions"
          className={({ isActive }) => (isActive ? "navItem active" : "navItem")}
        >
          <span className="navIcon">≡</span>
          {!collapsed && <span>Sessions & Logs</span>}
        </NavLink>

        {!collapsed && <div className="navSection">Analyze</div>}

        <NavLink
          to="/research"
          className={({ isActive }) => (isActive ? "navItem active" : "navItem")}
        >
          <span className="navIcon">⚗️</span>
          {!collapsed && <span>Research Tools</span>}
        </NavLink>

        <NavLink
          to="/docs"
          className={({ isActive }) => (isActive ? "navItem active" : "navItem")}
        >
          <span className="navIcon">◫</span>
          {!collapsed && <span>Documentation</span>}
        </NavLink>
      </div>

      {!collapsed && (
        <div className="sidebarFooter">
          <div className="sshPort">
            SSH LISTENER: <span>0.0.0.0:22</span>
          </div>
          <div className="sshPort" style={{ marginTop: "3px" }}>
            API: <span>localhost:8000</span>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Sidebar;