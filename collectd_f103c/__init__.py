import re
import collectd
import serial

# TODO make this configurable
TTY_PATH = "/dev/ttyUSB0"
EVAL = "value"

port = None


def config(conf):
    for kv in conf.children:
        if kv.key == "Device":
            global TTY_PATH
            TTY_PATH = kv.values[0]
        if kv.key == "Eval":
            global EVAL
            EVAL = kv.values[0]


def init():
    global port
    port = serial.Serial(TTY_PATH, 115200, timeout=0.1)
    collectd.info("Port open")


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


def read(data=None):
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
                values=(eval(EVAL, dict(value=m["raw"]))),
            )
            computed.dispatch()


collectd.register_config(config)
collectd.register_init(init)
collectd.register_read(read)
