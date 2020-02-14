import collectd
from threading import Thread

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
collectd.register_read(read, 0.5)
