FROM ubuntu:18.04

RUN apt-get update
RUN apt-get install -y tmux git python3.6 python3-pip
RUN apt-get install -y vim
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*
RUN git config --global user.email "you@example.com"
RUN git config --global user.name "Your Name"

WORKDIR /usr/local/lab-notebook
RUN pip3 install tabulate ipdb
COPY setup.py .
COPY README.rst .
COPY runs-git .
COPY runs runs/
RUN pip3 install -e .

#RUN echo 'alias t="python3 -m unittest runs/tests.py"' > /root/.bashrc
CMD ["nosetests", "-x"]
