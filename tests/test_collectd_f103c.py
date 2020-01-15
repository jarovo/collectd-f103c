from textwrap import dedent
import sys
from unittest.mock import Mock, call
import pytest


def mock_collectd_module():
    sys.modules["collectd"] = Mock()


mock_collectd_module()


import collectd_f103c  # noqa: E402
import collectd  # noqa: E402


@pytest.fixture
def collectd_module_mock():
    assert isinstance(collectd, Mock)
    collectd.reset_mock()
    return collectd


@pytest.fixture
def port_mock(mocker):
    return mocker.patch("collectd_f103c.port")


def test_broken_frame(port_mock, collectd_module_mock):
    data = dedent(
        """\
        CH0:2883	2.322V\r
        CH1:2327	1.875V\r
        CH2:2082	1.677V\r
        CH3:1970	1.58CH0:2884	2.323V\r
        CH1:2329	1.876V\r
        CH2:2082	1.678V\r
        CH3:1968	1.584V\r
        CH4:2158	1.738V\r
        CH5:2005	1.616V\r
        CH6:2175	1.751V\r
        CH7:2007	1.616V\r
        CH8:2179	1.754V\r
        CH9:4092	3.296V\r
        \r
        CH0:2888	2.325V\r
        CH1:2331	1.876V\r
        CH2:2084	1.679V\r
        CH3:1968	1.585V\r
        CH4:2161	1.740V\r
        CH5:2007	1.616V\r
        CH6:2178	1.753V\r
        CH7:2008	1.618V\r
        CH8:2181	1.757V\r
        CH9:4092	3.297V\r
    """
    )
    frames = [f.encode() for f in data.split("\r\n\r\n")]
    port_mock.read_until.side_effect = frames
    with pytest.raises(StopIteration):
        collectd_f103c.read()
    for c in (
        call.Values(
            plugin="python.f103c.voltages.0", type="gauge", values=(2.322,)
        ),
        call.Values(
            plugin="python.f103c.voltages.2", type="gauge", values=(1.677,)
        ),
    ):
        assert c not in collectd_module_mock.mock_calls
    collectd_module_mock.assert_has_calls(
        (
            call.Values(
                plugin="python.f103c.voltages.0", type="gauge", values=(2.325,)
            ),
            call.Values().dispatch(),
            call.Values(
                plugin="python.f103c.raw.0", type="gauge", values=(2888,)
            ),
            call.Values().dispatch(),
            call.Values(
                plugin="python.f103c.computed.0", type="gauge", values=2888
            ),
            call.Values().dispatch(),
        )
    )
    collectd_module_mock.assert_has_calls(
        (
            call.Values(
                plugin="python.f103c.voltages.9", type="gauge", values=(3.297,)
            ),
            call.Values().dispatch(),
            call.Values(
                plugin="python.f103c.raw.9", type="gauge", values=(4092,)
            ),
            call.Values().dispatch(),
            call.Values(
                plugin="python.f103c.computed.9", type="gauge", values=4092
            ),
            call.Values().dispatch(),
        )
    )
