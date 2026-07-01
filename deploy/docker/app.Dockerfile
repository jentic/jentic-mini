# syntax=docker/dockerfile:1
FROM python-base:runtime

COPY --from=python-base:builder /build/dist/*.whl /tmp/
RUN whl="$(ls /tmp/jentic_one-*.whl)" && \
    pip install --no-cache-dir "${whl}" && \
    rm /tmp/*.whl

# Writable data dir for the SQLite backend. Pre-creating it owned by the runtime
# user means a fresh Docker volume mounted here inherits jentic ownership, so the
# non-root process can create database files (a root-owned volume cannot).
RUN mkdir -p /data && chown jentic:jentic /data

USER jentic
ENV JENTIC__APPS=registry,admin,control,auth
CMD ["python", "-m", "jentic_one"]
