python-dlt
==========

python-dlt is a thin Python ctypes wrapper around libdlt functions. It was
primarily created for use with BMW's test execution framework. However,
the implementation is independent and the API makes few assumptions about
the intended use.

The version is different form the master branch on the repository this has been forked from as we used the version in the ubuntu repository for Ubuntu 20.04. But even like that due to some compatibility problem we had to rewrite the socket connection part of dlt.py to remove the use of Ipv6 and replace the fromfd by a normal socket connection.


dltLogToInflux.py
=================

Our main function to connect to a dlt-daemon, get the infos from /proc/pid(node/mcoaudioapp)/stat and send them to an influxdb server.

Require one argument to launch which is the IP of the dlt-daemon of the target.

It also require to possibly modify the Org, Bucket and TokenAPI fields for the influxdb database.

It will connect to a dlt-daemon, find the trace we need, split them into an array and compare some values to be sure we got the right trace, if it is the case we will get the value we need, calculate a cpu-load and RSS and send them both to the influxDB.
