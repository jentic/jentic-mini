# syntax=docker/dockerfile:1
FROM python-base:runtime

COPY --from=python-base:builder /build/dist/*.whl /tmp/
RUN whl="$(ls /tmp/jentic_one-*.whl)" && \
    pip install --no-cache-dir "${whl}" && \
    rm /tmp/*.whl

USER jentic
ENV JENTIC__APPS=registry
CMD ["python", "-m", "jentic_one"]
