# Linting

Please run the linter (ansible-lint) before you push commits, or your change may be rejected by CI.

## Install linter

On Ubuntu 24.04:

```
$ sudo apt update
$ sudo apt install pipx
$ pipx ensurepath
$ pipx install ansible-lint
```

## Run linter

```
$ ansible-lint
```
