// Dashboard.js
import React, { useEffect, useMemo, useState } from "react";
import { message } from "antd";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import "./Dashboard.css";


const API_BASE =
  process.env.REACT_APP_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";


function Dashboard() {
  const [collapsed, setCollapsed] = useState(false);


  const [connections, setConnections] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [commands, setCommands] = useState([]);
  const [analysisResults, setAnalysisResults] = useState([]);


  const [activeTab, setActiveTab] = useState("connections");
  const [activeSessionKey, setActiveSessionKey] = useState(null);


  const [selectedBehaviorSession, setSelectedBehaviorSession] = useState(null);
  const [behaviorModalOpen, setBehaviorModalOpen] = useState(false);


  const [loadingConnections, setLoadingConnections] = useState(false);
  const [loadingCommands, setLoadingCommands] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);


  const [username, setUsername] = useState("");
  const [since, setSince] = useState("");
  const [tableFilter, setTableFilter] = useState("");


  const [reportFrom, setReportFrom] = useState("");
  const [reportTo, setReportTo] = useState("");


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


    if (username.trim()) params.username = username.trim();


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


  const fetchAnalysisResults = async () => {
    setLoadingAnalysis(true);


    try {
      const res = await api.get("/analysis/results");
      setAnalysisResults(Array.isArray(res.data) ? res.data : []);
      return Array.isArray(res.data) ? res.data : [];
    } catch (err) {
      // This can be missing before the first analysis run, so do not show a loud error.
      setAnalysisResults([]);
      return [];
    } finally {
      setLoadingAnalysis(false);
    }
  };


  const triggerAnalysisRun = async () => {
    try {
      await api.post("/analysis/run");
      message.success("Analysis started. Refresh again after it completes.");
    } catch (err) {
      message.error(err?.response?.data?.detail || "Failed to start analysis");
    }
  };


  const refreshAll = async () => {
    await Promise.all([
      fetchConnections(),
      fetchCommands(),
      fetchSessions(),
      fetchAnalysisResults(),
    ]);


    message.info("Dashboard refreshed");
  };


  useEffect(() => {
    refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


  const applyFilters = async () => {
    await Promise.all([fetchConnections(), fetchCommands()]);
    message.success("Filters applied");
  };


  const resetFilters = async () => {
    setUsername("");
    setSince("");
    setTableFilter("");


    await Promise.all([fetchConnections(), fetchCommands()]);
    message.info("Filters reset");
  };


  const openSession = async (sessionId) => {
    if (!sessionId) return;


    if (!sessions.length) await fetchSessions();


    setActiveTab("sessions");
    setActiveSessionKey(String(sessionId));
  };


  const formatTime = (value) => {
    if (!value) return "-";


    const d = new Date(value);


    if (Number.isNaN(d.getTime())) return value;


    return d.toLocaleString();
  };


  const safeFilePart = (value) => {
    return String(value || "unknown")
      .replace(/[^a-zA-Z0-9-_]/g, "_")
      .slice(0, 80);
  };


  const downloadTextFile = (filename, content) => {
    const blob = new Blob([content], {
      type: "text/plain;charset=utf-8",
    });


    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");


    link.href = url;
    link.download = filename;


    document.body.appendChild(link);
    link.click();


    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };


  const analysisBySessionId = useMemo(() => {
    const map = new Map();


    analysisResults.forEach((item) => {
      if (item?.session_id) {
        map.set(String(item.session_id), item);
      }
    });


    return map;
  }, [analysisResults]);


  const getSessionAnalysis = (sessionId) => {
    if (!sessionId) return null;
    return analysisBySessionId.get(String(sessionId)) || null;
  };


  const getRawSession = (sessionId) => {
    if (!sessionId) return null;


    return (
      sessions.find((session) => String(session.session_id) === String(sessionId)) ||
      null
    );
  };


  const getSessionTime = (session, analysis) => {
    const activities = session?.activities || [];
    const analyzedCommands = analysis?.commands || [];


    const firstActivity = activities[0];
    const lastActivity = activities[activities.length - 1];


    const firstAnalyzed = analyzedCommands[0];
    const lastAnalyzed = analyzedCommands[analyzedCommands.length - 1];


    return {
      startedAt:
        analysis?.started_at ||
        firstActivity?.time ||
        firstAnalyzed?.time ||
        "-",
      endedAt:
        analysis?.ended_at ||
        lastActivity?.time ||
        lastAnalyzed?.time ||
        "-",
    };
  };


  const getCommandsForReport = (session, analysis) => {
    if (analysis?.commands?.length) {
      return analysis.commands.map((cmd, index) => ({
        index: cmd.command_index ?? index + 1,
        time: cmd.time || "",
        command: cmd.command || "-",
        cwd: cmd.cwd || "-",
        output: cmd.output || "",
        intent: cmd.intent || "Not analyzed",
        description: cmd.description || "No description available.",
      }));
    }


    return (session?.activities || []).map((activity, index) => ({
      index: index + 1,
      time: activity?.time || "",
      command: activity?.command || "-",
      cwd: activity?.cwd || "-",
      output: activity?.output || "",
      intent: "Analysis not available",
      description: "Run behavior analysis to generate intent and description.",
    }));
  };


  const buildSessionReportText = (session, analysis) => {
    const sessionId = analysis?.session_id || session?.session_id || "unknown";
    const remoteAddr =
      analysis?.remote_addr ||
      session?.remote_addr ||
      session?.activities?.[0]?.remote_addr ||
      "-";
    const attackerUsername =
      analysis?.username ||
      session?.username ||
      session?.activities?.[0]?.username ||
      "-";


    const { startedAt, endedAt } = getSessionTime(session, analysis);
    const commandsForReport = getCommandsForReport(session, analysis);


    const summary =
      analysis?.summary ||
      "Behavior summary is not available. Run analysis after the session ends.";


    const lines = [];


    lines.push("BinaryPot SSH Honeypot Session Report");
    lines.push("=====================================");
    lines.push("");
    lines.push(`Session ID      : ${sessionId}`);
    lines.push(`Attacker IP     : ${remoteAddr}`);
    lines.push(`Username        : ${attackerUsername}`);
    lines.push(`Started At      : ${formatTime(startedAt)}`);
    lines.push(`Ended At        : ${formatTime(endedAt)}`);
    lines.push(`Command Count   : ${commandsForReport.length}`);
    lines.push("");
    lines.push("Behavior Summary");
    lines.push("----------------");
    lines.push(summary);
    lines.push("");
    lines.push("Command Timeline");
    lines.push("----------------");


    if (!commandsForReport.length) {
      lines.push("No commands recorded.");
    }


    commandsForReport.forEach((cmd) => {
      lines.push("");
      lines.push(`#${cmd.index}`);
      lines.push(`Time        : ${formatTime(cmd.time)}`);
      lines.push(`CWD         : ${cmd.cwd}`);
      lines.push(`Command     : ${cmd.command}`);
      lines.push(`Intent      : ${cmd.intent}`);
      lines.push(`Description : ${cmd.description}`);


      if (cmd.output) {
        lines.push("Output      :");
        lines.push(String(cmd.output).trim());
      }
    });


    lines.push("");
    lines.push("End of Report");


    return lines.join("\n");
  };


  const handleDownloadSingleSession = async (sessionId) => {
    let latestAnalysis = analysisResults;


    if (!latestAnalysis.length) {
      latestAnalysis = await fetchAnalysisResults();
    }


    const analysis =
      latestAnalysis.find((item) => String(item.session_id) === String(sessionId)) ||
      getSessionAnalysis(sessionId);


    const session = getRawSession(sessionId);


    if (!analysis && !session) {
      message.warning("No session data found for this session.");
      return;
    }


    const report = buildSessionReportText(session, analysis);


    downloadTextFile(
      `binarypot_session_${safeFilePart(sessionId)}_report.txt`,
      report
    );


    message.success("Session report downloaded");
  };


  const handleDownloadRangeReport = async () => {
    if (!reportFrom || !reportTo) {
      message.warning("Please select both start and end time first.");
      return;
    }


    const fromTime = new Date(reportFrom);
    const toTime = new Date(reportTo);


    if (Number.isNaN(fromTime.getTime()) || Number.isNaN(toTime.getTime())) {
      message.warning("Invalid report date range.");
      return;
    }


    if (fromTime > toTime) {
      message.warning("Start time must be before end time.");
      return;
    }


    let latestAnalysis = analysisResults;


    if (!latestAnalysis.length) {
      latestAnalysis = await fetchAnalysisResults();
    }


    const sessionIdsInRange = new Set();


    sessions.forEach((session) => {
      const analysis = latestAnalysis.find(
        (item) => String(item.session_id) === String(session.session_id)
      );


      const { startedAt, endedAt } = getSessionTime(session, analysis);


      const startDate = new Date(startedAt);
      const endDate = new Date(endedAt);


      const validStart = !Number.isNaN(startDate.getTime()) ? startDate : null;
      const validEnd = !Number.isNaN(endDate.getTime()) ? endDate : validStart;


      if (!validStart) return;


      if (validStart <= toTime && validEnd >= fromTime) {
        sessionIdsInRange.add(String(session.session_id));
      }
    });


    latestAnalysis.forEach((analysis) => {
      const startDate = new Date(analysis.started_at);
      const endDate = new Date(analysis.ended_at || analysis.started_at);


      if (Number.isNaN(startDate.getTime())) return;


      if (startDate <= toTime && endDate >= fromTime) {
        sessionIdsInRange.add(String(analysis.session_id));
      }
    });


    if (!sessionIdsInRange.size) {
      message.warning("No sessions found in the selected time range.");
      return;
    }


    const reports = Array.from(sessionIdsInRange).map((sessionId) => {
      const session = getRawSession(sessionId);
      const analysis =
        latestAnalysis.find((item) => String(item.session_id) === String(sessionId)) ||
        null;


      return buildSessionReportText(session, analysis);
    });


    const content = [
      "BinaryPot Range Session Report",
      "==============================",
      "",
      `From: ${formatTime(fromTime.toISOString())}`,
      `To  : ${formatTime(toTime.toISOString())}`,
      `Sessions Included: ${sessionIdsInRange.size}`,
      "",
      "============================================================",
      "",
      reports.join("\n\n============================================================\n\n"),
    ].join("\n");


    downloadTextFile(
      `binarypot_range_report_${safeFilePart(reportFrom)}_to_${safeFilePart(reportTo)}.txt`,
      content
    );


    message.success("Range report downloaded");
  };


  const openBehaviorView = async (sessionId) => {
    let latestAnalysis = analysisResults;


    if (!latestAnalysis.length) {
      latestAnalysis = await fetchAnalysisResults();
    }


    const analysis =
      latestAnalysis.find((item) => String(item.session_id) === String(sessionId)) ||
      getSessionAnalysis(sessionId);


    const rawSession = getRawSession(sessionId);


    if (!analysis && !rawSession) {
      message.warning("No behavior data found for this session.");
      return;
    }


    setSelectedBehaviorSession({
      sessionId,
      rawSession,
      analysis,
    });


    setBehaviorModalOpen(true);
  };


  const closeBehaviorView = () => {
    setBehaviorModalOpen(false);
    setSelectedBehaviorSession(null);
  };


  const uniqueIPs = useMemo(() => {
    return new Set(connections.map((c) => c.remote_addr).filter(Boolean)).size;
  }, [connections]);


  const commandCount = commands.length;
  const connectionCount = connections.length;
  const sessionCount = sessions.length;


  const recentConnections = useMemo(() => connections.slice(0, 6), [connections]);
  const recentCommands = useMemo(() => commands.slice(0, 6), [commands]);


  const filteredConnections = useMemo(() => {
    const q = tableFilter.trim().toLowerCase();


    if (!q) return connections;


    return connections.filter(
      (item) =>
        String(item?.remote_addr || "").toLowerCase().includes(q) ||
        String(item?.username || "").toLowerCase().includes(q) ||
        String(item?.session_id || "").toLowerCase().includes(q)
    );
  }, [connections, tableFilter]);


  const filteredCommands = useMemo(() => {
    const q = tableFilter.trim().toLowerCase();


    if (!q) return commands;


    return commands.filter(
      (item) =>
        String(item?.command || "").toLowerCase().includes(q) ||
        String(item?.username || "").toLowerCase().includes(q)
    );
  }, [commands, tableFilter]);


  const renderConnectionsTable = () => (
    <div className="tableCard">
      <div className="tableHeadRow">
        <div>
          <div className="chartTitle">CONNECTIONS</div>
          <div className="smallMuted">Login attempts captured by BinaryPot</div>
        </div>


        <div className="tableHeadActions">
          <div className="tableSearch">
            <span className="searchIcon">⌕</span>
            <input
              type="text"
              placeholder="search ip, username, session..."
              value={tableFilter}
              onChange={(e) => setTableFilter(e.target.value)}
            />
          </div>


          <button className="miniBtn" onClick={fetchConnections} disabled={loadingConnections}>
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
              <th>IP ADDRESS</th>
              <th>PASSWORD</th>
              <th>SESSION</th>
            </tr>
          </thead>


          <tbody>
            {filteredConnections.length ? (
              filteredConnections.map((row, index) => (
                <tr key={`${row?.session_id || "conn"}-${index}`}>
                  <td>{formatTime(row?.time)}</td>
                  <td>
                    <span className="badge badgePurple">{row?.username || "unknown"}</span>
                  </td>
                  <td>
                    <span className="ipLink">{row?.remote_addr || "-"}</span>
                  </td>
                  <td>{row?.password || "-"}</td>
                  <td>
                    {row?.session_id ? (
                      <button className="sessionLinkBtn" onClick={() => openSession(row.session_id)}>
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
        <div>
          <div className="chartTitle">COMMANDS</div>
          <div className="smallMuted">Commands executed inside fake shell</div>
        </div>


        <div className="tableHeadActions">
          <div className="tableSearch">
            <span className="searchIcon">⌕</span>
            <input
              type="text"
              placeholder="search command or username..."
              value={tableFilter}
              onChange={(e) => setTableFilter(e.target.value)}
            />
          </div>


          <button className="miniBtn" onClick={fetchCommands} disabled={loadingCommands}>
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
            {filteredCommands.length ? (
              filteredCommands.map((row, index) => (
                <tr key={`${row?.time || "cmd"}-${index}`}>
                  <td>{formatTime(row?.time)}</td>
                  <td>
                    <span className="badge badgePurple">{row?.username || "unknown"}</span>
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


  const renderBehaviorModal = () => {
    if (!behaviorModalOpen || !selectedBehaviorSession) return null;


    const { sessionId, rawSession, analysis } = selectedBehaviorSession;
    const commandsForReport = getCommandsForReport(rawSession, analysis);


    const remoteAddr =
      analysis?.remote_addr ||
      rawSession?.remote_addr ||
      rawSession?.activities?.[0]?.remote_addr ||
      "-";


    const attackerUsername =
      analysis?.username ||
      rawSession?.username ||
      rawSession?.activities?.[0]?.username ||
      "-";


    const { startedAt, endedAt } = getSessionTime(rawSession, analysis);


    return (
      <div className="behaviorOverlay">
        <div className="behaviorModal">
          <div className="behaviorModalHead">
            <div>
              <div className="chartTitle">ATTACKER BEHAVIOR ANALYSIS</div>
              <div className="smallMuted">
                Session <span className="monoAccent">{sessionId}</span>
              </div>
            </div>


            <button className="miniBtn" onClick={closeBehaviorView}>
              CLOSE
            </button>
          </div>


          <div className="behaviorSummaryGrid">
            <div className="behaviorInfoCard">
              <div className="statLabel">ATTACKER IP</div>
              <div className="behaviorInfoValue">{remoteAddr}</div>
            </div>


            <div className="behaviorInfoCard">
              <div className="statLabel">USERNAME</div>
              <div className="behaviorInfoValue">{attackerUsername}</div>
            </div>


            <div className="behaviorInfoCard">
              <div className="statLabel">COMMANDS</div>
              <div className="behaviorInfoValue">{commandsForReport.length}</div>
            </div>


            <div className="behaviorInfoCard">
              <div className="statLabel">STATUS</div>
              <div className="behaviorInfoValue">
                {analysis ? "ANALYZED" : "RAW ONLY"}
              </div>
            </div>
          </div>


          <div className="behaviorSection">
            <div className="chartTitle">SESSION TIMELINE</div>
            <div className="behaviorMetaLine">
              <span>Started: {formatTime(startedAt)}</span>
              <span>Ended: {formatTime(endedAt)}</span>
            </div>
          </div>


          <div className="behaviorSection">
            <div className="chartTitle">SUMMARY</div>
            <p className="behaviorSummaryText">
              {analysis?.summary ||
                "No behavior summary available yet. Run analysis after the session ends."}
            </p>
          </div>


          <div className="behaviorSection">
            <div className="chartTitle">COMMAND INTENT DETAILS</div>


            <div className="behaviorCommandList">
              {commandsForReport.length ? (
                commandsForReport.map((cmd, index) => (
                  <div className="behaviorCommandCard" key={`${sessionId}-behavior-${index}`}>
                    <div className="behaviorCommandTop">
                      <span className="badge badgeSoft">#{cmd.index || index + 1}</span>
                      <span className="monoCell">{cmd.command}</span>
                    </div>


                    <div className="behaviorCommandMeta">
                      <span>CWD: {cmd.cwd || "-"}</span>
                      <span>TIME: {formatTime(cmd.time)}</span>
                    </div>


                    <div className="behaviorIntentRow">
                      <span className="badge badgePurple">{cmd.intent || "Unknown"}</span>
                    </div>


                    <p className="behaviorDescription">
                      {cmd.description || "No description available."}
                    </p>


                    {cmd.output ? (
                      <pre className="behaviorOutput">{String(cmd.output).trim()}</pre>
                    ) : null}
                  </div>
                ))
              ) : (
                <div className="emptyBlock">No command behavior found.</div>
              )}
            </div>
          </div>


          <div className="behaviorFooter">
            <button
              className="miniBtn reportBtn"
              onClick={() => handleDownloadSingleSession(sessionId)}
            >
              DOWNLOAD REPORT
            </button>
          </div>
        </div>
      </div>
    );
  };


  const renderSessions = () => (
    <div className="tableCard">
      <div className="tableHeadRow">
        <div>
          <div className="chartTitle">SESSIONS</div>
          <div className="smallMuted">Expand a session to view attacker activity</div>
        </div>


        <div className="tableHeadActions reportRangeActions">
          <input
            className="dateInput reportDateInput"
            type="datetime-local"
            value={reportFrom}
            onChange={(e) => setReportFrom(e.target.value)}
          />


          <input
            className="dateInput reportDateInput"
            type="datetime-local"
            value={reportTo}
            onChange={(e) => setReportTo(e.target.value)}
          />


          <button className="miniBtn reportBtn" onClick={handleDownloadRangeReport}>
            DOWNLOAD RANGE REPORT
          </button>


          <button className="miniBtn" onClick={triggerAnalysisRun}>
            RUN ANALYSIS
          </button>


          <button className="miniBtn" onClick={fetchAnalysisResults} disabled={loadingAnalysis}>
            {loadingAnalysis ? "ANALYZING..." : "REFRESH ANALYSIS"}
          </button>


          <button className="miniBtn" onClick={fetchSessions} disabled={loadingSessions}>
            {loadingSessions ? "LOADING..." : "REFRESH"}
          </button>
        </div>
      </div>


      <div className="sessionsWrap">
        {sessions.length ? (
          sessions.map((session) => {
            const isOpen = activeSessionKey === String(session.session_id);
            const analysis = getSessionAnalysis(session.session_id);
            const analyzedCommandCount = analysis?.commands?.length || 0;
            const rawEventCount = (session?.activities || []).length;


            return (
              <div className="sessionItem" key={String(session.session_id)}>
                <button
                  className={`sessionToggle ${isOpen ? "sessionToggleOpen" : ""}`}
                  onClick={() => setActiveSessionKey(isOpen ? null : String(session.session_id))}
                >
                  <div className="sessionHeaderLeft">
                    <span className="sessionMainLabel">
                      Session <span className="monoAccent">{session.session_id}</span>
                    </span>
                  </div>


                  <div className="sessionHeaderRight">
                    {analysis ? (
                      <span className="badge badgePurple">ANALYZED</span>
                    ) : (
                      <span className="badge badgeSoft">RAW</span>
                    )}


                    <span className="badge badgeSoft">
                      {analyzedCommandCount || rawEventCount} events
                    </span>


                    <span className="sessionArrow">{isOpen ? "−" : "+"}</span>
                  </div>
                </button>


                {isOpen && (
                  <div className="sessionBody">
                    <div className="sessionReportBar">
                      <div>
                        <div className="chartTitle">SESSION REPORT</div>
                        <div className="smallMuted">
                          Download report or inspect attacker behavior for this session
                        </div>
                      </div>


                      <div className="sessionActionGroup">
                        <button
                          className="miniBtn reportBtn"
                          onClick={() => handleDownloadSingleSession(session.session_id)}
                        >
                          DOWNLOAD REPORT
                        </button>


                        <button
                          className="miniBtn primaryBtn"
                          onClick={() => openBehaviorView(session.session_id)}
                        >
                          VIEW ATTACKER BEHAVIOR
                        </button>
                      </div>
                    </div>


                    {analysis?.summary ? (
                      <div className="sessionAnalysisPreview">
                        <div className="chartTitle">AI SUMMARY</div>
                        <p>{analysis.summary}</p>
                      </div>
                    ) : null}


                    <div className="tableWrap">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>TIME</th>
                            <th>COMMAND</th>
                            <th>INTENT</th>
                            <th>USERNAME</th>
                            <th>IP</th>
                          </tr>
                        </thead>


                        <tbody>
                          {(session.activities || []).length ? (
                            session.activities.map((activity, idx) => {
                              const analyzedCommand = analysis?.commands?.find(
                                (cmd) =>
                                  String(cmd.command_index) === String(activity.command_index) ||
                                  String(cmd.command || "") === String(activity.command || "")
                              );


                              return (
                                <tr key={`${session.session_id}-${idx}`}>
                                  <td>{formatTime(activity?.time)}</td>
                                  <td className="monoCell">{activity?.command || "-"}</td>
                                  <td>
                                    {analyzedCommand?.intent ? (
                                      <span className="badge badgePurple">
                                        {analyzedCommand.intent}
                                      </span>
                                    ) : (
                                      <span className="badge badgeSoft">-</span>
                                    )}
                                  </td>
                                  <td>
                                    <span className="badge badgePurple">
                                      {activity?.username || "unknown"}
                                    </span>
                                  </td>
                                  <td>{activity?.remote_addr || "-"}</td>
                                </tr>
                              );
                            })
                          ) : (
                            <tr>
                              <td colSpan="5" className="emptyCell">
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
          <div className="dashboardHero">
            <div>
              <h1 className="pageTitle">Live Dashboard</h1>
              <p className="pageSub">{"// real-time honeypot activity monitor"}</p>
            </div>
          </div>


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


              <button className="miniBtn" onClick={refreshAll}>
                REFRESH
              </button>
            </div>
          </div>


          <div className="statGrid refinedStats">
            <div className="statCard">
              <div className="statLabel">CONNECTIONS</div>
              <div className="statValue">{connectionCount}</div>
              <div className="statMeta statCyan">login attempts</div>
            </div>


            <div className="statCard">
              <div className="statLabel">COMMANDS</div>
              <div className="statValue">{commandCount}</div>
              <div className="statMeta statGreen">shell activity</div>
            </div>


            <div className="statCard">
              <div className="statLabel">SESSIONS</div>
              <div className="statValue">{sessionCount}</div>
              <div className="statMeta statAmber">grouped traces</div>
            </div>


            <div className="statCard">
              <div className="statLabel">UNIQUE IPS</div>
              <div className="statValue">{uniqueIPs}</div>
              <div className="statMeta statRed">source addresses</div>
            </div>
          </div>


          <div className="chartGrid refinedOverview">
            <div className="chartCard">
              <div className="chartHead">
                <div className="chartTitle">RECENT CONNECTIONS</div>
                <div className="chartBadge live">LIVE</div>
              </div>


              <div className="miniList">
                {recentConnections.length ? (
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
                <div className="chartTitle">LATEST COMMANDS</div>
                <div className="chartBadge top8">TOP 6</div>
              </div>


              <div className="miniList">
                {recentCommands.length ? (
                  recentCommands.map((item, idx) => (
                    <div className="miniListRow commandRow" key={`recent-cmd-${idx}`}>
                      <span className="miniMain monoAccent">{item?.command || "-"}</span>
                      <span className="miniSub">{item?.username || "unknown"}</span>
                      <span className="miniMeta">{formatTime(item?.time)}</span>
                    </div>
                  ))
                ) : (
                  <div className="emptyBlock">No recent commands.</div>
                )}
              </div>
            </div>
          </div>


          <div className="tabBar">
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


          {activeTab === "connections" && renderConnectionsTable()}
          {activeTab === "commands" && renderCommandsTable()}
          {activeTab === "sessions" && renderSessions()}
        </div>
      </div>


      {renderBehaviorModal()}
    </div>
  );
}


export default Dashboard;



