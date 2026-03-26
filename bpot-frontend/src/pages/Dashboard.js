import React, { useEffect, useMemo, useState } from "react";
import {
  Tabs,
  Table,
  Input,
  DatePicker,
  Button,
  message,
  Layout,
  Typography,
  Collapse,
  Tag,
  Tooltip,
} from "antd";
import {
  ReloadOutlined,
  FilterOutlined,
  ClearOutlined,
  LinkOutlined,
  ClockCircleOutlined,
  UserOutlined,
} from "@ant-design/icons";
import axios from "axios";
import "./Dashboard.css";

const { Title, Text } = Typography;
const { Content, Header } = Layout;
const { TabPane } = Tabs;
const { Panel } = Collapse;

const API_BASE =
  import.meta?.env?.VITE_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

function Dashboard() {
  const [connections, setConnections] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [commands, setCommands] = useState([]);

  const [activeTab, setActiveTab] = useState("1");
  const [activeSessionKey, setActiveSessionKey] = useState(null);

  const [loadingConnections, setLoadingConnections] = useState(false);
  const [loadingCommands, setLoadingCommands] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);

  const [username, setUsername] = useState("");
  const [since, setSince] = useState(null);

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

  const buildParams = () => {
    const params = {};
    if (username?.trim()) params.username = username.trim();
    if (since) params.since = since.toISOString();
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
    // initial load
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
    setSince(null);
    await Promise.all([fetchConnections(), fetchCommands()]);
    message.info("Filters reset");
  };

  const openSession = async (sessionId) => {
    if (!sessionId) return;

    if (!sessions || sessions.length === 0) {
      await fetchSessions();
    }
    setActiveTab("3");
    setActiveSessionKey(String(sessionId));
  };

  const columnsCommon = [
    {
      title: (
        <span className="col-title">
          <ClockCircleOutlined /> Time
        </span>
      ),
      dataIndex: "time",
      key: "time",
      render: (t) => (t ? new Date(t).toLocaleString() : "-"),
      width: 220,
    },
    {
      title: (
        <span className="col-title">
          <UserOutlined /> Username
        </span>
      ),
      dataIndex: "username",
      key: "username",
      render: (u) => (u ? <Tag className="tag-purple">{u}</Tag> : "-"),
      width: 160,
    },
  ];

  const connColumns = [
    ...columnsCommon,
    { title: "IP", dataIndex: "remote_addr", key: "remote_addr", width: 170 },
    {
      title: "Password",
      dataIndex: "password",
      key: "password",
      width: 200,
      render: (p) => (p ? <span className="mono">{p}</span> : "-"),
    },
    {
      title: "Session",
      dataIndex: "session_id",
      key: "session_id",
      width: 140,
      render: (id) =>
        id ? (
          <Button
            type="link"
            className="session-link"
            icon={<LinkOutlined />}
            onClick={() => openSession(id)}
          >
            {String(id)}
          </Button>
        ) : (
          "-"
        ),
    },
  ];

  const cmdColumns = [
    ...columnsCommon,
    {
      title: "Command",
      dataIndex: "command",
      key: "command",
      render: (c) => (c ? <span className="mono">{c}</span> : "-"),
    },
  ];

  return (
    <Layout className="dash-layout">
      <div className="dash-bg" />

      <Header className="dash-header">
        <div className="dash-header-left">
          <div className="brand-pill">BinaryPot</div>
          <div className="dash-title-wrap">
            <Title level={4} className="dash-title">
              Honeypot Dashboard
            </Title>
            <Text className="dash-subtitle">
              Monitor connections, sessions, and commands in one place.
            </Text>
          </div>
        </div>

        <div className="dash-header-right">
          <Tooltip title="Refresh everything">
            <Button
              className="ghost-btn"
              icon={<ReloadOutlined />}
              onClick={() => {
                fetchConnections();
                fetchCommands();
                fetchSessions();
                message.info("Refreshing data…");
              }}
            >
              Refresh
            </Button>
          </Tooltip>
        </div>
      </Header>

      <Content className="dash-content">
        <div className="dash-shell">
          {/* Filters */}
          <div className="filters-card">
            <div className="filters-left">
              <Input
                className="filter-input"
                placeholder="Filter by username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                allowClear
              />
              <DatePicker
                className="filter-date"
                showTime
                placeholder="Since…"
                value={since}
                onChange={(v) => setSince(v)}
              />
            </div>

            <div className="filters-right">
              <Button
                type="primary"
                icon={<FilterOutlined />}
                onClick={applyFilters}
              >
                Apply
              </Button>
              <Button
                className="ghost-btn"
                icon={<ClearOutlined />}
                onClick={resetFilters}
              >
                Reset
              </Button>
            </div>
          </div>

          {/* Tabs */}
          <Tabs
            className="dash-tabs"
            activeKey={activeTab}
            onChange={(k) => {
              setActiveTab(k);
              if (k !== "3") setActiveSessionKey(null);
            }}
          >
            <TabPane tab="Connections" key="1">
              <div className="table-wrap">
                <Table
                  dataSource={connections}
                  columns={connColumns}
                  loading={loadingConnections}
                  rowKey={(r, i) => `${r?.session_id || "conn"}-${i}`}
                  pagination={{ pageSize: 10, showSizeChanger: false }}
                  size="middle"
                />
              </div>
            </TabPane>

            <TabPane tab="Commands" key="2">
              <div className="table-wrap">
                <Table
                  dataSource={commands}
                  columns={cmdColumns}
                  loading={loadingCommands}
                  rowKey={(r, i) => `${r?.time || "cmd"}-${i}`}
                  pagination={{ pageSize: 10, showSizeChanger: false }}
                  size="middle"
                />
              </div>
            </TabPane>

            <TabPane tab="Sessions" key="3">
              <div className="sessions-top">
                <Text type="secondary">
                  Click a session to expand and view full activity.
                </Text>
                <Button
                  className="ghost-btn"
                  icon={<ReloadOutlined />}
                  loading={loadingSessions}
                  onClick={fetchSessions}
                >
                  Refresh sessions
                </Button>
              </div>

              <div className="sessions-wrap">
                <Collapse
                  accordion
                  activeKey={activeSessionKey}
                  onChange={(k) => setActiveSessionKey(k)}
                  className="session-collapse"
                >
                  {sessions.map((s) => (
                    <Panel
                      header={
                        <div className="session-header">
                          <span className="session-title">
                            Session: <span className="mono">{s.session_id}</span>
                          </span>
                          <Tag className="tag-soft">
                            {s?.activities?.length || 0} events
                          </Tag>
                        </div>
                      }
                      key={String(s.session_id)}
                    >
                      <Table
                        dataSource={s.activities || []}
                        columns={[
                          {
                            title: "Time",
                            dataIndex: "time",
                            render: (t) => (t ? new Date(t).toLocaleString() : "-"),
                            width: 220,
                          },
                          {
                            title: "Command",
                            dataIndex: "command",
                            render: (c) => (c ? <span className="mono">{c}</span> : "-"),
                          },
                          {
                            title: "Username",
                            dataIndex: "username",
                            render: (u) => (u ? <Tag className="tag-purple">{u}</Tag> : "-"),
                            width: 160,
                          },
                          { title: "IP", dataIndex: "remote_addr", width: 170 },
                        ]}
                        pagination={false}
                        rowKey={(r, i) => `${s.session_id}-${i}`}
                        size="small"
                        className="session-table"
                      />
                    </Panel>
                  ))}
                </Collapse>
              </div>
            </TabPane>
          </Tabs>
        </div>
      </Content>
    </Layout>
  );
}

export default Dashboard;
