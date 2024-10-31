# Copyright Tomer Figenblat.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Switcher integration helper functions."""

from asyncio import StreamReader, StreamWriter
from binascii import unhexlify
from logging import getLogger

from ..device.tools import set_message_length, sign_packet_with_crc_key

logger = getLogger(__name__)


async def send_packet(
    writer: StreamWriter, reader: StreamReader, packet_id: str, packet: str
) -> bytes:
    """Sign and send a packet, then read the response.

    Args:
        writer (StreamWriter): The writer to send the packet.
        reader (StreamReader): The reader to receive the response.
        packet_id (str): The identifier for the packet being sent.
        packet (str): The packet to be sent.

    Returns:
        bytes: The response from the device.
    """
    packet = set_message_length(packet)
    signed_packet = sign_packet_with_crc_key(packet)

    logger.debug(f"sending a {packet_id} packet")
    writer.write(unhexlify(signed_packet))
    response = await reader.read(1024)
    return response
