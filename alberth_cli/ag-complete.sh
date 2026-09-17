# ag-complete.sh – Script de autocompletado para Zsh de agc (Alberth Dev Console)

_agc_completion() {
  local -a commands projects
  commands=(
    'open:Abrir proyecto en Antigravity IDE'
    'status:Ver estado git, branch y cambios'
    'git:Ejecutar comandos git en el proyecto'
    'run:Ejecutar scripts configurados'
    'list:Listar todos los proyectos de Novasyscom'
    'hud:Abrir Quantum HUD en Chrome'
    'help:Mostrar ayuda de comandos'
  )

  projects=(
    'drivo:Plataforma de Ride-Hailing P2P (Flutter)'
    'drivo-one:Delivery y Quick-Commerce Multitienda'
    'alberth:COO Digital & Asistente Personal de IA'
    'globalmarket:Portal Web Agroexportador B2B'
    'valex:Fintech de Cambio de Divisas USD-PEN'
  )

  if (( CURRENT == 2 )); then
    _describe -t commands 'comandos agc' commands
    _describe -t projects 'proyectos' projects
  elif (( CURRENT == 3 )); then
    local prev="${words[2]}"
    if [[ "$prev" =~ ^(open|status|git|run)$ ]]; then
      _describe -t projects 'proyectos' projects
    elif [[ "$prev" =~ ^(drivo|drivo-one|alberth|globalmarket|valex)$ ]]; then
      _describe -t commands 'comandos' commands
    fi
  fi
}

compdef _agc_completion agc 2>/dev/null || true
