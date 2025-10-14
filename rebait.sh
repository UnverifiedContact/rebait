rebait() {
    source "$HOME/personal_scripts/rebait/.env"
    "$HOME/personal_scripts/rebait/venv/bin/python" \
        "$HOME/personal_scripts/rebait/rebait.py" "$@"
}
alias rb="rebait"