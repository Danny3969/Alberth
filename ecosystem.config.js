module.exports = {
  apps: [
    {
      name: "alberth-web",
      cwd: __dirname,
      script: process.env.PYTHON_PATH || "python3",
      args: "alberth_web_server.py",
      interpreter: "none",
      autorestart: true,
      watch: false
    },
    {
      name: "alberth-voice",
      cwd: __dirname,
      script: process.env.PYTHON_PATH || "python3",
      args: "alberth_voice_server.py",
      interpreter: "none",
      autorestart: true,
      watch: false
    },
    {
      name: "alberth-reminders",
      cwd: __dirname,
      script: process.env.PYTHON_PATH || "python3",
      args: "alberth_reminders_daemon.py",
      interpreter: "none",
      autorestart: true,
      watch: false
    },
    {
      name: "alberth-qa-watcher",
      cwd: __dirname,
      script: process.env.PYTHON_PATH || "python3",
      args: "alberth_qa_watcher.py",
      interpreter: "none",
      autorestart: true,
      watch: false
    }
  ]
};
