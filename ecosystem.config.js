module.exports = {
  apps: [
    {
      name: "alberth-web",
      cwd: "/Users/digitalspace/.openclaw/workspace",
      script: "/usr/local/bin/python3",
      args: "alberth_web_server.py",
      interpreter: "none",
      autorestart: true,
      watch: false
    },
    {
      name: "alberth-voice",
      cwd: "/Users/digitalspace/.openclaw/workspace",
      script: "/usr/local/bin/python3",
      args: "alberth_voice_server.py",
      interpreter: "none",
      autorestart: true,
      watch: false
    },
    {
      name: "alberth-reminders",
      cwd: "/Users/digitalspace/.openclaw/workspace",
      script: "/usr/local/bin/python3",
      args: "alberth_reminders_daemon.py",
      interpreter: "none",
      autorestart: true,
      watch: false
    },
    {
      name: "alberth-qa-watcher",
      cwd: "/Users/digitalspace/.openclaw/workspace",
      script: "/usr/local/bin/python3",
      args: "alberth_qa_watcher.py",
      interpreter: "none",
      autorestart: true,
      watch: false
    }
  ]
};
