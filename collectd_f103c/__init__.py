import re
import collectd
import serial
from threading import Thread

# TODO make this configurable
TTY_PATH = "/dev/ttyUSB0"
EVAL = "value"

port = None
comp_emas = None
alpha = None
DEFAULT_ALPHA = 0.3


def config(conf):
    for kv in conf.children:
        if kv.key == "Device":
            global TTY_PATH
            TTY_PATH = kv.values[0]
        if kv.key == "Eval":
            global EVAL
            EVAL = kv.values[0]
        if kv.key == "alpha":
            global alpha
            alpha = kv.values[0]


def init():
    global port, comp_emas
    port = serial.Serial(TTY_PATH, 115200, timeout=0.1)
    collectd.info("Port open")
    comp_emas = [ema(alpha or DEFAULT_ALPHA, 0) for i in range(10)]


def fix_types(groups):
    groups["channel"] = int(groups["channel"])
    groups["voltage"] = float(groups["voltage"])
    groups["raw"] = int(groups["raw"])
    return groups


def read_frame(port):
    data = port.read_until(b"\r\n\r\n")
    data = data.decode("ascii").strip()
    return data


def to_measurements(data):
    measurements = [None for _ in range(10)]
    for line in data.split("\r\n"):
        pattern = r"CH(?P<channel>.):(?P<raw>\d+)\t(?P<voltage>[.\d]+)V"
        m = re.match(pattern, line)
        if not m:
            break
        g = fix_types(m.groupdict())
        measurements[g["channel"]] = g
    return measurements


def serial_reader():
    while True:
        frame = read_frame(port)
        if not frame:
            collectd.error(
                "Timeouted when waiting for data."
            )  # TODO improve message
            break
        measurements = to_measurements(frame)
        if not all(measurements):
            collectd.info("Incomplete read, repeating. ({})".format(frame))
            continue
        yield measurements


def ema(alpha, initial=0.0):
    previous = initial
    while True:
        current = yield previous
        if current:
            previous = alpha * current + (1.0 - alpha) * previous


def add_computed(expression, measurements_series):
    for measurements in measurements_series:
        for m in measurements:
            m["computed"] = eval(expression, dict(value=m["raw"]))[
                0
            ]  # Todo remove the subscription
        yield measurements


def smoothing(measurement_series, comp_emas):
    init = next(measurement_series)  # TODO
    for ce in comp_emas:
        next(ce)
    for measurements in measurement_series:
        for m in measurements:
            m["computed_smoothed"] = comp_emas[m["channel"]].send(
                m["computed"]
            )
        yield measurements


def dispatch(measurement_series):
    for measurements in measurement_series:
        for m in measurements:
            collectd.Values(
                type="voltage",
                plugin="python.f103c",
                plugin_instance=str(TTY_PATH),
                type_instance="{}".format(m["channel"]),
                values=(m["voltage"],),
            ).dispatch()
            collectd.Values(
                type="f103c",
                plugin="python.f103c",
                plugin_instance=str(TTY_PATH),
                type_instance="{}".format(m["channel"]),
                values=(m["raw"], m["computed"], m["computed_smoothed"]),
            ).dispatch()
            continue
            collectd.Values(
                type="gauge",
                plugin="python.f103c",
                plugin_instance=str(TTY_PATH),
                type_instance="{}.computed_smoothed".format(m["channel"]),
                values=(m["computed_smoothed"],),
            ).dispatch()
            collectd.Values(
                type="gauge",
                plugin="python.f103c",
                plugin_instance=str(TTY_PATH),
                type_instance="{}.computed".format(m["channel"]),
                values=(m["computed"],),
            ).dispatch()
        yield measurements


class ReaderThread(Thread):
    def run(self):
        for measurements in dispatch(smooth(add_computed(serial_reader()))):
            pass


def read():
    for measurements in dispatch(
        smoothing(add_computed(EVAL, serial_reader()), comp_emas)
    ):
        pass


def legacy_read():
    collectd.info("Reading serial port {}.".format(port))
    while True:
        frame = read_frame(port)
        measurements = to_measurements(frame)
        if not any(measurements):
            collectd.info("Timeout ({})".format(frame))
            break
        if not all(measurements):
            collectd.info("Incomplete read, repeating. ({})".format(frame))
            continue

        for ch, m in enumerate(measurements):
            if not m:
                continue
            voltage = collectd.Values(
                type="gauge",
                plugin="python.f103c.voltages.{}".format(ch),
                values=(m["voltage"],),
            )
            voltage.dispatch()

            raw = collectd.Values(
                type="gauge",
                plugin="python.f103c.raw.{}".format(ch),
                values=(m["raw"],),
            )
            raw.dispatch()

            computed = collectd.Values(
                type="gauge",
                plugin="python.f103c.computed.{}".format(ch),
                values=(),
            )
            computed.dispatch()


collectd.register_config(config)
collectd.register_init(init)
collectd.register_read(read)
