import f103c
import os
from datetime import datetime

from influxdb_client import InfluxDBClient

influx_url = os.environ.get(
    "INFLUX_URL", "https://us-central1-1.gcp.cloud2.influxdata.com"
)
token = os.environ["INFLUX_TOKEN"]
bucket = os.environ["INFLUX_BUCKET"]
org = os.environ["INFLUX_ORG"]
host = os.environ["HOST"]

F103_DEVICE = "/usr/bin/ttyUSB0"

client = InfluxDBClient(url=influx_url, token=token)
wa = client.write_api()


def add_computed_kpa(measurement_series):
    for measurements in measurement_series:
        for m in measurements:
            m["kpa"] = 0.25 * m["raw"] - 128
        yield measurements


def main():
    reader = f103c.F103(F103_DEVICE)
    measurements_series = add_computed_kpa(reader.blocking_reader())

    for measurements in measurements_series:
        for measurement in measurements:
            if measurement["channel"] != 5:  # TODO deal with this
                continue
            now = datetime.utcnow()
            json_body = [
                {
                    "measurement": "water",
                    "tags": {"host": host, "sensor": "f103"},
                    "time": now,
                    "fields": {"pressure": measurement["kpa"]},
                }
            ]

            #    wa.write(json_body, dict(bucket=bucket))
            wa.write(bucket, org, record=json_body)
