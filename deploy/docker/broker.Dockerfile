# syntax=docker/dockerfile:1
FROM python-base:runtime

COPY --from=python-base:builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

USER jentic
ENV JENTIC__APPS=broker
CMD ["python", "-m", "jentic_one"]
