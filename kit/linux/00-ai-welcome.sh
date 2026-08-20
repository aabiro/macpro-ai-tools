# Beginner's nudge on interactive login. Asks the gateway whether any provider
# key is loaded -- it must NOT read /etc/ai-cockpit/env, which is root-only, and
# must NOT call sudo, or every login would prompt for a password after handover.
case $- in *i*) ;; *) return ;; esac
[ -n "${AI_WELCOME_SHOWN:-}" ] && return
export AI_WELCOME_SHOWN=1
_ai_ready=$(timeout 2 curl -fsS http://127.0.0.1:8081/health 2>/dev/null \
            | grep -o '"providers_configured": *\[[^]]*\]' | grep -o '"[a-z]*"' | head -1)
if [ -z "$_ai_ready" ]; then
    printf '\n\033[1m  Welcome. This machine has AI tools installed, but no key yet.\033[0m\n'
    printf '  Type \033[36mai setup\033[0m and press Enter to switch them on (about two minutes).\n'
    printf '  Type \033[36mai help\033[0m for everything else.\n\n'
else
    printf '\n  AI is ready. \033[36mai chat\033[0m to talk to it, \033[36mai help\033[0m for the list.\n\n'
fi
unset _ai_ready
