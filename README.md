[![Lint Check](https://github.com/feo-cz/docker-systemctl-replacement/actions/workflows/lintcheck.yml/badge.svg?event=push&branch=master)](https://github.com/feo-cz/docker-systemctl-replacement/actions/workflows/lintcheck.yml)
[![Type Check](https://github.com/feo-cz/docker-systemctl-replacement/actions/workflows/typecheck.yml/badge.svg?event=push&branch=master)](https://github.com/feo-cz/docker-systemctl-replacement/actions/workflows/typecheck.yml)
[![Unit Tests](https://github.com/feo-cz/docker-systemctl-replacement/actions/workflows/unittests.yml/badge.svg?event=push&branch=master)](https://github.com/feo-cz/docker-systemctl-replacement/actions/workflows/unittests.yml)
[![PyPI version](https://badge.fury.io/py/docker-systemctl-replacement.svg)](https://pypi.org/project/docker-systemctl-replacement/)

# This fork

A fork of [gdraheim/docker-systemctl-replacement](https://github.com/gdraheim/docker-systemctl-replacement),
rebased onto upstream v1.7.1311. Everything below this section is the
upstream README and describes the upstream project.

The work here sits on its own topic branches so that any of it can be
taken one piece at a time; `master` is their merge. Each branch carries a
test that fails without it. Numbers below are measured, not estimated.

**Answers that were wrong**

* an unreadable `PIDFile=` no longer makes the state `unknown` - an
  unprivileged caller gets the same answer as root. An *absent* PIDFile
  still means `inactive`: the application has spoken and that is complete
* a template instance gets its own conf instead of sharing the template's,
  so every instance but the last stopped losing its recorded state
* an enabled instance link is read as an instance, not as an alias
* `enable --now` and `disable --now` report a start or stop that failed
  instead of returning success
* a clean shutdown of the init loop exits 0, not 1
* `systemctl show -p path` on a unit with no file reports an empty path

**Shutdown and signals**

* `KillMode=` decides who is signalled *and* who is waited for. Waiting on
  processes it never touched made every stop of an `ssh`, `cron` or
  `puppet` unit burn its whole `TimeoutStopSec`: measured 30.9s -> 1.0s
* a shutdown request can end the init loop. It used to switch to waiting
  for the machine to run out of processes, which a container running
  journald or holding one login shell never does - the units went down,
  PID 1 stayed up and the restart policy never fired
* the signal handlers go up before the units are started, not after. As
  PID 1 that is not a late handler but no handler at all: measured on a
  container, an 8.75s window in which eight SIGTERMs vanished without a
  trace. Now zero
* a fork child leaves by `os._exit` and cannot unwind into the manager's
  frames, whatever happens - including an exception before the exec
* an `ExecStop=` that hangs no longer holds the stop open: 32.7s against
  `TimeoutStopSec=2`, now 4.0s, and the service is actually gone
* `/sbin/{reboot,halt,poweroff,shutdown,telinit}` dispatch on `argv[0]`
  the way systemd does. Typing `reboot` used to print a unit listing and
  return success. `reboot` and `poweroff` exist as commands now

**Files, permissions and noise**

* our runtime files do not depend on the caller's umask, and the five
  `*DirectoryMode=` settings default to 0755 as `systemd.exec(5)` says
* a `PIDFile=` we may not stat is the normal case for an unprivileged
  caller, not a warning on every query
* `journalctl` for a unit that logged nothing answers `-- No entries --`
  with exit 0, matching the real journalctl byte for byte, instead of
  failing and burying the error it was being asked to fetch
* the `mount*` ignore pattern, lost upstream in `0b02699b` when the ignore
  lists were rewritten

**Additions**

* `PermissionsStartOnly=` and the `+` prefix on `Exec*` lines
* `[get|set|unset]-environment`
* `journalctl --since` accepted and ignored, the way deployment tooling
  passes it
* `list-unit-files` honours its state filter, its mask filter and every
  PATTERN given
* `unmask` keeps a unit file that is a symlink to something other than
  `/dev/null`
* service aliases resolved consistently

**Checks**

`make lint`, `make testlocal` and `make type` are green here - see the
badges above. `make testlocal` is `tests/functests.py`: 129 in-process
tests in about five seconds, 73 of them added by this fork.

`make exectests` is the heavy one - 371 subprocess tests, no docker
needed, around half an hour. The wide check used while this work was
done covers 254 of those (`test_1*`, `test_2*`, `test_3*`) and reports
no failures. `tests/docktests.py` and `tests/buildtests.py` need docker
and have not been run here.

# docker systemctl replacement

This script may be used to overwrite "/usr/bin/systemctl".
It will execute the systemctl commands without SystemD!

This is used to test deployment of services with a docker
container as the target host. Just as on a real machine you 
can use "systemctl start" and "systemctl enable" and other 
commands to bring up services for further configuration and 
testing. Information from "systemctl show" allows deployment
automation tools to work seamlessly.

This script can also be run as docker-init of a docker container
(i.e. the main "CMD" on PID 1) where it will automatically bring 
up all enabled services in the "multi-user.target" and where it 
will reap all zombies from background processes in the container.
When running a "docker stop" on such a container it will also 
bring down all configured services correctly before exit.

    ## docker exec lamp-stack-container systemctl list-units --state=running
    httpd.service     loaded active running   The Apache HTTP Server
    mariadb.service   loaded active running   MariaDB database server
    
    ## docker exec lamp-stack-container pstree -ap
    systemctl,1 /usr/bin/systemctl
      |-httpd,7 -DFOREGROUND
      |   |-httpd,9 -DFOREGROUND
      |   |-httpd,10 -DFOREGROUND
      `-mysqld_safe,44 /usr/bin/mysqld_safe --basedir=/usr
          `-mysqld,187 --basedir=/usr --datadir=/var/lib/mysql
              |-{mysqld},191
              |-{mysqld},192

## Problems with SystemD in Docker

The background for this script is the inability to run a
SystemD daemon easily inside a docker container. There have
been multiple workarounds with varying complexity and actual
functionality. (The systemd-nsspawn tool is supposed to help 
with  running systemd in a container but only rkt with CoreOs 
is using it so far).

Most people have come to take the easy path and to create a
startup shell script for the docker container that will
bring up the service processes one by one. Essentially one would
read the documentation or the SystemD `*.service` scripts of the
application to see how that would be done. By using this
replacement script a programmer can skip that step.

## Service Manager

The systemctl-replacement script does cover the functionality
of a service manager where commands like `systemctl start xx`
are executed. This is achieved by parsing the `*.service`
files that are installed by the standard application packages 
(rpm, deb) in the container. These service unit descriptors
define the actual commands to start/stop a service in their
ExecStart/ExecStop settings.

When installing systemctl3.py as /usr/bin/systemctl in a
container then it provides enough functionality that
deployment scripts for virtual machines continue to
work unchanged when trying to start/stop, enable/disable
or mask/unmask a service in a container.

This is also true for deployment tools like Ansible. As of 
version 2.0 and later Ansible is able to connect to docker 
containers directly without the help of a ssh-daemon in 
the container. Just make your inventory look like

    [frontend]
    my_frontend_1 ansible_connection=docker

Based on that `ansible_connection` one can enable the
systemctl-replacement to intercept subsequent calls
to `"service:"` steps. Effectively Ansible scripts that 
shall be run on real virtual machines can be tested 
with docker containers. However in newer centos/ubuntu
images you need to check for python first.

    - copy: src="files/docker/systemctl3.py" dest="/usr/bin/systemctl"
    - package: name="python"
    - file: name="/run/systemd/system/" state="directory"
    - service: name="dbus.service" state="stopped"

See [SERVICE-MANAGER](SERVICE-MANAGER.md) for more details.

---

## Problems with PID 1 in Docker

The command listed as "CMD" in the docker image properties
or being given as docker-run argument will become the PID-1
of a new container. Actually it takes the place that would
traditionally be used by the /sbin/init process which has
a special functionality in unix'ish operating systems.

The docker-stop command will send a SIGTERM to PID-1 in
the container - but NOT to any other process. If the CMD
is the actual application (exec java -jar whatever) then 
this works fine as it will also clean up its subprocesses. 
In many other cases it is not sufficient leaving 
[zombie processes](https://www.howtogeek.com/119815/htg-explains-what-is-a-zombie-process-on-linux/) 
around.

Zombie processes may also occur when a master process does 
not do a `wait` for its children or the children were
explicitly "disown"ed to run as a daemon themselves. The
systemctl replacement script can help here as it implements 
the "zombie reaper" functionality that the standard unix
init daemon would provide. Otherwise the zombie PIDs would
continue to live forever (as long as the container is
running) filling also the process table of the docker host
as the init daemon of the host does not reap them.

## Init Daemon

Another function of the init daemon is to startup the
default system services. What has been known as runlevel
in SystemV is now "multi-user.target" or "graphical.target"
in a SystemD environment.

Let's assume that a system has been configured with some
"systemctl enable xx" services. When a virtual machine
starts then these services are started as well. The
systemctl-replacement script does provide this functionality
for a docker container, thereby implementing
"systemctl default" for usage in inside a container.

The "systemctl halt" command is also implemented
allowing to stop all services that are found as
"is-enabled" services that have been run upon container
start. It does execute all the "systemctl stop xx"
commands to bring down the enabled services correctly.

This is most useful when the systemctl replacement script 
has been run as the entrypoint of a container - so when a 
"docker stop" sends a SIGTERM to the container's PID-1 then 
all the services are shut down before exiting the container.
This can be permanently achieved by registering the
systemctl replacement script  as the CMD attribute of an 
image, perhaps by a "docker commit" like this:

    docker commit -c "CMD ['/usr/bin/systemctl']" \
        -m "<comment>" <container> <new-image>

After all it allows to use a docker container to be
more like a virtual machine with multiple services
running at the same time in the same context.

See [INIT-DAEMON](INIT-DAEMON.md) for more details.

---

## Testsuite and Examples

There is an extensive testsuite in the project that allows
for a high line coverage of the tool. All the major functionality
of the systemctl replacement script is being tested so that its 
usage in continuous development pipeline will no break on updates 
of the script. If the systemctl replacment script has some important
changes in the implementation details it will be marked with
an update of the major version.

Please run the `testsuite.py` or `make check` upon providing
a patch. It takes a couple of minutes because it may download
a number of packages during provisioning - but with the help of the
[docker-mirror-packages-repo](https://github.com/gdraheim/docker-mirror-packages-repo)
scripting this can be reduced a lot (it even runs without internet connection).

Some real world examples have been cut out into a separate
project. See [gdraheim/docker-systemctl-images](https://github.com/gdraheim/docker-systemctl-images)
for a list. Those have been mostly merged back to the v1.7
series in 2026, so you can just check `tests/*.dockerfile`.

See [TESTSUITE](TESTUITE.md) for more details.

## Development

Although this script has been developed for quite a while,
it does only implement a limited number of commands. It
does not cover all commands of "systemctl" and it will not
cover all the functionality of SystemD. The implementation
tries to align with SystemD's systemctl commands as close
as possible as quite some third party tools are interpreting
the output of it. However the implemented software 
[ARCHITECTURE](ARCHITECTURE.md) is very different.

The systemctl replacement script has a long [HISTORY](HISTORY.md)
now with over a [thousand commits on github](https://github.com/gdraheim/docker-systemctl-replacement/tree/master)
(mostly for the testsuite). It has also garnered some additional 
functionality like the [USERMODE](USERMODE.md) which is 
specifically targeted at running docker containers. See the 
[RELEASENOTES](RELEASENOTES.md) for the latest achievements.
The choice of the [EUPL-LICENSE](EUPL-LICENSE.md) is intentionally
permissive to allow you to copy the script to your project.

Sadly the functionality of SystemD's systemctl is badly 
documented so that much of the current implementation is 
done by trial and fixing the errors. Some [BUGS](BUGS.md)
are actually in other tools and need to be circumvented. As 
most programmers tend to write very simple `*.service` files 
it works in a surprising number of cases however. But definitely 
not all. So if there is a problem, use the
[github issue tracker](https://github.com/gdraheim/docker-systemctl-replacement/issues)
to make me aware of it. In general it is not needed to emulate
every feature as [EXTRA-CONFIGS](EXTRA-CONFIGS.md) can help.

And I take patches. ;)

## The author

Guido Draheim is working as a freelance consultant for
multiple big companies in Germany. This script is related to 
the current surge of DevOps topics which often use docker 
as a lightweight replacement for cloud containers or even 
virtual machines. It makes it easier to test deployments
in the standard build pipelines of development teams.
