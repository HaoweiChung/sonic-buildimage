#
# Copyright (c) 2020-2021 NVIDIA CORPORATION & AFFILIATES.
# Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import time

from sonic_py_common.logger import Logger
from . import utils

logger = Logger()

class Led(object):
    STATUS_LED_COLOR_GREEN = 'green'
    STATUS_LED_COLOR_GREEN_BLINK = 'green_blink'
    STATUS_LED_COLOR_RED = 'red'
    STATUS_LED_COLOR_RED_BLINK = 'red_blink'
    STATUS_LED_COLOR_ORANGE = 'orange'
    STATUS_LED_COLOR_ORANGE_BLINK = 'orange_blink'
    STATUS_LED_COLOR_OFF = 'off'

    LED_ON = '255'
    LED_OFF = '0'
    LED_BLINK = '50'

    LED_PATH = "/var/run/hw-management/led/"

    def set_status(self, color):
        led_cap_list = self.get_capability()
        if led_cap_list is None:
            return False

        status = False
        try:
            self._stop_blink(led_cap_list)
            blink_pos = color.find('blink')
            if blink_pos != -1:
                return self._set_status_blink(color, led_cap_list)

            if color == Led.STATUS_LED_COLOR_GREEN:
                utils.write_file(self.get_green_led_path(), Led.LED_ON)
                status = True
            elif color == Led.STATUS_LED_COLOR_RED:
                # Some led don't support red led but support orange led, in this case we set led to orange
                if Led.STATUS_LED_COLOR_RED in led_cap_list:
                    led_path = self.get_red_led_path()
                elif Led.STATUS_LED_COLOR_ORANGE in led_cap_list:
                    led_path = self.get_orange_led_path()
                else:
                    return False

                utils.write_file(led_path, Led.LED_ON)
                status = True
            elif color == Led.STATUS_LED_COLOR_OFF:
                if Led.STATUS_LED_COLOR_GREEN in led_cap_list:
                    utils.write_file(self.get_green_led_path(), Led.LED_OFF)
                if Led.STATUS_LED_COLOR_RED in led_cap_list:
                    utils.write_file(self.get_red_led_path(), Led.LED_OFF)
                if Led.STATUS_LED_COLOR_ORANGE in led_cap_list:
                    utils.write_file(self.get_orange_led_path(), Led.LED_OFF)

                status = True
            else:
                status = False
        except (ValueError, IOError):
            status = False

        return status

    def _set_status_blink(self, color, led_cap_list):
        if color not in led_cap_list:
            if color == Led.STATUS_LED_COLOR_RED_BLINK and Led.STATUS_LED_COLOR_ORANGE_BLINK in led_cap_list:
                color = Led.STATUS_LED_COLOR_ORANGE_BLINK
            elif color == Led.STATUS_LED_COLOR_ORANGE_BLINK and Led.STATUS_LED_COLOR_RED_BLINK in led_cap_list:
                color = Led.STATUS_LED_COLOR_RED_BLINK
            else:
                return False

        if Led.STATUS_LED_COLOR_GREEN_BLINK == color:
            self._trigger_blink(self.get_green_led_trigger())
            return self._set_led_blink_status(self.get_green_led_delay_on_path(), self.get_green_led_delay_off_path(), Led.LED_BLINK)
        elif Led.STATUS_LED_COLOR_RED_BLINK == color:
            self._trigger_blink(self.get_red_led_trigger())
            return self._set_led_blink_status(self.get_red_led_delay_on_path(), self.get_red_led_delay_off_path(), Led.LED_BLINK)
        elif Led.STATUS_LED_COLOR_ORANGE_BLINK == color:
            self._trigger_blink(self.get_orange_led_trigger())
            return self._set_led_blink_status(self.get_orange_led_delay_on_path(), self.get_orange_led_delay_off_path(), Led.LED_BLINK)
        else:
            return False

    def _stop_blink(self, led_cap_list):
        try:
            if Led.STATUS_LED_COLOR_GREEN_BLINK in led_cap_list:
                self._untrigger_blink(self.get_green_led_trigger())
            if Led.STATUS_LED_COLOR_RED_BLINK in led_cap_list:
                self._untrigger_blink(self.get_red_led_trigger())
            if Led.STATUS_LED_COLOR_ORANGE_BLINK in led_cap_list:
                self._untrigger_blink(self.get_orange_led_trigger())
        except Exception as e:
            return

    def _trigger_blink(self, blink_trigger_file):
        utils.write_file(blink_trigger_file, 'timer')

    def _untrigger_blink(self, blink_trigger_file):
        utils.write_file(blink_trigger_file, 'none')

    def _set_led_blink_status(self, delay_on_file, delay_off_file, value):
        if not self._wait_files_ready((delay_on_file, delay_off_file)):
            return False

        utils.write_file(delay_on_file, value)
        utils.write_file(delay_off_file, value)
        return True

    def _wait_files_ready(self, file_list):
        """delay_off and delay_on sysfs will be available only if _trigger_blink is called. And once
           _trigger_blink is called, driver might need time to prepare delay_off and delay_on. So,
           need wait a few seconds here to make sure the sysfs is ready

        Args:
            file_list (list of str): files to be checked
        """
        wait_time = 5.0
        initial_sleep = 0.01
        while wait_time > 0:
            if all([os.path.exists(x) for x in file_list]):
                return True
            time.sleep(initial_sleep)
            wait_time -= initial_sleep
            initial_sleep = initial_sleep * 2

        return False

    def get_status(self):
        led_cap_list = self.get_capability()
        if led_cap_list is None:
            return Led.STATUS_LED_COLOR_OFF

        try:
            blink_status = self._get_blink_status(led_cap_list)
            if blink_status is not None:
                return blink_status

            if utils.read_str_from_file(self.get_green_led_path()) != Led.LED_OFF:
                return Led.STATUS_LED_COLOR_GREEN

            if Led.STATUS_LED_COLOR_RED in led_cap_list:
                if utils.read_str_from_file(self.get_red_led_path()) != Led.LED_OFF:
                    return Led.STATUS_LED_COLOR_RED
            if Led.STATUS_LED_COLOR_ORANGE in led_cap_list:
                if utils.read_str_from_file(self.get_orange_led_path()) != Led.LED_OFF:
                    return Led.STATUS_LED_COLOR_RED
        except (ValueError, IOError) as e:
            raise RuntimeError("Failed to read led status due to {}".format(repr(e)))

        return Led.STATUS_LED_COLOR_OFF

    def _get_blink_status(self, led_cap_list):
        try:
            if Led.STATUS_LED_COLOR_GREEN_BLINK in led_cap_list:
                if self._is_led_blinking(self.get_green_led_delay_on_path(), self.get_green_led_delay_off_path()):
                    return Led.STATUS_LED_COLOR_GREEN_BLINK

            if Led.STATUS_LED_COLOR_RED_BLINK in led_cap_list:
                if self._is_led_blinking(self.get_red_led_delay_on_path(), self.get_red_led_delay_off_path()):
                    return Led.STATUS_LED_COLOR_RED_BLINK
            if Led.STATUS_LED_COLOR_ORANGE_BLINK in led_cap_list:
                if self._is_led_blinking(self.get_orange_led_delay_on_path(), self.get_orange_led_delay_off_path()):
                    return Led.STATUS_LED_COLOR_ORANGE_BLINK
        except Exception as e:
            return None

        return None

    def _is_led_blinking(self, delay_on_file, delay_off_file):
        delay_on = utils.read_str_from_file(delay_on_file, default=Led.LED_OFF, log_func=None)
        delay_off = utils.read_str_from_file(delay_off_file, default=Led.LED_OFF, log_func=None)
        return delay_on != Led.LED_OFF and delay_off != Led.LED_OFF

    def get_capability(self):
        caps = utils.read_str_from_file(self.get_led_cap_path())
        return set(caps.split())

    def get_green_led_path(self):
        return os.path.join(Led.LED_PATH, 'led_{}_green'.format(self._led_id))

    def get_green_led_delay_off_path(self):
        return os.path.join(Led.LED_PATH, 'led_{}_green_delay_off'.format(self._led_id))

    def get_green_led_delay_on_path(self):
        return os.path.join(Led.LED_PATH, 'led_{}_green_delay_on'.format(self._led_id))

    def get_green_led_trigger(self):
        return os.path.join(Led.LED_PATH, 'led_{}_green_trigger'.format(self._led_id))

    def get_red_led_path(self):
        return os.path.join(Led.LED_PATH, 'led_{}_red'.format(self._led_id))

    def get_red_led_delay_off_path(self):
        return os.path.join(Led.LED_PATH, 'led_{}_red_delay_off'.format(self._led_id))

    def get_red_led_delay_on_path(self):
        return os.path.join(Led.LED_PATH, 'led_{}_red_delay_on'.format(self._led_id))

    def get_red_led_trigger(self):
        return os.path.join(Led.LED_PATH, 'led_{}_red_trigger'.format(self._led_id))

    def get_orange_led_path(self):
        return os.path.join(Led.LED_PATH, 'led_{}_orange'.format(self._led_id))

    def get_orange_led_delay_off_path(self):
        return os.path.join(Led.LED_PATH, 'led_{}_orange_delay_off'.format(self._led_id))

    def get_orange_led_delay_on_path(self):
        return os.path.join(Led.LED_PATH, 'led_{}_orange_delay_on'.format(self._led_id))

    def get_orange_led_trigger(self):
        return os.path.join(Led.LED_PATH, 'led_{}_orange_trigger'.format(self._led_id))

    def get_led_cap_path(self):
        return os.path.join(Led.LED_PATH, 'led_{}_capability'.format(self._led_id))


class FanLed(Led):
    def __init__(self, index):
        if index is not None:
            self._led_id = 'fan{}'.format(index)
        else:
            self._led_id = 'fan'


class PsuLed(Led):
    def __init__(self, index):
        if index is not None:
            self._led_id = 'psu{}'.format(index)
        else:
            self._led_id = 'psu'


class SystemLed(Led):
    def __init__(self):
        self._led_id = 'status'


class SharedLed(object):
    LED_PRIORITY = {
        Led.STATUS_LED_COLOR_RED: 0,
        Led.STATUS_LED_COLOR_GREEN: 1
    }

    def __init__(self, led):
        self._led = led
        self._virtual_leds = []

    def add_virtual_leds(self, led):
        self._virtual_leds.append(led)

    def update_status_led(self):
        target_color = Led.STATUS_LED_COLOR_GREEN
        for virtual_led in self._virtual_leds:
            try:
                if SharedLed.LED_PRIORITY[virtual_led.get_led_color()] < SharedLed.LED_PRIORITY[target_color]:
                    target_color = virtual_led.get_led_color()
            except KeyError:
                return False
        return self._led.set_status(target_color)

    def get_status(self):
        return self._led.get_status()


class ComponentFaultyIndicator(object):
    def __init__(self, shared_led):
        self._color = Led.STATUS_LED_COLOR_GREEN
        self._shared_led = shared_led
        self._shared_led.add_virtual_leds(self)

    def set_status(self, color):
        current_color = self._color
        self._color = color
        if self._shared_led.update_status_led():
            return True
        else:
            self._color = current_color
            return False

    def get_led_color(self):
        return self._color

    def get_status(self):
        return self._shared_led.get_status()
