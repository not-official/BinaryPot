```markdown
# 🛡️ BinaryPot

**LLM-Powered SSH Honeypot for Realistic Attacker Simulation**

BinaryPot is a high-interaction SSH honeypot that uses Large Language Models to simulate realistic Linux terminal behavior and analyze attacker behavior and threats. It dynamically generates state-aware command responses to engage attackers, capture their actions, and support deeper cybersecurity analysis.

---

## 🚀 Features

* 🧠 **LLM-Powered Shell Simulation**  
  Generates realistic Linux terminal outputs using fine-tuned local models

* 🔐 **High-Interaction Honeypot**  
  Engages attackers instead of blocking them immediately

* ⚙️ **State-Aware Responses**  
  Behavior adapts based on user, working directory, installed tools, permissions, and network rules

* 📡 **Command Logging & Analysis**  
  Captures attacker commands, outputs, sessions, and activity patterns

* 🔌 **Backend API (FastAPI)**  
  Handles authentication, sessions, logs, approvals, and honeypot logic

* 💻 **Frontend Dashboard (React + AntD)**  
  Clean dashboard for monitoring and managing honeypot activity

* 🤖 **Local Model Support**  
  Supports locally stored AI models for shell response generation

---

## 🏗️ Project Structure

```bash
BinaryPot/
│
├── bpot-backend/     # FastAPI backend, honeypot engine, auth/API, AI logic
├── bpot-frontend/    # React frontend dashboard
└── README.md
```

---

## ⚙️ Tech Stack

### Backend

* Python
* FastAPI
* SQLAlchemy
* JWT Authentication
* SSH honeypot engine
* Local LLM integration

### Frontend

* React
* Ant Design (AntD)
* Axios
* React Router

### ML / AI

* Fine-tuned local models for shell response generation
* QLoRA / LoRA fine-tuning for lightweight adapter training
* State-aware command response generation
* Behavioral analysis
* Threat analysis
* Report support through API

---

## 🧠 How It Works

1. Attacker connects through SSH into a simulated environment
2. Commands are parsed with system state context
3. Hardcoded commands return fast and realistic shell outputs
4. Complex or unknown commands can be handled by local AI models
5. All commands, outputs, and sessions are logged for analysis
6. The frontend dashboard displays captured honeypot activity

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

# activate virtual environment
source venv/bin/activate   # Linux / macOS
venv\Scripts\activate      # Windows

# install dependencies
pip install -r requirements.txt
```

---

## 🤖 Local AI Model Setup

BinaryPot requires local AI model files for generating realistic shell responses.

The model files are large, so they are **not included in this GitHub repository**.  
Each user must download the required model files separately and place them inside the backend `models` folder.

Create a `models` folder inside `bpot-backend`:

```bash
cd bpot-backend
mkdir models
```

Expected structure:

```bash
bpot-backend/
│
├── models/
│   ├── model-folder-1/
│   │   ├── adapter_config.json
│   │   ├── adapter_model.safetensors
│   │   └── other model files...
│   │
│   └── model-folder-2/
│       ├── config files...
│       └── model files...
│
├── honeypot/
├── ai/
├── app/
└── requirements.txt
```

Example:

```bash
bpot-backend/models/your-model-folder-name/
```

Make sure the model path in the backend code matches the folder name inside `models`.

> Note: The `models/` folder is ignored by Git because model files are large. Models must be downloaded separately and placed manually inside the correct folder.

---

## ▶️ Running the Project

### Start Honeypot Server

From inside `bpot-backend`:

```bash
py -m honeypot.run-honeypot
```

Connect to the honeypot:

```bash
ssh -p 2222 localhost
```

---

### Start Backend API Server

From inside `bpot-backend`:

```bash
uvicorn app.main:app --reload
```

---

### Start Frontend

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

SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ADMIN_EMAIL=admin@example.com
```

If external AI APIs are used in future versions, add the required API keys in the backend `.env` file.

---

## ⚠️ Important Notes

* Model files are not pushed to GitHub
* Create the `models` folder manually inside `bpot-backend`
* Download and place required models inside the `models` folder
* Ensure `__init__.py` files exist in required Python folders for imports to work correctly
* Run backend commands from inside the `bpot-backend` directory
* Keep `.env`, model files, SSH keys, and local virtual environments out of Git

---

## 📄 License

This is a final-year project built for educational and research purposes.
```