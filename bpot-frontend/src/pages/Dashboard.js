import React, { useEffect, useMemo, useState } from "react";
import { message } from "antd";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import "./Dashboard.css";

const API_BASE =
  import.meta?.env?.VITE_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";


function Dashboard() {
  const [collapsed, setCollapsed] = useState(false);

  const [connections, setConnections] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [commands, setCommands] = useState([]);

  const [activeTab, setActiveTab] = useState("connections");
  const [activeSessionKey, setActiveSessionKey] = useState(null);

  const [loadingConnections, setLoadingConnections] = useState(false);
  const [loadingCommands, setLoadingCommands] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);

  const [username, setUsername] = useState("");
  const [since, setSince] = useState("");
  const [tableFilter, setTableFilter] = useState("");

  const token = sessionStorage.getItem("token");

    const navigate = useNavigate();

  const handleLogout = () => {
    sessionStorage.removeItem("token");
    navigate("/login", { replace: true });
  };

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

  const buildParams = () => {
    const params = {};
    if (username?.trim()) params.username = username.trim();
    if (since) {
      const parsed = new Date(since);
      if (!Number.isNaN(parsed.getTime())) {
        params.since = parsed.toISOString();
      }
    }
    return params;
  };

  const fetchConnections = async () => {
    setLoadingConnections(true);
    try {
      const res = await api.get("/api/connections", { params: buildParams() });
      setConnections(res.data || []);
    } catch (err) {
      message.error(err?.response?.data?.detail || "Failed to fetch connections");
    } finally {
      setLoadingConnections(false);
    }
  };

  const fetchCommands = async () => {
    setLoadingCommands(true);
    try {
      const res = await api.get("/api/commands", { params: buildParams() });
      setCommands(res.data || []);
    } catch (err) {
      message.error(err?.response?.data?.detail || "Failed to fetch commands");
    } finally {
      setLoadingCommands(false);
    }
  };

  const fetchSessions = async () => {
    setLoadingSessions(true);
    try {
      const res = await api.get("/api/sessions");
      setSessions(res.data || []);
      return res.data || [];
    } catch (err) {
      message.error(err?.response?.data?.detail || "Failed to fetch sessions");
      return [];
    } finally {
      setLoadingSessions(false);
    }
  };

  useEffect(() => {
    fetchConnections();
    fetchCommands();
    fetchSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const applyFilters = async () => {
    await Promise.all([fetchConnections(), fetchCommands()]);
    message.success("Filters applied");
  };

  const resetFilters = async () => {
    setUsername("");
    setSince("");
    await Promise.all([fetchConnections(), fetchCommands()]);
    message.info("Filters reset");
  };

  const openSession = async (sessionId) => {
    if (!sessionId) return;
    if (!sessions || sessions.length === 0) {
      await fetchSessions();
    }
    setActiveTab("sessions");
    setActiveSessionKey(String(sessionId));
  };

  const uniqueIPs = useMemo(() => {
    const ips = new Set(
      connections.map((c) => c.remote_addr).filter(Boolean)
    );
    return ips.size;
  }, [connections]);

  const uniqueUsers = useMemo(() => {
    const users = new Set(
      [...connections, ...commands]
        .map((item) => item.username)
        .filter(Boolean)
    );
    return users.size;
  }, [connections, commands]);

  const commandCount = commands.length;
  const connectionCount = connections.length;
  const sessionCount = sessions.length;

  const activeSessionsCount = useMemo(() => {
    return sessions.filter((s) => (s.activities || []).length > 0).length;
  }, [sessions]);

  const recentCommands = useMemo(() => {
    return commands.slice(0, 8);
  }, [commands]);

  const recentConnections = useMemo(() => {
    return connections.slice(0, 8);
  }, [connections]);

  const filteredConnections = useMemo(() => {
    const q = tableFilter.trim().toLowerCase();
    if (!q) return connections;

    return connections.filter((item) => {
      return (
        String(item?.remote_addr || "").toLowerCase().includes(q) ||
        String(item?.username || "").toLowerCase().includes(q) ||
        String(item?.session_id || "").toLowerCase().includes(q) ||
        String(item?.password || "").toLowerCase().includes(q)
      );
    });
  }, [connections, tableFilter]);

  const filteredCommands = useMemo(() => {
    const q = tableFilter.trim().toLowerCase();
    if (!q) return commands;

    return commands.filter((item) => {
      return (
        String(item?.command || "").toLowerCase().includes(q) ||
        String(item?.username || "").toLowerCase().includes(q) ||
        String(item?.time || "").toLowerCase().includes(q)
      );
    });
  }, [commands, tableFilter]);

  const formatTime = (value) => {
    if (!value) return "-";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    return d.toLocaleString();
  };

  const renderConnectionsTable = () => (
    <div className="tableCard">
      <div className="tableHeadRow">
        <div className="chartTitle">CONNECTIONS</div>

        <div className="tableHeadActions">
          <div className="tableSearch">
            <span className="searchIcon">⌕</span>
            <input
              type="text"
              placeholder="filter by ip, username, session..."
              value={tableFilter}
              onChange={(e) => setTableFilter(e.target.value)}
            />
          </div>

          <button
            className="miniBtn"
            onClick={fetchConnections}
            disabled={loadingConnections}
          >
            {loadingConnections ? "LOADING..." : "REFRESH"}
          </button>
        </div>
      </div>

      <div className="tableWrap">
        <table className="table">
          <thead>
            <tr>
              <th>TIME</th>
              <th>USERNAME</th>
              <th>IP</th>
              <th>PASSWORD</th>
              <th>SESSION</th>
            </tr>
          </thead>
          <tbody>
            {filteredConnections.length > 0 ? (
              filteredConnections.map((row, index) => (
                <tr key={`${row?.session_id || "conn"}-${index}`}>
                  <td>{formatTime(row?.time)}</td>
                  <td>
                    {row?.username ? (
                      <span className="badge badgePurple">{row.username}</span>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td>
                    <span className="ipLink">{row?.remote_addr || "-"}</span>
                  </td>
                  <td>{row?.password || "-"}</td>
                  <td>
                    {row?.session_id ? (
                      <button
                        className="sessionLinkBtn"
                        onClick={() => openSession(row.session_id)}
                      >
                        → {row.session_id}
                      </button>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="5" className="emptyCell">
                  No connection records found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderCommandsTable = () => (
    <div className="tableCard">
      <div className="tableHeadRow">
        <div className="chartTitle">COMMANDS</div>

        <div className="tableHeadActions">
          <div className="tableSearch">
            <span className="searchIcon">⌕</span>
            <input
              type="text"
              placeholder="filter by command or username..."
              value={tableFilter}
              onChange={(e) => setTableFilter(e.target.value)}
            />
          </div>

          <button
            className="miniBtn"
            onClick={fetchCommands}
            disabled={loadingCommands}
          >
            {loadingCommands ? "LOADING..." : "REFRESH"}
          </button>
        </div>
      </div>

      <div className="tableWrap">
        <table className="table">
          <thead>
            <tr>
              <th>TIME</th>
              <th>USERNAME</th>
              <th>COMMAND</th>
            </tr>
          </thead>
          <tbody>
            {filteredCommands.length > 0 ? (
              filteredCommands.map((row, index) => (
                <tr key={`${row?.time || "cmd"}-${index}`}>
                  <td>{formatTime(row?.time)}</td>
                  <td>
                    {row?.username ? (
                      <span className="badge badgePurple">{row.username}</span>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td className="monoCell">{row?.command || "-"}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="3" className="emptyCell">
                  No command records found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  const renderSessions = () => (
    <div className="tableCard">
      <div className="tableHeadRow">
        <div className="chartTitle">SESSIONS</div>

        <div className="tableHeadActions">
          <span className="smallMuted">Click a session to expand full activity</span>
          <button
            className="miniBtn"
            onClick={fetchSessions}
            disabled={loadingSessions}
          >
            {loadingSessions ? "LOADING..." : "REFRESH"}
          </button>
        </div>
      </div>

      <div className="sessionsWrap">
        {sessions.length > 0 ? (
          sessions.map((session) => {
            const isOpen = activeSessionKey === String(session.session_id);

            return (
              <div className="sessionItem" key={String(session.session_id)}>
                <button
                  className={`sessionToggle ${isOpen ? "sessionToggleOpen" : ""}`}
                  onClick={() =>
                    setActiveSessionKey(
                      isOpen ? null : String(session.session_id)
                    )
                  }
                >
                  <div className="sessionHeaderLeft">
                    <span className="sessionMainLabel">
                      Session: <span className="monoAccent">{session.session_id}</span>
                    </span>
                  </div>

                  <div className="sessionHeaderRight">
                    <span className="badge badgeSoft">
                      {(session?.activities || []).length} events
                    </span>
                    <span className="sessionArrow">{isOpen ? "−" : "+"}</span>
                  </div>
                </button>

                {isOpen && (
                  <div className="sessionBody">
                    <div className="tableWrap">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>TIME</th>
                            <th>COMMAND</th>
                            <th>USERNAME</th>
                            <th>IP</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(session.activities || []).length > 0 ? (
                            session.activities.map((activity, idx) => (
                              <tr key={`${session.session_id}-${idx}`}>
                                <td>{formatTime(activity?.time)}</td>
                                <td className="monoCell">{activity?.command || "-"}</td>
                                <td>
                                  {activity?.username ? (
                                    <span className="badge badgePurple">
                                      {activity.username}
                                    </span>
                                  ) : (
                                    "-"
                                  )}
                                </td>
                                <td>{activity?.remote_addr || "-"}</td>
                              </tr>
                            ))
                          ) : (
                            <tr>
                              <td colSpan="4" className="emptyCell">
                                No activity found for this session.
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        ) : (
          <div className="emptyBlock">No sessions found.</div>
        )}
      </div>
    </div>
  );

  return (
    <div className="dashboardLayout">
      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />

      <div
        className="dashboardPage"
        style={{
          marginLeft: collapsed ? "70px" : "220px",
        }}
      >
          <Topbar
    section="Monitor"
    page="Live Dashboard"
    statusText="LIVE FEED"
    onLogout={handleLogout}
      />
        <div className="dashboardShell">
          <h1 className="pageTitle">Live Dashboard</h1>
          <p className="pageSub">// real-time threat intelligence · api-driven monitor</p>

          <div className="filtersBar">
            <div className="filtersLeft">
              <div className="tableSearch filterField">
                <span className="searchIcon">⌕</span>
                <input
                  type="text"
                  placeholder="filter by username..."
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>

              <input
                className="dateInput"
                type="datetime-local"
                value={since}
                onChange={(e) => setSince(e.target.value)}
              />
            </div>

            <div className="filtersRight">
              <button className="miniBtn primaryBtn" onClick={applyFilters}>
                APPLY
              </button>
              <button className="miniBtn" onClick={resetFilters}>
                RESET
              </button>
              <button
                className="miniBtn"
                onClick={() => {
                  fetchConnections();
                  fetchCommands();
                  fetchSessions();
                  message.info("Refreshing data...");
                }}
              >
                REFRESH ALL
              </button>
            </div>
          </div>

          <div className="statGrid">
            <div className="statCard">
              <div className="statLabel">TOTAL CONNECTIONS</div>
              <div className="statValue">{connectionCount}</div>
              <div className="statMeta statCyan">live api data</div>
            </div>

            <div className="statCard">
              <div className="statLabel">TOTAL COMMANDS</div>
              <div className="statValue">{commandCount}</div>
              <div className="statMeta statGreen">captured commands</div>
            </div>

            <div className="statCard">
              <div className="statLabel">SESSIONS</div>
              <div className="statValue">{sessionCount}</div>
              <div className="statMeta statAmber">full traces stored</div>
            </div>

            <div className="statCard">
              <div className="statLabel">UNIQUE IPS</div>
              <div className="statValue">{uniqueIPs}</div>
              <div className="statMeta statRed">distinct sources</div>
            </div>

            <div className="statCard">
              <div className="statLabel">UNIQUE USERS</div>
              <div className="statValue">{uniqueUsers}</div>
              <div className="statMeta">credential spread</div>
            </div>
          </div>

          <div className="chartGrid">
            <div className="chartCard">
              <div className="chartHead">
                <div className="chartTitle">RECENT CONNECTION SNAPSHOT</div>
                <div className="chartBadge live">LIVE</div>
              </div>

              <div className="miniList">
                {recentConnections.length > 0 ? (
                  recentConnections.map((item, idx) => (
                    <div className="miniListRow" key={`recent-conn-${idx}`}>
                      <span className="miniMain">{item?.remote_addr || "-"}</span>
                      <span className="miniSub">{item?.username || "unknown"}</span>
                      <span className="miniMeta">{formatTime(item?.time)}</span>
                    </div>
                  ))
                ) : (
                  <div className="emptyBlock">No recent connections.</div>
                )}
              </div>
            </div>

            <div className="chartCard">
              <div className="chartHead">
                <div className="chartTitle">SESSION HEALTH</div>
                <div className="chartBadge top8">ACTIVE</div>
              </div>

              <div className="statusPanel">
                <div className="statusRow">
                  <span>Tracked Sessions</span>
                  <strong>{sessionCount}</strong>
                </div>
                <div className="statusRow">
                  <span>Active Sessions</span>
                  <strong>{activeSessionsCount}</strong>
                </div>
                <div className="statusRow">
                  <span>Stored Commands</span>
                  <strong>{commandCount}</strong>
                </div>
                <div className="statusRow">
                  <span>Known IP Sources</span>
                  <strong>{uniqueIPs}</strong>
                </div>
              </div>
            </div>
          </div>

          <div className="chartRow">
            <div className="chartCard">
              <div className="chartHead">
                <div className="chartTitle">LATEST COMMANDS</div>
              </div>

              <div className="miniList">
                {recentCommands.length > 0 ? (
                  recentCommands.map((item, idx) => (
                    <div className="miniListRow" key={`recent-cmd-${idx}`}>
                      <span className="miniMain monoAccent">
                        {item?.command || "-"}
                      </span>
                      <span className="miniSub">{item?.username || "unknown"}</span>
                      <span className="miniMeta">{formatTime(item?.time)}</span>
                    </div>
                  ))
                ) : (
                  <div className="emptyBlock">No recent commands.</div>
                )}
              </div>
            </div>

            <div className="chartCard">
              <div className="chartHead">
                <div className="chartTitle">QUICK NAVIGATION</div>
              </div>

              <div className="quickActions">
                <button
                  className={`tabBtn ${activeTab === "connections" ? "tabBtnActive" : ""}`}
                  onClick={() => setActiveTab("connections")}
                >
                  CONNECTIONS
                </button>
                <button
                  className={`tabBtn ${activeTab === "commands" ? "tabBtnActive" : ""}`}
                  onClick={() => setActiveTab("commands")}
                >
                  COMMANDS
                </button>
                <button
                  className={`tabBtn ${activeTab === "sessions" ? "tabBtnActive" : ""}`}
                  onClick={() => setActiveTab("sessions")}
                >
                  SESSIONS
                </button>
              </div>
            </div>
          </div>

          {activeTab === "connections" && renderConnectionsTable()}
          {activeTab === "commands" && renderCommandsTable()}
          {activeTab === "sessions" && renderSessions()}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;