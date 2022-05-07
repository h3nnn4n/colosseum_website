# Colosseum Website

The website for [Colosseum](https://colosseum.website), the automated AI
Tournament engine.  This project contains the user facing website, a public API
as well as the internal API used by the tournament engine.

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

- Install redis and postgres

- Setup postgres to connect with django. The easiest way to do this is to
  create a database named `postgres`, with a user named `postgres`, with
  `postgres` as the password. This is only safe for the local environment where
  no remote connections to the databased are allowed (this is the default
  behavior).
  - Open `psql` as the postgres user using `sudo -u postgres psql`
  - Create the database using `CREATE DATABASE postgres;`
  - Create the user using
  `CREATE USER postgres WITH ENCRYPTED PASSWORD 'mypass';`
  - Grant access to the new user to the newly created table
  `GRANT ALL PRIVILEGES ON DATABASE postgres TO postgres;`

# LICENSE

Released under the MIT license. See [LICENSE](LICENSE) for more details.
