import React from "react";
import "./Topbar.css";

const Topbar = ({
  section = "Portal",
  page = "Overview",
  statusText = "SYSTEM ONLINE",
  onRefresh,
  onLogout,
}) => {
  return (
    <div className="topbar">
      <div className="topbarLeft">
        <div className="breadcrumb">
          <span className="crumbText">{section}</span> / {page}
        </div>
      </div>

      <div className="topbarRight">
        <div className="tbPill">{statusText}</div>

        {onRefresh && (
          <button type="button" className="tbBtn" onClick={onRefresh}>
            REFRESH
          </button>
        )}

        {onLogout && (
          <button type="button" className="tbBtn" onClick={onLogout}>
            LOGOUT
          </button>
        )}
      </div>
    </div>
  );
};

export default Topbar;