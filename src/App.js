import React, { useEffect, useState } from "react";
import { Tabs, Table, Input, DatePicker, Button, message, Layout, Typography, Collapse } from "antd";
import axios from "axios";
import "./App.css";

const { Title } = Typography;
const { Content, Header } = Layout;
const { TabPane } = Tabs;
const { Panel } = Collapse;

const API_BASE = "http://localhost:8000"; 

function App() {
  const [connections, setConnections] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [commands, setCommands] = useState([]);
  const [activeTab, setActiveTab] = useState("1");
  const [activeSessionKey, setActiveSessionKey] = useState(null);
  const [loading, setLoading] = useState(false);
  const [username, setUsername] = useState("");
  const [since, setSince] = useState(null);

  const fetchData = async (type) => {
    setLoading(true);
    try {
      const params = {};
      if (username) params.username = username;
      if (since) params.since = since.toISOString();
      const res = await axios.get(`${API_BASE}/${type}`, { params });
      if (type === "connections") setConnections(res.data);
      else if (type === "commands") setCommands(res.data);
    } catch {
      message.error("Failed to fetch " + type);
    } finally {
      setLoading(false);
    }
  };

  const fetchSessions = async () => {
    try {
      const res = await axios.get(`${API_BASE}/sessions`);
      setSessions(res.data);
      return res.data;
    } catch {
      message.error("Failed to fetch sessions");
      return [];
    }
  };

  useEffect(() => {
    fetchData("connections");
    fetchData("commands");
    fetchSessions();
  }, []);

  const openSession = async (sessionId) => {
    if (!sessionId) return;
    // ensure sessions are loaded
    if (!sessions || sessions.length === 0) {
      await fetchSessions();
    }
    setActiveTab("3");
    setActiveSessionKey(String(sessionId));
  };

  const columnsCommon = [
    {
      title: "Time",
      dataIndex: "time",
      key: "time",
      render: (t) => (t ? new Date(t).toLocaleString() : "-"),
    },
    { title: "Username", dataIndex: "username", key: "username" },
  ];

  const connColumns = [
    ...columnsCommon,
    { title: "IP", dataIndex: "remote_addr", key: "remote_addr" },
    { title: "Password", dataIndex: "password", key: "password" },
    {
      title: "Session ID",
      dataIndex: "session_id",
      key: "session_id",
      render: (id) => (id ? <a style={{ cursor: "pointer" }} onClick={() => openSession(id)}>{String(id)}</a> : "-"),
    },
  ];

  const cmdColumns = [
    ...columnsCommon,
    { title: "Command", dataIndex: "command", key: "command" },
  ];

  return (
    <Layout>
      <Header className="header">
        <Title level={3} style={{ color: "white", margin: 0 }}>
          Honeypot Dashboard
        </Title>
      </Header>

      <Content className="content">
        <div className="filters">
          <Input
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={{ width: 180 }}
          />
          <DatePicker showTime placeholder="Since" onChange={(v) => setSince(v)} />
          <Button type="primary" onClick={() => { fetchData("connections"); fetchData("commands"); }}>
            Apply
          </Button>
          <Button onClick={() => { setUsername(""); setSince(null); fetchData("connections"); fetchData("commands"); }}>
            Reset
          </Button>
        </div>

        <Tabs activeKey={activeTab} onChange={(k) => { setActiveTab(k); if (k !== "3") setActiveSessionKey(null); }}>
          <TabPane tab="Connections" key="1">
            <Table
              dataSource={connections}
              columns={connColumns}
              loading={loading}
              rowKey={(r, i) => i}
              pagination={{ pageSize: 10 }}
            />
          </TabPane>

          <TabPane tab="Sessions" key="3">
            <Collapse accordion activeKey={activeSessionKey} onChange={(k) => setActiveSessionKey(k)}>
              {sessions.map((s) => (
                <Panel header={`Session: ${s.session_id}`} key={String(s.session_id)}>
                  <Table
                    dataSource={s.activities}
                    columns={[
                      { title: "Time", dataIndex: "time", render: (t) => new Date(t).toLocaleString() },
                      { title: "Command", dataIndex: "command" },
                      { title: "Username", dataIndex: "username" },
                      { title: "IP", dataIndex: "remote_addr" },
                    ]}
                    pagination={false}
                    rowKey={(r, i) => i}
                    size="small"
                  />
                </Panel>
              ))}
            </Collapse>
          </TabPane>
        </Tabs>
      </Content>
    </Layout>
  );
}

export default App;
