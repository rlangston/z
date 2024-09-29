# z - the zettelkasten organiser

## Installation

To install via docker first clone the github repository.

'''

git clone https://github.com/rlangston/z.git

'''

Then initialise the database

'''

cd z/tools
python3 initdb.py

'''

The Dockerfile is as follows.  Set the environment variables for SECRET_KEY (the session secret key) and PASSWORD (the login password for the site)

'''

FROM python:3.12.6-slim-bookworm

ADD z z
WORKDIR z
ENV SECRET_KEY="your_secret_key"
ENV PASSWORD="your_password"
RUN pip3 install -r requirements.txt

CMD [ "python", "-m" , "flask", "run", "--host=0.0.0.0"]

'''

And the Docker Compose entry (which uses the above Dockerfile) is

'''

z:
  container_name: zettelkasten
  build:
    context: .
    dockerfile: Dockerfile-z
  restart: unless-stopped
  ports:
    - 8004:5000

'''

