# z - the zettelkasten organiser

## Installation

To install via docker first clone the github repository.

```

git clone https://github.com/rlangston/z.git

```

Then initialise the database

```

cd z/tools
python3 initdb.py

```

The Dockerfile is as follows.  Set the environment variables for SECRET_KEY (the session secret key), PASSWORD (the login password for the site) and DATABASE (the url for the database which is mapped from the local drive to this location by Docker Compose).

```

FROM python:3.12.6-slim-bookworm

ADD z z
WORKDIR z
ENV SECRET_KEY="your_secret_key"
ENV PASSWORD="your_password"
ENV DATABASE_RL="sqlite////db/z.db"
RUN pip3 install -r requirements.txt

CMD [ "python", "-m" , "flask", "run", "--host=0.0.0.0"]

```

And the Docker Compose entry (which uses the above Dockerfile) is (change hte ./zdb to the location of the folder containing the database on the local drive - this will persist a rebuild of the docker file).

```

z:
  container_name: zettelkasten
  build:
    context: .
    dockerfile: Dockerfile-z
  restart: unless-stopped
  ports:
    - 8004:5000
  volumes:
    - ./zdb:/zb

```

## Usage

### Tags and search
The /index page can loaded with url params q and tags to search for text and tags respectively.  For example /index?q=hello&tags=world would list all items which include the text hello and the tag world.

Click on the hamburger to get a list of the tags, and their count.  These are then populated into the tags box and the page reloaded.  Alternatively type in the box and then press return to reload the page.  Clearing the box and pressing return reloads the page and clears the tag search.

To find items with no tag, either select the "No tag" option in the list of tags, or type <none> in the tags box.s
