# Colosseum Website

The website for [Colosseum](https://colosseum.website), the automated AI Tournament engine.

# Local setup

- Get the source code from [github](https://github.com/h3nnn4n/colosseum_website)

- Install [`pyenv`](https://github.com/pyenv/pyenv):
  - The recommended way is listed here: https://github.com/pyenv/pyenv#basic-github-checkout
  - If you know what you are doing feel free to use another way

- Install the current python version. Note that this command should be run from inside the git repository.
```
pyenv install `cat .python-version`
```

- Ensure that pip is available:
```
python -m ensurepip
```

- Install poetry
```
python -m pip install poetry
```

- Install the package dependencies
```
poetry install
```

- Rehash python commands
```
pyenv rehash
```

- Install the git hooks
```
pre-commit install -t pre-commit -t pre-push
```

# LICENSE

Released under the MIT license. See [LICENSE](LICENSE) for more details.
