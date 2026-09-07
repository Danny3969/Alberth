const fs = require('fs');
const path = require('path');

const venvPython = path.join(__dirname, 'venv/bin/python3');
const pythonBin = process.env.PYTHON_PATH || (fs.existsSync(venvPython) ? venvPython : 'python3');

module.exports = {
  apps: [
    {
      name: "alberth-web",
      cwd: __dirname,
      script: pythonBin,
      args: "alberth_web_server.py",
      interpreter: "none",
      autorestart: true,
      watch: false
    },
    {
      name: "alberth-voice",
      cwd: __dirname,
      script: pythonBin,
      args: "alberth_voice_server.py",
      interpreter: "none",
      autorestart: true,
      watch: false
    },
    {
      name: "alberth-reminders",
      cwd: __dirname,
      script: pythonBin,
      args: "alberth_reminders_daemon.py",
      interpreter: "none",
      autorestart: true,
      watch: false
    },
    {
      name: "alberth-qa-watcher",
      cwd: __dirname,
      script: pythonBin,
      args: "alberth_qa_watcher.py",
      interpreter: "none",
      autorestart: true,
      watch: false
    }
  ]
};
