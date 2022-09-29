from __future__ import absolute_import
from dlt.dlt import DLTClient, DLT_RECEIVE_SOCKET, DLT_RETURN_OK, DLT_RETURN_ERROR, py_dlt_client_main_loop
from dlt.dlt_broker import DLTBroker
from dlt import dlt
import re
from datetime import datetime
import sys
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import ctypes
import time
import argparse
import logging
import socket
from dlt.core import (
    dltlib, DLT_ID_SIZE, DLT_HTYP_WEID, DLT_HTYP_WSID, DLT_HTYP_WTMS,
    DLT_HTYP_UEH, DLT_RETURN_OK, DLT_RETURN_ERROR, DLT_RETURN_TRUE, DLT_FILTER_MAX, DLT_MESSAGE_ERROR_OK,
    cDltExtendedHeader, cDltClient, MessageMode, cDLTMessage, cDltStorageHeader, cDltStandardHeader,
    DLT_TYPE_INFO_UINT, DLT_TYPE_INFO_SINT, DLT_TYPE_INFO_STRG, DLT_TYPE_INFO_SCOD,
    DLT_TYPE_INFO_TYLE, DLT_TYPE_INFO_VARI, DLT_TYPE_INFO_RAWD,
    DLT_SCOD_ASCII, DLT_SCOD_UTF8, DLT_TYLE_8BIT, DLT_TYLE_16BIT, DLT_TYLE_32BIT, DLT_TYLE_64BIT,
    DLT_TYLE_128BIT, DLT_DAEMON_TCP_PORT, DLT_CLIENT_RCVBUFSIZE,
    DLT_RECEIVE_SOCKET,
)
from dlt.helpers import bytes_to_str
logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

utime = 9999.99
stime = 9999.99
globaltime = 9999.99


# pylint: disable=too-many-arguments,too-many-return-statements,too-many-branches
def clientLoop(client, limit=None, verbose=0, dumpfile=None, callback=None):
    """Reimplementation of dlt_client.c:dlt_client_main_loop() in order to handle callback
    function return value"""
    bad_messages = 0
    f = open("rssESG.xlsx", 'a')
    global globaltime
    while True:
        if bad_messages > 100:
            # Some bad data is coming in and we can not recover - raise an error to cause a reconnect
            logger.warning("Dropping connection due to multiple malformed messages")
            return False
        # check connection status by peeking on the socket for data.
        # Note that if the remote connection is abruptly terminated,
        # this will raise a socket.timeout exception which the caller is
        # expected to handle (possibly by attempting a reconnect)
        # pylint: disable=protected-access
        if not client:
            try:
                ready_to_read = client._connected_socket.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT)
            except OSError as os_exc:
                logger.error("[%s]: DLTLib closed connected socket", os_exc)
                return False

            if not ready_to_read:
                # - implies that the other end has called close()/shutdown()
                # (ie: clean disconnect)
                logger.debug("connection terminated, returning")
                return False

        # - check if stop flag has been set (end of loop)
        if callback and not callback(None):
            logger.debug("callback returned 'False'. Stopping main loop")
            return False

        # we now have data to read. Note that dlt_receiver_receive()
        # is a blocking call that only returns if there is data to be
        # read or the remote end closes connection. So, irrespective of
        # the status of the callback (in the case of dlt_broker, this is
        # the stop_flag Event), this loop will only proceed after the
        # function has returned or terminate when an exception is raised
        recv_size = dltlib.dlt_receiver_receive(ctypes.byref(client.receiver), DLT_RECEIVE_SOCKET)
        if recv_size <= 0:
            logger.error("Error while reading from socket")
            return False

        msg = client.read_message(verbose)
        #print(msg)
        if msg is not None:
            msgSTR = str(msg)
            msgArr = msgSTR.split(' ')
            #print(msgArr[8] + " : " + msgArr[9])
            if msgArr[9] == "PROC" and msgArr[8] == "SYS":
                if msgArr[18] == "(node)" or msgArr[18] == ("(mco-audioApp)"):
                    # read the next message
                    msgArr[18] = re.sub(r'[()]', '', msgArr[18])
                    utime = float(msgArr[30])/100
                    stime = float(msgArr[31])/100
                    globaltime = float(msgArr[5])
                    msg = client.read_message()
                    print(msgArr[40])
                    with InfluxDBClient(url="http://localhost:8086", token=token, org=org) as Influxclient:
                        write_api = Influxclient.write_api(write_options=SYNCHRONOUS)
                        data = ""+msgArr[18]+",timestamp="+msgArr[5]+" RSS="+msgArr[40]+""
                        write_api.write(bucket, org, data)
                        if(utime!=9999.99 and stime!=9999.99 and globaltime!=9999.99):
                            print("time to send cpuload")
                            cpuload=(utime+stime)/globaltime
                            print(cpuload)
                            data = ""+str(msgArr[18])+",timestamp="+str(msgArr[5])+" cpu_load="+str(cpuload)+""
                            write_api.write(bucket, org, data)
        while msg:
            try:
                if msg.apid == b"" and msg.ctid == b"":
                    logger.debug("Received a corrupt message")
                    bad_messages += 1
            except AttributeError:
                logger.debug("Skipping a very corrupted message")
                bad_messages += 1
                msg = client.read_message()
                continue

            bad_messages = 0

            # remove message from receiver buffer
            size = msg.headersize + msg.datasize - ctypes.sizeof(cDltStorageHeader)
            if msg.found_serialheader:
                size += DLT_ID_SIZE

            if dltlib.dlt_receiver_remove(ctypes.byref(client.receiver), size) < 0:
                logger.error("dlt_receiver_remove failed")
                return False

            # send the message to the callback and check whether we
            # need to continue
            if callback and not callback(msg):
                logger.debug("callback returned 'False'. Stopping main loop")
                break

            if limit is not None:
                limit -= 1
                if limit == 0:
                    break

            # read the next message
            msg = client.read_message()
            
            #print(msg)
        else:
            # - failed to read a complete message, rewind the client
            # receiver buffer pointer to start of the buffer
            if dltlib.dlt_receiver_move_to_begin(ctypes.byref(client.receiver)) == DLT_RETURN_ERROR:
                logger.error("dlt_receiver_move_to_begin failed")
                return False

        # Check if we need to keep going
        if callback and not callback(msg):
            logger.debug("callback returned 'False'. Stopping main loop")
            break

    return True


# You can generate an API token from the "API Tokens Tab" in the UI
token = API_TOKEN_HERE
org = "VOGO"
bucket = "Vogo"

#Take first argument in the commandline as the IP of the DLT-Daemon to connect to
client = DLTClient(servIP=sys.argv[1], port=3490)

#Connect client so we can start received message in the socket.
client.connect()

clientLoop(client)

