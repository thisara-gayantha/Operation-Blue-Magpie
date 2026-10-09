FROM ctfd/ctfd:3.8.7

USER root
RUN /opt/venv/bin/python -m pip install --no-cache-dir psycopg2-binary
COPY plugins/operation_blue_magpie /opt/CTFd/CTFd/plugins/operation_blue_magpie
RUN chown -R ctfd:ctfd /opt/CTFd/CTFd/plugins/operation_blue_magpie
USER ctfd
