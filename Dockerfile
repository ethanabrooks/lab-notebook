# A Dockerfile that sets up a full Gym install
FROM ubuntu:16.04

RUN apt-get update --fix-missing
RUN apt-get install -y tmux git python3 python3-pip
    #&& apt-get clean \
    #&& rm -rf /var/lib/apt/lists/* \
    #&& easy_install pip

WORKDIR /usr/local/run_manager
#RUN mkdir -p gym && touch gym/__init__.py
COPY runs.py .
COPY setup.py .
RUN pip3 install -e .

WORKDIR /root
#ENTRYPOINT ["/usr/local/gym/bin/docker_entrypoint"]
