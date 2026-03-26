# 🛡️ BinaryPot

**LLM-Powered SSH Honeypot for Realistic Attacker Simulation**

BinaryPot is a high-interaction SSH honeypot that uses a fine-tuned Large Language Model to simulate realistic Linux terminal behavior. It dynamically generates state-aware command responses to engage attackers, capture their actions, and enable deeper cybersecurity analysis.

---

## 🚀 Features

* 🧠 **LLM-Powered Shell Simulation**
  Generates realistic Linux terminal outputs using a fine-tuned model

* 🔐 **High-Interaction Honeypot**
  Engages attackers instead of blocking them

* ⚙️ **State-Aware Responses**
  Behavior adapts based on system state (user, tools, permissions, network restrictions)

* 📡 **Command Logging & Analysis**
  Captures attacker commands for monitoring and research

* 🔌 **Backend API (FastAPI)**
  Handles authentication, sessions, and honeypot logic

* 💻 **Frontend Dashboard (Next + AntD)**
  Clean UI for managing and observing honeypot activity

---

## 🏗️ Project Structure

```bash
BinaryPot/
│
├── bpot-backend/     # FastAPI backend (honeypot engine + auth/API + AI)
├── bpot-frontend/    # NEXT frontend (dashboard UI)
└── README.md
```

---

## ⚙️ Tech Stack

### Backend

* Python
* FastAPI
* SQLAlchemy
* JWT Authentication
* LLM Integration (fine-tuned model)

### Frontend

* Next
* Ant Design (AntD)
* Axios

### ML / AI

* QLoRA / LoRA fine-tuning for shell response
* Behavorial analysis
* Threat analysis
* API for reports

---

## 🧠 How It Works

1. Attacker connects via SSH (simulated environment)
2. Commands are parsed with system **state context**
3. LLM generates realistic terminal output:

   * Valid commands → realistic response
   * Invalid commands → shell errors
   * Restricted actions → permission/network failures
4. All interactions are logged for analysis

---

## 🔧 Installation

### 1. Clone Repository

```bash
git clone https://github.com/not-official/BinaryPot.git
cd BinaryPot
```

---

### 2. Backend Setup

```bash
cd bpot-backend

# create virtual environment
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate (Windows)

# install dependencies
pip install -r requirements.txt

# start honeypot server
py -m honeypot.run_honeypot

# connect to honeypot (SSH simulation)
ssh -p 2222 localhost

# run api server
uvicorn app.main:app --reload
```

---

### 3. Frontend Setup

```bash
cd bpot-frontend

npm install
npm start
```

---

## 🔐 Environment Variables

Create `.env` files where required.

### Backend example:

```env
JWT_SECRET=your_secret_key
DATABASE_URL=sqlite:///./binarypot.db
```

---

## 📄 License

This project is for educational and research purposes.

---

