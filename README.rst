python-dlt
==========

python-dlt is a thin Python ctypes wrapper around libdlt functions. It was
primarily created for use with BMW's test execution framework. However,
the implementation is independent and the API makes few assumptions about
the intended use.

The version is different form the master branch on the repository this has been forked from as we used the version in the ubuntu repository for Ubuntu 20.04. But even like that due to some compatibility problem we had to rewrite the socket connection part of dlt.py to remove the use of Ipv6 and replace the fromfd by a normal socket connection.

Note: Due to how python work when looking for a module to import it:
- Look in /usr/lib/python3/dist-packages/ for the package name and files
if the package doesn't exist in this folder, it will look in the folder where the python script has been called.
Which mean that it will find our dlt/ folder with the module inside and use it, which mean we don't have to actually install the library in the system as long as we accept that it will stay in the code folder (and that it will not be accessible by other python scripts outside).


dltLogToInflux.py
=================

Our main function to connect to a dlt-daemon, get the infos from /proc/pid(node/mcoaudioapp)/stat and send them to an influxdb server.

Require one argument to launch which is the IP of the dlt-daemon of the target.

It also require to possibly modify the Org, Bucket and TokenAPI fields for the influxdb database.

It will connect to a dlt-daemon, find the trace we need, split them into an array and compare some values to be sure we got the right trace, if it is the case we will get the value we need, calculate a cpu-load and RSS and send them both to the influxDB.


Docker-compose.yaml
===================

Once the python file is correct and manage to connect to the socket as wanted we now have to set up the services such as influxdb to store our data and possibly other service like Grafana for live monitoring.

Now, for user convenience and to not bother too much with settings such services and configuring them we have a docker-compose.yml file.
The goal of such file is to give rules about docker instances and services. This docker file will set every instances and services automatically for our use, with possible configuration (such as ports) that we can modify.

By using a command "sudo docker-compose up" we are able to start them all at once, with their configurations as declared in the yml file.

we can now access the influxdb CI with localhost:8086 or the grafana via localhost:3000
Once the CI access to Influxdb is possible we can also get the API token needed to connect it to our python script.
