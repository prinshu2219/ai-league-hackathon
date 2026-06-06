import unittest

from osft_lab.device import describe_device, select_best_device


class _FakeCuda:
    def __init__(self, available):
        self._available = available

    def is_available(self):
        return self._available

    def get_device_name(self, index):
        return f"Fake CUDA:{index}"


class _FakeMps:
    def __init__(self, available):
        self._available = available

    def is_available(self):
        return self._available


class _FakeBackends:
    def __init__(self, mps_available):
        self.mps = _FakeMps(mps_available)


class _FakeTorch:
    def __init__(self, cuda_available=False, mps_available=False):
        self.cuda = _FakeCuda(cuda_available)
        self.backends = _FakeBackends(mps_available)


class DeviceTests(unittest.TestCase):
    def test_select_best_device_prefers_cuda(self):
        torch_module = _FakeTorch(cuda_available=True, mps_available=True)

        self.assertEqual(select_best_device(torch_module=torch_module), "cuda")

    def test_select_best_device_uses_mps_when_cuda_missing(self):
        torch_module = _FakeTorch(cuda_available=False, mps_available=True)

        self.assertEqual(select_best_device(torch_module=torch_module), "mps")

    def test_select_best_device_falls_back_to_cpu(self):
        torch_module = _FakeTorch(cuda_available=False, mps_available=False)

        self.assertEqual(select_best_device(torch_module=torch_module), "cpu")

    def test_describe_device_returns_interview_friendly_details(self):
        torch_module = _FakeTorch(cuda_available=True, mps_available=False)

        details = describe_device(torch_module=torch_module)

        self.assertEqual(details["selected_device"], "cuda")
        self.assertTrue(details["cuda_available"])
        self.assertFalse(details["mps_available"])
        self.assertEqual(details["cuda_name"], "Fake CUDA:0")


if __name__ == "__main__":
    unittest.main()
