#!/bin/zsh
#
# Useful zsh functions for Python virtual environments using vex
#

export WORKON_HOME=$VIRTUAL_ENV_ROOT

function workon {
    vex "$@"
}

function mkv {
    venv="$VIRTUAL_ENV_ROOT/$1"
    if [ ! -d "$venv" ]; then
        virtualenv "$venv" 
    else
        echo "Virtualenv '$1' already exists."
        return 1
    fi 
}

function lsvr {
    ls "$VIRTUAL_ENV_ROOT"
}

function cdvr {
    cd "$VIRTUAL_ENV_ROOT"
}

function cdpr {
    cd "$PROJECT_ROOT"
}

function _create_project {
    cd "$PROJECT_ROOT"
    if [ -n "$2" ]; then
        git clone "$2" "$1"
    else
        mkdir "$1"
    fi
    cd - >/dev/null
}

function mkp {
    venv_dotproject="$VIRTUAL_ENV_ROOT/$1/.project" 
    venv_project="$PROJECT_ROOT/$1"
    if [ ! -d "$venv_project" ]; then
        mkv "$@" && echo "$venv_project" > "$venv_dotproject" && _create_project "$@"    
    else
        echo "Project '$1' already exists."
        return 1
    fi
}

if [ -n "$VIRTUAL_ENV" ]; then 
    export VIRTUAL_ENV_NAME="${VIRTUAL_ENV##*/}"

    function cdv {
        cd "$VIRTUAL_ENV" 
    }

    function _get_venv_site_packages {
        "$VIRTUAL_ENV/bin/python" -c "import distutils; print(distutils.sysconfig.get_python_lib())"
    }

    export VENV_SITE_PACKAGES="$(_get_venv_site_packages)"

    function cdsp {
        cd "$VENV_SITE_PACKAGES"
    }

    function cdp {
        if [ "$1" = "-q" ]; then
            quiet=True
        fi

        venv_dotproject="$VIRTUAL_ENV/.project"
        if [ -f "$venv_dotproject" ]; then
            venv_project=`cat "$venv_dotproject"` 
            if [ -d "$venv_project" ]; then
                export VIRTUAL_ENV_PROJECT="$venv_project"
                cd "$venv_project"
            elif [ -n "$quiet" ]; then
                return 0
            else
                echo "Project directory '$venv_project' is missing."
                return 1
            fi
        elif [ -n "$quiet" ]; then
            return 0
        else
            echo "No project defined for virtualenv '$VIRTUAL_ENV_NAME'."
            return 1
        fi 
    }

    export PS1="
($VIRTUAL_ENV_NAME)$PS1"

    #
    # Change into project directory
    #
    cdp -q

    #
    # Run postactivate scripts
    #
    GLOBAL_POSTACTIVATE="$VIRTUAL_ENV_ROOT/postactivate" 
    if [ -f "$GLOBAL_POSTACTIVATE" ]; then
        source "$GLOBAL_POSTACTIVATE"
    fi

    VENV_POSTACTIVATE="$VIRTUAL_ENV/bin/postactivate"
    if [ -f "$VENV_POSTACTIVATE" ]; then
        source "$VENV_POSTACTIVATE"
    fi

else
    if which pyenv > /dev/null; then eval "$(pyenv init -)"; fi

    function rmv {
        venv="$VIRTUAL_ENV_ROOT/$1"
        if [ -d "$venv" ]; then
            rm -rf "$venv"
        else
            echo "Virtualenv '$1' doesn't exist."
            return 1
        fi
    }
fi

# Configure ZSH completion
autoload compinit; compinit
function _virtualenvs {
    reply=( $(cd $VIRTUAL_ENV_ROOT && ls) )
}
function _cdv_complete {
    reply=( $(cdv && ls -d ${1}*) )
}
function _cdsp_complete {
    reply=( $(cdsp && ls -d ${1}*) )
}
compctl -K _virtualenvs workon rmv 
compctl -K _cdv_complete cdv
compctl -K _cdsp_complete cdsp
