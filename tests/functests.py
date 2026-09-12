#! /usr/bin/env python3
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,line-too-long,too-many-lines,too-many-public-methods
# pylint: disable=invalid-name,unspecified-encoding,consider-using-with,multiple-statements
""" testing functions directly in strip_python3 module """

__copyright__ = "(C) Guido Draheim, licensed under the EUPL"""
__version__ = "2.1.1311"

from typing import Optional, Any
import sys
import re
import shutil
import inspect
import time
import signal
import unittest
import logging
import os.path
from fnmatch import fnmatchcase as fnmatch

logg = logging.getLogger(os.path.basename(__file__))

SYSTEMCTL = "files/docker/systemctl3.py"
TODO = 0
KEEP = 0
NIX = ""
VV = "-vv"

if __name__ == "__main__":
    # unittest.main()
    from optparse import OptionParser  # pylint: disable=deprecated-module
    cmdline = OptionParser("%prog [options] test*",
                      epilog=__doc__.strip().split("\n", 1)[0])
    cmdline.add_option("-v", "--verbose", action="count", default=0,
                  help="increase logging level [%default]")
    cmdline.add_option("-l", "--logfile", metavar="FILE", default="",
                  help="additionally save the output log to a file [%default]")
    cmdline.add_option("--todo", action="count", default=TODO,
                  help="show when an alternative outcome is desired [%default]")
    cmdline.add_option("--failfast", action="store_true", default=False,
                  help="Stop the test run on the first error or failure. [%default]")
    cmdline.add_option("--xmlresults", metavar="FILE", default=None,
                  help="capture results as a junit xml file [%default]")
    cmdline.add_option("--with", "--systemctl", dest="systemctl", metavar="PY", default=SYSTEMCTL)
    opt, cmdline_args = cmdline.parse_args()
    logging.basicConfig(level = logging.WARNING - opt.verbose * 5)
    TODO = opt.todo
    SYSTEMCTL = opt.systemctl
    VV = "-v" + ("v" * opt.verbose)
    logfile = None
    if opt.logfile:
        if os.path.exists(opt.logfile):
            os.remove(opt.logfile)
        logfile = logging.FileHandler(opt.logfile)
        logfile.setFormatter(logging.Formatter("%(levelname)s:%(relativeCreated)d:%(message)s"))
        logging.getLogger().addHandler(logfile)
        logg.info("log diverted to %s", opt.logfile)

logg.warning("importing %s", SYSTEMCTL)
sys.path.insert(0, os.path.dirname(SYSTEMCTL) or ".")
import journalctl3 as journal # pylint: disable=wrong-import-position,import-error
if "files/docker/systemctl3" in SYSTEMCTL:
    sys.path = [os.curdir] + sys.path
    from files.docker import systemctl3 as app # pylint: disable=wrong-import-position,import-error,no-name-in-module
elif "src/systemctl3" in SYSTEMCTL:
    sys.path = [os.curdir] + sys.path
    from src import systemctl3 as app # type: ignore[no-redef,attr-defined,unused-ignore] # pylint: disable=no-name-in-module
elif "src/systemctl" in SYSTEMCTL:
    sys.path = [os.curdir] + sys.path
    from src import systemctl as app # type: ignore[no-redef,attr-defined,unused-ignore] # pylint: disable=no-name-in-module
elif "tmp/systemctl3" in SYSTEMCTL:
    sys.path = [os.curdir] + sys.path
    from tmp import systemctl3 as app # type: ignore[no-redef,attr-defined,unused-ignore] # pylint: disable=no-name-in-module
elif "tmp/systemctl" in SYSTEMCTL:
    sys.path = [os.curdir] + sys.path
    from tmp import systemctl as app # type: ignore[no-redef,attr-defined,unused-ignore] # pylint: disable=no-name-in-module
else:
    raise ImportError(F"unknown src location {SYSTEMCTL}")

def shell_file(filename: str, content: str) -> None:
    text_file(filename, content)
    os.chmod(filename, 0o775)
def text_file(filename: str, content: str) -> None:
    filedir = os.path.dirname(filename)
    if not os.path.isdir(filedir):
        os.makedirs(filedir)
    f = open(filename, "w")
    if content.startswith("\n"):
        x = re.match("(?s)\n( *)", content)
        assert x is not None
        indent = x.group(1)
        for line in content[1:].split("\n"):
            if line.startswith(indent):
                line = line[len(indent):]
            f.write(line+"\n")
    else:
        f.write(content)
    f.close()
    logg.info("::: made %s", filename)
def get_caller_name() -> str:
    currentframe = inspect.currentframe()
    if not currentframe: return "global"
    frame = currentframe.f_back.f_back # type: ignore[union-attr]
    return frame.f_code.co_name # type: ignore[union-attr]
def get_caller_caller_name() -> str:
    currentframe = inspect.currentframe()
    if not currentframe: return "global"
    frame = currentframe.f_back.f_back.f_back # type: ignore[union-attr]
    return frame.f_code.co_name # type: ignore[union-attr]

def execmode(val: app.ExecMode) -> str:
    bits = ["check" if val.check else "nocheck"]
    if val.nouser:
        bits += ["nouser"]
    if val.noexpand:
        bits += ["noexpand"]
    if val.argv0:
        bits += ["argv0"]
    return "+".join(bits)

class AppUnitTest(unittest.TestCase):
    def assertEq(self, val1: Any, val2: Any, msg: str = NIX) -> None: # type: ignore[explicit-any]
        self.assertEqual(val2, val1, msg)
    def caller_testname(self) -> str:
        name = get_caller_caller_name()
        x1 = name.find("_")
        if x1 < 0: return name
        x2 = name.find("_", x1+1)
        if x2 < 0: return name
        return name[:x2]
    def testname(self, suffix: Optional[str] = None) -> str:
        name = self.caller_testname()
        if suffix:
            return name + "_" + suffix
        return name
    def testdir(self, testname: Optional[str] = None, keep: bool = False) -> str:
        testname = testname or self.caller_testname()
        newdir = "tmp/tmp."+testname
        if os.path.isdir(newdir) and not keep:
            shutil.rmtree(newdir)
        if not os.path.isdir(newdir):
            os.makedirs(newdir)
        return newdir
    def rm_testdir(self, testname: Optional[str] = None) -> str:
        testname = testname or self.caller_testname()
        newdir = "tmp/tmp."+testname
        if os.path.isdir(newdir):
            if not KEEP:
                shutil.rmtree(newdir)
        return newdir
    def test_0100(self) -> None:
        n = app.to_int(0)
        y = app.to_int(1)
        x = app.to_int(2)
        self.assertEqual(n, 0)
        self.assertEqual(y, 1)
        self.assertEqual(x, 2)
    def test_0101(self) -> None:
        n = app.to_int("0")
        y = app.to_int("1")
        x = app.to_int("2")
        z = app.to_int("zz", 11)
        d = app.to_int("1.1.1")
        e = app.to_int("1.1.1", -1)
        f = app.to_int(["wrong"]) # type: ignore[arg-type]
        self.assertEqual(n, 0)
        self.assertEqual(y, 1)
        self.assertEqual(x, 2)
        self.assertEqual(z, 11)
        self.assertEqual(d, 0)
        self.assertEqual(e, -1)
        self.assertEqual(f, 0)
    def test_0105(self) -> None:
        n = app.to_intN(None, 11)
        m = app.to_intN("m", 11)
        x = app.to_intN("2")
        y = app.to_intN("1")
        z = app.to_intN("0")
        d = app.to_intN("1.1.1")
        e = app.to_intN("1.1.1", -1)
        f = app.to_intN(["wrong"]) # type: ignore[arg-type]
        self.assertEqual(n, 11)
        self.assertEqual(m, 11)
        self.assertEqual(x, 2)
        self.assertEqual(y, 1)
        self.assertEqual(z, 0)
        self.assertEqual(d, None)
        self.assertEqual(e, -1)
        self.assertEqual(f, None)
    def test_0109(self) -> None:
        n = app.int_mode("")
        x = app.int_mode("2")
        y = app.int_mode("1")
        z = app.int_mode("0")
        q = app.int_mode("qq")
        r = app.int_mode("11")
        d = app.int_mode("1.1.1")
        e = app.int_mode("1.1.1", -1)
        f = app.int_mode(["wrong"]) # type: ignore[arg-type]
        self.assertEqual(n, None)
        self.assertEqual(x, 2)
        self.assertEqual(y, 1)
        self.assertEqual(z, 0)
        self.assertEqual(q, None)
        self.assertEqual(r, 9)
        self.assertEqual(d, None)
        self.assertEqual(e, -1)
        self.assertEqual(f, None)
    def test_0110(self) -> None:
        n = app.strYes(None)
        x = app.strYes(False)
        y = app.strYes(True)
        z = app.strYes("zz")
        self.assertEqual(n, "no")
        self.assertEqual(x, "no")
        self.assertEqual(y, "yes")
        self.assertEqual(z, "zz")
    def test_0111(self) -> None:
        n = app.strE(None)
        x = app.strE(False)
        y = app.strE(True)
        z = app.strE("zz")
        self.assertEqual(n, "")
        self.assertEqual(x, "")
        self.assertEqual(y, "*")
        self.assertEqual(z, "zz")
    def test_0112(self) -> None:
        n = app.strE(None)
        x = app.strE(False)
        y = app.strE(True)
        z = app.strE("zz")
        self.assertTrue(n is app.NIX)
        self.assertTrue(x is app.NIX)
        self.assertTrue(y is app.ALL)
        self.assertFalse(z is app.NIX)
    def test_0113(self) -> None:
        n = app.strQ(None)
        x = app.strQ(0)
        y = app.strQ(1)
        z = app.strQ("zz")
        q = app.strQ("")
        self.assertEqual(n, "")
        self.assertEqual(x, "0")
        self.assertEqual(y, "1")
        self.assertEqual(z, "'zz'")
        self.assertEqual(q, "''")
    def test_0115(self) -> None:
        s20 = "0123456789" * 2
        s90 = "0123456789" * 9
        x20 = app.o22(s20)
        x90 = app.o22(s90)
        xxx = app.o22(["x"])   # type: ignore[arg-type]
        self.assertEq(x20, s20)
        self.assertEq(x90, "01234...67890123456789")
        self.assertEq(len(x90), 22)
        self.assertEq(xxx, ["x"])
        n = app.o22(None) # type: ignore[arg-type]
        z = app.o22(0) # type: ignore[arg-type]
        self.assertEqual(n, None)
        self.assertEqual(z, 0)
    def test_0116(self) -> None:
        s20 = "0123456789" * 2
        s90 = "0123456789" * 9
        x20 = app.o44(s20)
        x90 = app.o44(s90)
        xxx = app.o44(["x"])   # type: ignore[arg-type]
        self.assertEq(x20, s20)
        self.assertEq(x90, "0123456789...9012345678901234567890123456789")
        self.assertEq(len(x90), 44)
        self.assertEq(xxx, ["x"])
        n = app.o44(None) # type: ignore[arg-type]
        z = app.o44(0) # type: ignore[arg-type]
        self.assertEq(n, None)
        self.assertEq(z, 0)
    def test_0117(self) -> None:
        s20 = "0123456789" * 2
        s90 = "0123456789" * 9
        x20 = app.o77(s20)
        x90 = app.o77(s90)
        xxx = app.o77(["x"])   # type: ignore[arg-type]
        self.assertEq(x20, s20)
        self.assertEq(x90, "01234567890123456789...678901234567890123456789012345678901234567890123456789")
        self.assertEq(len(x90), 77)
        self.assertEq(xxx, ["x"])
        n = app.o77(None) # type: ignore[arg-type]
        z = app.o77(0) # type: ignore[arg-type]
        self.assertEqual(n, None)
        self.assertEqual(z, 0)
    def test_0118(self) -> None:
        n00 = app.delayed(0)
        n01 = app.delayed(1)
        n02 = app.delayed(2)
        n09 = app.delayed(9)
        n10 = app.delayed(10)
        n11 = app.delayed(11)
        n99 = app.delayed(99)
        n111 = app.delayed(111)
        self.assertEqual(n00, "...")
        self.assertEqual(n01, "+1.")
        self.assertEqual(n02, "+2.")
        self.assertEqual(n09, "+9.")
        self.assertEqual(n10, "10.")
        self.assertEqual(n11, "11.")
        self.assertEqual(n99, "99.")
        self.assertEqual(n111, "111.")
    def test_0119(self) -> None:
        n00 = app.delayed(0,":")
        n01 = app.delayed(1,":")
        n02 = app.delayed(2,":")
        n09 = app.delayed(9,":")
        n10 = app.delayed(10,":")
        n11 = app.delayed(11,":")
        n99 = app.delayed(99,":")
        n111 = app.delayed(111,":")
        self.assertEqual(n00, "..:")
        self.assertEqual(n01, "+1:")
        self.assertEqual(n02, "+2:")
        self.assertEqual(n09, "+9:")
        self.assertEqual(n10, "10:")
        self.assertEqual(n11, "11:")
        self.assertEqual(n99, "99:")
        self.assertEqual(n111, "111:")
    def test_0120(self) -> None:
        n0 = app.to_list(None)
        n1 = app.to_list([])
        n2 = app.to_list("")
        n3 = app.to_list(())
        n4 = app.to_list(0) # type: ignore[arg-type]
        x1 = app.to_list([""])
        y1 = app.to_list(("",))
        z1 = app.to_list(",")
        x2 = app.to_list(["",""])
        y2 = app.to_list(("",""))
        z2 = app.to_list(",,")
        self.assertEqual(n0, [])
        self.assertEqual(n1, [])
        self.assertEqual(n2, [])
        self.assertEqual(n3, [])
        self.assertEqual(n4, [])
        self.assertEqual(x1, [""])
        self.assertEqual(y1, [""])
        self.assertEqual(z1, ["",""])
        self.assertEqual(x2, ["",""])
        self.assertEqual(y2, ["",""])
        self.assertEqual(z2, ["","",""])
    def test_0122(self) -> None:
        n1 = app.commalist([""])
        n2 = app.commalist(["", ""])
        n3 = app.commalist([" "])
        n4 = app.commalist(["", " "])
        x1 = app.commalist([","])
        x2 = app.commalist([",", ","])
        x3 = app.commalist([", "])
        x4 = app.commalist([" ,", " , "])
        a1 = app.commalist(["a"])
        a2 = app.commalist(["a", ""])
        a3 = app.commalist(["a,", ","])
        b1 = app.commalist(["a,b"])
        b2 = app.commalist(["a,b", ""])
        c1 = app.commalist(["a,b", "c"])
        c2 = app.commalist(["a,b", "", "c"])
        self.assertEq(n1, [])
        self.assertEq(n2, [])
        self.assertEq(n3, [])
        self.assertEq(n4, [])
        self.assertEq(x1, [])
        self.assertEq(x2, [])
        self.assertEq(x3, [])
        self.assertEq(x4, [])
        self.assertEq(a1, ["a"])
        self.assertEq(a2, ["a"])
        self.assertEq(a3, ["a"])
        self.assertEq(b1, ["a", "b"])
        self.assertEq(b2, ["a", "b"])
        self.assertEq(c1, ["a", "b", "c"])
        self.assertEq(c2, ["a", "b", "c"])
    def test_0124(self) -> None:
        n1 = app.wordlist([""])
        n2 = app.wordlist(["", ""])
        n3 = app.wordlist([" "])
        n4 = app.wordlist(["", " "])
        x1 = app.wordlist([","])
        x2 = app.wordlist([",", ","])
        x3 = app.wordlist([", "])
        x4 = app.wordlist([" ,", " , "])
        a1 = app.wordlist(["a"])
        a2 = app.wordlist(["a", ""])
        a3 = app.wordlist(["a,", ","])
        b1 = app.wordlist(["a b"])
        b2 = app.wordlist(["a b", ""])
        c1 = app.wordlist(["a b", "c"])
        c2 = app.wordlist(["a b", "", "c"])
        c3 = app.wordlist(["a b ", " ", "c "])
        self.assertEq(n1, [])
        self.assertEq(n2, [])
        self.assertEq(n3, [])
        self.assertEq(n4, [])
        self.assertEq(x1, [','])
        self.assertEq(x2, [',',','])
        self.assertEq(x3, [','])
        self.assertEq(x4, [',',','])
        self.assertEq(a1, ["a"])
        self.assertEq(a2, ["a"])
        self.assertEq(a3, ['a,',','])
        self.assertEq(b1, ["a", "b"])
        self.assertEq(b2, ["a", "b"])
        self.assertEq(c1, ["a", "b", "c"])
        self.assertEq(c2, ["a", "b", "c"])
        self.assertEq(c3, ["a", "b", "c"])
    def test_0130(self) -> None:
        n = app.fnmatched("a")
        z = app.fnmatched("a", "")
        x = app.fnmatched("a", "", "b")
        a = app.fnmatched("a", "a")
        b = app.fnmatched("a", "b")
        c = app.fnmatched("a", "b", "a")
        self.assertTrue(n)
        self.assertTrue(z)
        self.assertTrue(x)
        self.assertTrue(a)
        self.assertFalse(b)
        self.assertTrue(c)
    def test_0201(self) -> None:
        import socket # pylint: disable=import-outside-toplevel
        want = "UDP"
        have = app.strINET(socket.SOCK_DGRAM)
        self.assertEqual(have, want)
    def test_0202(self) -> None:
        import socket # pylint: disable=import-outside-toplevel
        want = "TCP"
        have = app.strINET(socket.SOCK_STREAM)
        self.assertEqual(have, want)
    def test_0203(self) -> None:
        import socket # pylint: disable=import-outside-toplevel
        want = "RAW"
        have = app.strINET(socket.SOCK_RAW)
        self.assertEqual(have, want)
    def test_0204(self) -> None:
        import socket # pylint: disable=import-outside-toplevel
        want = "RDM"
        have = app.strINET(socket.SOCK_RDM)
        self.assertEqual(have, want)
    def test_0205(self) -> None:
        import socket # pylint: disable=import-outside-toplevel
        want = "SEQ"
        have = app.strINET(socket.SOCK_SEQPACKET)
        self.assertEqual(have, want)
    def test_0209(self) -> None:
        import socket # pylint: disable=import-outside-toplevel,unused-import
        want = "<?>"
        have = app.strINET(255)
        self.assertEqual(have, want)
    def test_0210(self) -> None:
        orig = "foo/bar-1@/var.lock$"
        want = "foo-bar\\x2d1\\x40-var.lock\\x24"
        have = app.unit_name_escape(orig)
        self.assertEqual(have, want)
        back = app.unit_name_unescape(have)
        self.assertEqual(back, orig)
    def test_0230(self) -> None:
        runs = os.environ.get("XDG_RUNTIME_DIR", "")
        want = runs or "/tmp/run-"
        have = app.get_runtime_dir()
        logg.info("have %s", have)
        self.assertTrue(have.startswith(want))
    def test_0231(self) -> None:
        runs = os.environ.get("XDG_RUNTIME_DIR", "")
        want = runs or "/tmp/run-"
        have = app.get_RUN()
        logg.info("have %s", have)
        want = "/tmp/run"
        have = app.get_RUN(True)
        logg.info("have %s", have)
        self.assertTrue(have.startswith(want))
    def test_0232(self) -> None:
        runs = os.environ.get("XDG_RUNTIME_DIR", "")
        want = runs or "/tmp/run-"
        have = app.get_PID_DIR()
        logg.info("have %s", have)
        self.assertTrue(have.startswith(want))
        want = "/tmp/run"
        have = app.get_PID_DIR(True)
        logg.info("have %s", have)
        self.assertTrue(have.startswith(want))
    def test_0233(self) -> None:
        home = os.path.expanduser("~")
        have = app.get_HOME()
        logg.info("have %s", have)
        self.assertEqual(have, home)
        home = os.path.expanduser("~root")
        have = app.get_HOME(True)
        logg.info("have %s", have)
        self.assertEqual(have, home)
    def test_0234(self) -> None:
        have = app.is_good_root(None)
        self.assertEq(have, True)
        have = app.is_good_root("")
        self.assertEq(have, True)
        have = app.is_good_root("/")
        self.assertEq(have, False)
        have = app.is_good_root("/a")
        self.assertEq(have, False)
        have = app.is_good_root("/a/b")
        self.assertEq(have, False)
        have = app.is_good_root("/a/b/")
        self.assertEq(have, False)
        have = app.is_good_root("/a/b/c")
        self.assertEq(have, True)
        have = app.is_good_root("a/b")
        self.assertEq(have, False)
        have = app.is_good_root("a/b/")
        self.assertEq(have, False)
        have = app.is_good_root("a/b/c")
        self.assertEq(have, True)
    def test_0235(self) -> None:
        have = app.os_path("","")
        self.assertEq(have, "")
        have = app.os_path("","y")
        self.assertEq(have, "y")
        have = app.os_path("x","")
        self.assertEq(have, "")
        have = app.os_path("x","y")
        self.assertEq(have, "x/y")
        have = app.os_path("x","/y")
        self.assertEq(have, "x/y")
        have = app.os_path("x","//y")
        self.assertEq(have, "//y")
    def test_0236(self) -> None:
        have = app.get_unit_type("foo")
        self.assertEq(have, None)
        have = app.get_unit_type("foo.c")
        self.assertEq(have, None)
        have = app.get_unit_type("foo.py")
        self.assertEq(have, None)
        have = app.get_unit_type("foo.txt")
        self.assertEq(have, None)
        have = app.get_unit_type("foo.html")
        self.assertEq(have, None)
        have = app.get_unit_type("foo.htmlx")
        self.assertEq(have, "htmlx")
        have = app.get_unit_type("foo.timer")
        self.assertEq(have, "timer")
        have = app.get_unit_type("foo.target")
        self.assertEq(have, "target")
        have = app.get_unit_type("foo.socket")
        self.assertEq(have, "socket")
        have = app.get_unit_type("foo.service")
        self.assertEq(have, "service")
    def test_0237(self) -> None:
        pre, cmd = app.checkprefix("foo")
        self.assertEq(cmd, "foo")
        self.assertEq(pre, "")
        pre, cmd = app.checkprefix("-foo")
        self.assertEq(cmd, "foo")
        self.assertEq(pre, "-")
        pre, cmd = app.checkprefix("-!foo")
        self.assertEq(cmd, "foo")
        self.assertEq(pre, "-!")
        pre, cmd = app.checkprefix("!-foo")
        self.assertEq(cmd, "foo")
        self.assertEq(pre, "!-")
        pre, cmd = app.checkprefix("-+!@foo")
        self.assertEq(cmd, "foo")
        self.assertEq(pre, "-+!@")
        pre, cmd = app.checkprefix("-+:|foo")
        self.assertEq(cmd, "foo")
        self.assertEq(pre, "-+:|")
        pre, cmd = app.checkprefix("")
        self.assertEq(cmd, "")
        self.assertEq(pre, "")
    def test_0238(self) -> None:
        pre, cmd = app.exec_path("foo")
        self.assertEq(cmd, "foo")
        self.assertEq(pre.mode, "")
        self.assertTrue(pre.check)
        self.assertFalse(pre.nouser)
        self.assertFalse(pre.noexpand)
        self.assertFalse(pre.argv0)
        pre, cmd = app.exec_path("-foo")
        self.assertEq(cmd, "foo")
        self.assertEq(pre.mode, "-")
        self.assertFalse(pre.check)
        self.assertFalse(pre.nouser)
        self.assertFalse(pre.noexpand)
        self.assertFalse(pre.argv0)
        pre, cmd = app.exec_path("-!foo")
        self.assertEq(cmd, "foo")
        self.assertEq(pre.mode, "-!")
        self.assertFalse(pre.check)
        self.assertTrue(pre.nouser)
        self.assertFalse(pre.noexpand)
        self.assertFalse(pre.argv0)
        pre, cmd = app.exec_path("!-foo")
        self.assertEq(cmd, "foo")
        self.assertEq(pre.mode, "!-")
        self.assertFalse(pre.check)
        self.assertTrue(pre.nouser)
        self.assertFalse(pre.noexpand)
        self.assertFalse(pre.argv0)
        pre, cmd = app.exec_path("-+!@foo")
        self.assertEq(cmd, "foo")
        self.assertEq(pre.mode, "-+!@")
        self.assertFalse(pre.check)
        self.assertTrue(pre.nouser)
        self.assertFalse(pre.noexpand)
        self.assertTrue(pre.argv0)
        pre, cmd = app.exec_path("-+:|foo")
        self.assertEq(cmd, "foo")
        self.assertEq(pre.mode, "-+:|")
        self.assertFalse(pre.check)
        self.assertTrue(pre.nouser)
        self.assertTrue(pre.noexpand)
        self.assertFalse(pre.argv0)
        pre, cmd = app.exec_path("")
        self.assertEq(cmd, "")
        self.assertEq(pre.mode, "")
        self.assertTrue(pre.check)
        self.assertFalse(pre.nouser)
        self.assertFalse(pre.noexpand)
        self.assertFalse(pre.argv0)
    def test_0239(self) -> None:
        pre, cmd = app.load_path("foo")
        self.assertEq(cmd, "foo")
        self.assertEq(pre.mode, "")
        self.assertTrue(pre.check)
        pre, cmd = app.load_path("-foo")
        self.assertEq(cmd, "foo")
        self.assertEq(pre.mode, "-")
        self.assertFalse(pre.check)
        pre, cmd = app.load_path("-!foo")
        self.assertEq(cmd, "!foo")
        self.assertEq(pre.mode, "-")
        self.assertFalse(pre.check)
        pre, cmd = app.load_path("!-foo")
        self.assertEq(cmd, "!-foo")
        self.assertEq(pre.mode, "")
        self.assertTrue(pre.check)
        pre, cmd = app.load_path("-+:|foo")
        self.assertEq(cmd, "+:|foo")
        self.assertEq(pre.mode, "-")
        self.assertFalse(pre.check)
        pre, cmd = app.load_path("")
        self.assertEq(cmd, "")
        self.assertEq(pre.mode, "")
        self.assertTrue(pre.check)
    def test_0240(self) -> None:
        want = 777
        have = app.time_to_seconds("infinity", 777)
        logg.info("have %s", have)
        self.assertEqual(have, want)
    def test_0241(self) -> None:
        want = 111
        have = app.time_to_seconds("111", 777)
        logg.info("have %s", have)
        self.assertEqual(have, want)
        have = app.time_to_seconds("111s", 777)
        logg.info("have %s", have)
        self.assertEqual(have, want)
        have = app.time_to_seconds("111 s", 777)
        logg.info("have %s", have)
        self.assertEqual(have, want)
        have = app.time_to_seconds("999 s", 777)
        logg.info("have %s", have)
        self.assertEqual(have, 777)
        have = app.time_to_seconds("999ms", 777)
        logg.info("have %s", have)
        self.assertEqual(have, 0.999)
        have = app.time_to_seconds("xxs", 777)
        logg.info("have %s", have)
        self.assertEqual(have, 99)
        have = app.time_to_seconds("xxms", 777)
        logg.info("have %s", have)
        self.assertEqual(have, 1)
        have = app.time_to_seconds("s", 777)
        logg.info("have %s", have)
        self.assertEqual(have, 1)
        have = app.time_to_seconds("ms", 777)
        logg.info("have %s", have)
        self.assertEqual(have, 1)
    def test_0242(self) -> None:
        want = 6660
        have = app.time_to_seconds("111min", 7777)
        logg.info("have %s", have)
        self.assertEqual(have, want)
        have = app.time_to_seconds("111m", 7777)
        logg.info("have %s", have)
        self.assertEqual(have, want)
        have = app.time_to_seconds("111 m", 7777)
        logg.info("have %s", have)
        self.assertEqual(have, 111) # TODO
        have = app.time_to_seconds("9999 m", 7777)
        logg.info("have %s", have)
        self.assertEqual(have, 7777)
        have = app.time_to_seconds("xxmin", 7777)
        logg.info("have %s", have)
        self.assertEqual(have, 99*60)
        have = app.time_to_seconds("xxm", 7777)
        logg.info("have %s", have)
        self.assertEqual(have, 99*60)
        have = app.time_to_seconds("m", 777)
        logg.info("have %s", have)
        self.assertEqual(have, 1)
        have = app.time_to_seconds("min", 777)
        logg.info("have %s", have)
        self.assertEqual(have, 1)
    def test_0260(self) -> None:
        have = app.pid_zombie(None) # type: ignore[arg-type]
        logg.info("have %s", have)
        self.assertFalse(have)
        have = app.pid_zombie(-1)
        logg.info("have %s", have)
        self.assertFalse(have)
        self.assertRaises(ValueError, lambda: app.pid_zombie(0))
        have = app.pid_zombie(1)
        logg.info("have %s", have)
        self.assertFalse(have)
        maxpid = int(open('/proc/sys/kernel/pid_max').read())
        logg.info("maxpid %s", maxpid)
        have = app.pid_zombie(maxpid+1)
        logg.info("have %s", have)
        self.assertFalse(have)
        have = app.pid_zombie(os.getpid())
        logg.info("have %s", have)
        self.assertFalse(have)
    def test_0270(self) -> None:
        tmp = self.testdir()
        svc1 = "test1.txt"
        svc2 = "test2.txt"
        text_file(F"{tmp}/{svc1}", """info""")
        have = app.get_exist_path([svc1,svc2])
        self.assertEq(have, None)
        have = app.get_exist_path([F"{tmp}/{svc1}",F"{tmp}/{svc2}"])
        self.assertEq(have, F"{tmp}/{svc1}")
        have = app.get_exist_path([F"{tmp}/{svc2}",F"{tmp}/{svc1}"])
        self.assertEq(have, F"{tmp}/{svc1}")
        self.rm_testdir()
    def test_0271(self) -> None:
        tmp = self.testdir()
        svc1 = "test1.txt"
        svc2 = "test2.txt"
        text_file(F"{tmp}/{svc1}", """info""")
        size1 = os.path.getsize(F"{tmp}/{svc1}")
        app.shutil_truncate(F"{tmp}/{svc1}")
        size2 = os.path.getsize(F"{tmp}/{svc1}")
        self.assertNotEqual(size1, size2)
        self.assertEqual(size2, 0)
        new1: Optional[int]
        try:
            new1 = os.path.getsize(F"{tmp}/{svc2}")
        except OSError:
            new1 = None
        app.shutil_truncate(F"{tmp}/{svc2}")
        new2 = os.path.getsize(F"{tmp}/{svc2}")
        self.assertNotEqual(new1, new2)
        self.assertEqual(new1, None)
        self.assertEqual(new2, 0)
        app.shutil_truncate(F"{tmp}/subdir/{svc2}")
        sub2 = os.path.getsize(F"{tmp}/subdir/{svc2}")
        self.assertEqual(sub2, 0)
    def test_0272(self) -> None:
        tmp = self.testdir()
        files = app.SystemctlUnitFiles(tmp)
        want = os.path.expanduser("~/.config/systemd/user")
        have = files.user_folder()
        logg.info("have %s", have)
        self.assertEq(have, want)
        have = files.system_folder()
        logg.info("have %s", have)
        self.assertEq(have, "/etc/systemd/system")
        files._SYSTEMD_UNIT_PATH = "" # pylint: disable=protected-access
        self.assertRaises(FileNotFoundError, files.user_folder)
        self.assertRaises(FileNotFoundError, files.system_folder)
        self.rm_testdir()
    def test_0300(self) -> None:
        tmp = self.testdir()
        svc1 = "test1.service"
        text_file(F"{tmp}/{svc1}", """
        [Unit]
        Description = foo""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        want = "foo"
        conf = unit.get_conf(svc1)
        have = unit.get_Description(conf)
        self.assertEqual(want, have)
        self.rm_testdir()
    def test_0350(self) -> None:
        """ PermissionsStartOnly=yes is off by default """
        tmp = self.testdir()
        svc1 = "test1.service"
        text_file(F"{tmp}/{svc1}", """
        [Service]
        User = someone
        ExecStart = /usr/bin/true""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        conf = unit.get_conf(svc1)
        self.assertEq(unit.get_PermissionsStartOnly(conf), False)
        self.rm_testdir()
    def test_0351(self) -> None:
        """ PermissionsStartOnly=yes is read from the [Service] section """
        tmp = self.testdir()
        svc1 = "test1.service"
        text_file(F"{tmp}/{svc1}", """
        [Service]
        User = someone
        PermissionsStartOnly = yes
        ExecStart = /usr/bin/true""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        conf = unit.get_conf(svc1)
        self.assertEq(unit.get_PermissionsStartOnly(conf), True)
        self.assertEq(unit.get_User(conf), "someone")
        self.rm_testdir()
    def test_0352(self) -> None:
        """ the '+' prefix of an Exec line is reported as nouser, so that the
            step runs privileged even when the service has a User= """
        tmp = self.testdir()
        svc1 = "test1.service"
        text_file(F"{tmp}/{svc1}", """
        [Service]
        User = someone
        ExecStartPre = +/usr/bin/true
        ExecStart = /usr/bin/true""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        conf = unit.get_conf(svc1)
        env = unit.get_env(conf)
        for cmd in conf.getlist("Service", "ExecStartPre", []):
            exe, newcmd = unit.expand_cmd(cmd, env, conf)
            self.assertEq(newcmd, ["/usr/bin/true"])
            self.assertEq(exe.nouser, True)
        for cmd in conf.getlist("Service", "ExecStart", []):
            exe, newcmd = unit.expand_cmd(cmd, env, conf)
            self.assertEq(exe.nouser, False)
        self.rm_testdir()
    def test_0354(self) -> None:
        """ run_as_root() is the decision the Exec steps make: either the unit says
            PermissionsStartOnly=yes, or the single step is prefixed with '+' """
        tmp = self.testdir()
        svc1, svc2 = "test1.service", "test2.service"
        text_file(F"{tmp}/{svc1}", """
        [Service]
        User = someone
        ExecStartPre = +/usr/bin/true
        ExecStart = /usr/bin/true""")
        text_file(F"{tmp}/{svc2}", """
        [Service]
        User = someone
        PermissionsStartOnly = yes
        ExecStart = /usr/bin/true""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        unit.add_unit_file(svc2, F"{tmp}/{svc2}")
        systemctl = app.Systemctl()
        conf1 = unit.get_conf(svc1)
        env1 = unit.get_env(conf1)
        pre = conf1.getlist("Service", "ExecStartPre", [])[0]
        exe, newcmd = unit.expand_cmd(pre, env1, conf1)
        self.assertEq(systemctl.run_as_root(conf1, exe), True)   # '+' prefix
        start = conf1.getlist("Service", "ExecStart", [])[0]
        exe, newcmd = unit.expand_cmd(start, env1, conf1)
        self.assertEq(systemctl.run_as_root(conf1, exe), False)  # plain, has User=
        conf2 = unit.get_conf(svc2)
        env2 = unit.get_env(conf2)
        start = conf2.getlist("Service", "ExecStart", [])[0]
        exe, newcmd = unit.expand_cmd(start, env2, conf2)
        self.assertEq(systemctl.run_as_root(conf2, exe), True)   # PermissionsStartOnly
        self.rm_testdir()
    def test_0353(self) -> None:
        """ '!' is the other spelling of the same thing, and the prefixes
            combine with '-' (no-check) in any order """
        tmp = self.testdir()
        svc1 = "test1.service"
        text_file(F"{tmp}/{svc1}", """
        [Service]
        ExecStartPre = !/usr/bin/true
        ExecStartPost = -+/usr/bin/true
        ExecStop = +-/usr/bin/true""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        conf = unit.get_conf(svc1)
        env = unit.get_env(conf)
        for name, nouser, check in [("ExecStartPre", True, True), ("ExecStartPost", True, False), ("ExecStop", True, False)]:
            for cmd in conf.getlist("Service", name, []):
                exe, newcmd = unit.expand_cmd(cmd, env, conf)
                self.assertEq(newcmd, ["/usr/bin/true"], name)
                self.assertEq(exe.nouser, nouser, name)
                self.assertEq(exe.check, check, name)
        self.rm_testdir()
    def test_0360(self) -> None:
        """ journalctl --since is accepted and ignored - deployment tooling passes it
            and systemd would not fail on it either """
        parser = journal.argument_parser()
        args = parser.parse_args(["-u", "zzz.service", "--since", "yesterday"])
        self.assertEq(args.unit, "zzz.service")
        self.assertEq(args.since, "yesterday")
        cmd = journal.systemctl_command(args)
        self.assertEq("--since" in cmd, False)
        self.assertEq("yesterday" in cmd, False)
    def test_0361(self) -> None:
        """ it calls the tool by the name it is installed under, 'systemctl' """
        parser = journal.argument_parser()
        args = parser.parse_args(["-u", "zzz.service"])
        self.assertEq(journal.systemctl_command(args), ["systemctl", "log", "zzz.service"])
        self.assertEq(journal.systemctl_command(args, "/bin"), ["/bin/systemctl", "log", "zzz.service"])
    def test_0362(self) -> None:
        """ the other options are translated, and -u itself is dropped """
        parser = journal.argument_parser()
        args = parser.parse_args(["-u", "zzz.service", "-f", "-n", "5", "--no-pager", "--root", "/R", "-x"])
        cmd = journal.systemctl_command(args)
        self.assertEq(cmd, ["systemctl", "log", "zzz.service", "-f", "-n", "5", "--no-pager", "--root", "/R", "-vvv"])
        self.assertEq("-u" in cmd, False)
    def test_0370(self) -> None:
        """ unmask removes the /dev/null symlink that masking put there """
        tmp = self.testdir()
        sysd = F"{tmp}/etc/systemd/system"
        os.makedirs(sysd)
        svc1 = "masked1.service"
        os.symlink("/dev/null", F"{sysd}/{svc1}")
        systemctl = app.Systemctl()
        systemctl._root = tmp # pylint: disable=protected-access
        systemctl.unitfiles._root = tmp # pylint: disable=protected-access
        self.assertEq(os.path.islink(F"{sysd}/{svc1}"), True)
        systemctl.unmask_unit(svc1)
        self.assertEq(os.path.exists(F"{sysd}/{svc1}"), False)
        self.rm_testdir()
    def test_0371(self) -> None:
        """ unmask must not remove a symlink that is NOT a mask - a unit file may
            well be a link to the real unit (an alias, or a packaging choice), and
            deleting it uninstalls the service instead of unmasking it """
        tmp = self.testdir()
        sysd = F"{tmp}/etc/systemd/system"
        os.makedirs(sysd)
        real, link = "real1.service", "link1.service"
        text_file(F"{sysd}/{real}", """
        [Service]
        ExecStart = /usr/bin/true""")
        os.symlink(real, F"{sysd}/{link}")
        systemctl = app.Systemctl()
        systemctl._root = tmp # pylint: disable=protected-access
        systemctl.unitfiles._root = tmp # pylint: disable=protected-access
        systemctl.unmask_unit(link)
        self.assertEq(os.path.islink(F"{sysd}/{link}"), True)
        self.assertEq(os.readlink(F"{sysd}/{link}"), real)
        self.assertEq(os.path.isfile(F"{sysd}/{real}"), True)
        self.rm_testdir()
    def _list_unit_files_setup(self, tmp: str) -> "app.Systemctl":
        sysd = F"{tmp}/etc/systemd/system"
        os.makedirs(sysd)
        for name in ["zza.service", "zzb.service", "other.service"]:
            text_file(F"{sysd}/{name}", """
            [Service]
            ExecStart = /usr/bin/true""")
        os.symlink("/dev/null", F"{sysd}/zzmasked.service")
        systemctl = app.Systemctl()
        systemctl._root = tmp # pylint: disable=protected-access
        systemctl.unitfiles._root = tmp # pylint: disable=protected-access
        systemctl._no_legend = True # pylint: disable=protected-access
        return systemctl
    def test_0380(self) -> None:
        """ list-unit-files PATTERN filters the listing """
        tmp = self.testdir()
        systemctl = self._list_unit_files_setup(tmp)
        names = [item[0] for item in systemctl.list_unit_files_modules("zz*")]
        self.assertEq(sorted(names), ["zza.service", "zzb.service", "zzmasked.service"])
        self.rm_testdir()
    def test_0381(self) -> None:
        """ every PATTERN counts, not just the first one """
        tmp = self.testdir()
        systemctl = self._list_unit_files_setup(tmp)
        names = [item[0] for item in systemctl.list_unit_files_modules("zza*", "other*")]
        self.assertEq(sorted(names), ["other.service", "zza.service"])
        self.rm_testdir()
    def test_0382(self) -> None:
        """ --state=masked selects by the enablement state that is listed """
        tmp = self.testdir()
        systemctl = self._list_unit_files_setup(tmp)
        systemctl._only_state = ["masked"] # pylint: disable=protected-access
        names = [item[0] for item in systemctl.list_unit_files_modules()]
        self.assertEq(names, ["zzmasked.service"])
        self.rm_testdir()
    def test_0383(self) -> None:
        """ a PATTERN and --state= narrow together """
        tmp = self.testdir()
        systemctl = self._list_unit_files_setup(tmp)
        systemctl._only_state = ["masked"] # pylint: disable=protected-access
        self.assertEq([item[0] for item in systemctl.list_unit_files_modules("zza*")], [])
        self.assertEq([item[0] for item in systemctl.list_unit_files_modules("zzm*")], ["zzmasked.service"])
        self.rm_testdir()
    def test_0390(self) -> None:
        """ set-environment / get-environment round trip, and the file is kept under
            the runtime directory of the root we were pointed at """
        tmp = self.testdir()
        systemctl = app.Systemctl()
        systemctl._root = tmp # pylint: disable=protected-access
        self.assertEq(systemctl.get_environment_modules("FOO"), "")
        self.assertEq(systemctl.set_environment_modules("FOO=bar"), 0)
        self.assertEq(systemctl.get_environment_modules("FOO"), "bar")
        self.assertEq(os.path.isfile(systemctl.get_environment_file()), True)
        self.assertEq(systemctl.get_environment_file().startswith(tmp), True)
        self.rm_testdir()
    def test_0391(self) -> None:
        """ a second setting joins the first, and unset removes only its own """
        tmp = self.testdir()
        systemctl = app.Systemctl()
        systemctl._root = tmp # pylint: disable=protected-access
        systemctl.set_environment_modules("FOO=bar")
        systemctl.set_environment_modules("BAZ=qux")
        self.assertEq(systemctl.get_environment_modules("FOO"), "bar")
        self.assertEq(systemctl.get_environment_modules("BAZ"), "qux")
        self.assertEq(systemctl.unset_environment_modules("FOO"), 0)
        self.assertEq(systemctl.get_environment_modules("FOO"), "")
        self.assertEq(systemctl.get_environment_modules("BAZ"), "qux")
        self.rm_testdir()
    def test_0392(self) -> None:
        """ a value may contain '=' itself, and bad input is refused instead of
            being stored under a half name """
        tmp = self.testdir()
        systemctl = app.Systemctl()
        systemctl._root = tmp # pylint: disable=protected-access
        self.assertEq(systemctl.set_environment_modules("FOO=a=b=c"), 0)
        self.assertEq(systemctl.get_environment_modules("FOO"), "a=b=c")
        self.assertEq(systemctl.set_environment_modules("NOEQUALSIGN"), 2)
        self.assertEq(systemctl.set_environment_modules(), 1)
        self.assertEq(systemctl.get_environment_modules(), 1)
        self.assertEq(systemctl.unset_environment_modules(), 1)
        self.rm_testdir()
    def test_0393(self) -> None:
        """ unset of something never set is not an error, and reading a runtime
            directory that does not exist yet answers empty rather than failing """
        tmp = self.testdir()
        systemctl = app.Systemctl()
        systemctl._root = tmp # pylint: disable=protected-access
        self.assertEq(os.path.isfile(systemctl.get_environment_file()), False)
        self.assertEq(systemctl.get_environment_modules("NEVERSET"), "")
        self.assertEq(systemctl.unset_environment_modules("NEVERSET"), 0)
        self.rm_testdir()
    def _template_setup(self, tmp: str) -> "app.SystemctlUnitFiles":
        sysd = F"{tmp}/etc/systemd/system"
        os.makedirs(sysd)
        text_file(F"{sysd}/tmpl@.service", """
        [Unit]
        Description = template for %i
        [Service]
        ExecStart = /usr/bin/true %i""")
        unit = app.SystemctlUnitFiles()
        unit._root = tmp # pylint: disable=protected-access
        return unit
    def test_0400(self) -> None:
        """ every instance of a template gets its own conf - they used to share the
            template's object, so the name of the last one loaded won for all """
        tmp = self.testdir()
        unit = self._template_setup(tmp)
        conf_a = unit.load_conf("tmpl@a.service")
        conf_b = unit.load_conf("tmpl@b.service")
        self.assertEq(conf_a.name(), "tmpl@a.service")
        self.assertEq(conf_b.name(), "tmpl@b.service")
        self.assertEq(conf_a is conf_b, False)
        self.rm_testdir()
    def test_0401(self) -> None:
        """ loading a second instance does not rename the first one """
        tmp = self.testdir()
        unit = self._template_setup(tmp)
        conf_a = unit.load_conf("tmpl@a.service")
        self.assertEq(conf_a.name(), "tmpl@a.service")
        unit.load_conf("tmpl@b.service")
        self.assertEq(conf_a.name(), "tmpl@a.service")
        self.rm_testdir()
    def test_0402(self) -> None:
        """ %i expands per instance, and the bare template has no instance at all """
        tmp = self.testdir()
        unit = self._template_setup(tmp)
        conf_a = unit.load_conf("tmpl@a.service")
        conf_b = unit.load_conf("tmpl@b.service")
        self.assertEq(unit.get_Description(conf_a), "template for a")
        self.assertEq(unit.get_Description(conf_b), "template for b")
        conf_t = unit.load_conf("tmpl@.service")
        self.assertEq(unit.get_Description(conf_t), "template for ")
        self.rm_testdir()
    def test_0403(self) -> None:
        """ the state of one instance is not the state of another """
        tmp = self.testdir()
        unit = self._template_setup(tmp)
        conf_a = unit.load_conf("tmpl@a.service")
        conf_b = unit.load_conf("tmpl@b.service")
        conf_a.status = {"ActiveState": "active"}
        self.assertEq(conf_b.status, None)
        self.assertEq(conf_a.status, {"ActiveState": "active"})
        self.rm_testdir()
    def _alias_setup(self, tmp: str) -> "app.SystemctlUnitFiles":
        sysd = F"{tmp}/etc/systemd/system"
        os.makedirs(sysd)
        text_file(F"{sysd}/real1.service", """
        [Unit]
        Description = the real one
        [Service]
        ExecStart = /usr/bin/true""")
        text_file(F"{sysd}/tmpl@.service", """
        [Unit]
        Description = template for %i
        [Service]
        ExecStart = /usr/bin/true""")
        unit = app.SystemctlUnitFiles()
        unit._root = tmp # pylint: disable=protected-access
        return unit
    def test_0410(self) -> None:
        """ a unit file that is a symlink to another unit is an alias of it - asking
            for either name answers about the one that is really there """
        tmp = self.testdir()
        unit = self._alias_setup(tmp)
        os.symlink("real1.service", F"{tmp}/etc/systemd/system/alias1.service")
        self.assertEq(unit.real_unit_name("alias1.service"), "real1.service")
        conf = unit.load_conf("alias1.service")
        self.assertEq(conf.name(), "real1.service")
        self.assertEq(unit.get_Description(conf), "the real one")
        self.rm_testdir()
    def test_0411(self) -> None:
        """ a name that is not a link is not an alias """
        tmp = self.testdir()
        unit = self._alias_setup(tmp)
        self.assertEq(unit.real_unit_name("real1.service"), "real1.service")
        self.rm_testdir()
    def test_0412(self) -> None:
        """ tmpl@one.service -> tmpl@.service is how an instance is enabled, not an
            alias of the template - resolving it that way would hand every instance
            the template's conf and its name """
        tmp = self.testdir()
        unit = self._alias_setup(tmp)
        sysd = F"{tmp}/etc/systemd/system"
        os.symlink("tmpl@.service", F"{sysd}/tmpl@one.service")
        os.symlink("tmpl@.service", F"{sysd}/tmpl@two.service")
        self.assertEq(unit.real_unit_name("tmpl@one.service"), "tmpl@one.service")
        conf1 = unit.load_conf("tmpl@one.service")
        conf2 = unit.load_conf("tmpl@two.service")
        self.assertEq(conf1.name(), "tmpl@one.service")
        self.assertEq(conf2.name(), "tmpl@two.service")
        self.assertEq(unit.get_Description(conf1), "template for one")
        self.assertEq(unit.get_Description(conf2), "template for two")
        self.rm_testdir()
    def test_0413(self) -> None:
        """ a link onto a DIFFERENT template is a real alias, and systemd carries the
            instance across it - other@one.service means tmpl@one.service """
        tmp = self.testdir()
        unit = self._alias_setup(tmp)
        os.symlink("tmpl@.service", F"{tmp}/etc/systemd/system/other@one.service")
        self.assertEq(unit.real_unit_name("other@one.service"), "tmpl@one.service")
        conf = unit.load_conf("other@one.service")
        self.assertEq(unit.get_Description(conf), "template for one")
        self.rm_testdir()
    def test_0414(self) -> None:
        """ an instance link is read from the template it points at, so the drop-ins
            of the template apply to the instance as well """
        tmp = self.testdir()
        unit = self._alias_setup(tmp)
        sysd = F"{tmp}/etc/systemd/system"
        os.makedirs(F"{sysd}/tmpl@.service.d")
        text_file(F"{sysd}/tmpl@.service.d/10-extra.conf", """
        [Service]
        Environment = FROMDROPIN=yes""")
        os.symlink("tmpl@.service", F"{sysd}/tmpl@one.service")
        conf = unit.load_conf("tmpl@one.service")
        self.assertEq(conf.getlist("Service", "Environment", []), ["FROMDROPIN=yes"])
        self.rm_testdir()
    def _status_conf(self, tmp: str, unit: str = "zz1.service") -> Any: # type: ignore[explicit-any]
        sysd = F"{tmp}/etc/systemd/system"
        os.makedirs(sysd)
        text_file(F"{sysd}/{unit}", """
        [Service]
        ExecStart = /usr/bin/true""")
        systemctl = app.Systemctl()
        systemctl._root = tmp # pylint: disable=protected-access
        systemctl.unitfiles._root = tmp # pylint: disable=protected-access
        return systemctl, systemctl.unitfiles.get_conf(unit)
    def test_0420(self) -> None:
        """ the status file must be readable whatever umask we were called with -
            an unreadable one makes a running service look stopped """
        tmp = self.testdir()
        systemctl, conf = self._status_conf(tmp)
        old = os.umask(0o077)
        try:
            systemctl.write_status_from(conf, MainPID=1234)
        finally:
            os.umask(old)
        status_file = systemctl.get_status_file_from(conf)
        mode = os.stat(status_file).st_mode & 0o777
        self.assertEq(mode & 0o044, 0o044, F"mode is {mode:04o}")
        self.rm_testdir()
    def test_0421(self) -> None:
        """ read bits are added, never taken away - a mode widened on purpose stays """
        tmp = self.testdir()
        systemctl, conf = self._status_conf(tmp)
        systemctl.write_status_from(conf, MainPID=1234)
        status_file = systemctl.get_status_file_from(conf)
        os.chmod(status_file, 0o664)
        systemctl.write_status_from(conf, MainPID=1235)
        self.assertEq(os.stat(status_file).st_mode & 0o777, 0o664)
        self.rm_testdir()
    def test_0422(self) -> None:
        """ the status file is our own state, never a symlink - writing through one
            overwrites whatever it points at """
        tmp = self.testdir()
        systemctl, conf = self._status_conf(tmp)
        status_file = systemctl.get_status_file_from(conf)
        os.makedirs(os.path.dirname(status_file), exist_ok=True)
        victim = F"{tmp}/victim.txt"
        text_file(victim, "SECRET\n")
        os.symlink(os.path.abspath(victim), status_file) # must be resolvable
        self.assertEq(os.path.exists(status_file), True) # not a dangling link
        systemctl.write_status_from(conf, MainPID=1234)
        self.assertEq(open(victim).read(), "SECRET\n")
        self.rm_testdir()
    def test_0423(self) -> None:
        """ a read-only command must not truncate a foreign file through a symlink
            either - shutil_truncate runs from is-active and show """
        tmp = self.testdir()
        victim = F"{tmp}/victim.txt"
        text_file(victim, "SECRET\n")
        link = F"{tmp}/link.status"
        os.symlink(os.path.abspath(victim), link)
        self.assertEq(os.path.exists(link), True) # not a dangling link
        try:
            app.shutil_truncate(link)
        except OSError:
            pass
        self.assertEq(open(victim).read(), "SECRET\n")
        self.rm_testdir()
    def test_0424(self) -> None:
        """ a runtime directory of ours must be enterable whatever the umask was """
        tmp = self.testdir()
        folder = F"{tmp}/run/systemd"
        old = os.umask(0o077)
        try:
            app.makedirs_mode(folder)
        finally:
            os.umask(old)
        mode = os.stat(folder).st_mode & 0o777
        self.assertEq(mode & 0o055, 0o055, F"mode is {mode:04o}")
        app.makedirs_mode(folder) # again on an existing directory must not raise
        self.rm_testdir()
    def test_0430(self) -> None:
        """ a status file we cannot read must not be reported as "not running" -
            that is the opposite answer, not a missing one """
        tmp = self.testdir()
        systemctl, conf = self._status_conf(tmp)
        systemctl.write_status_from(conf, MainPID=os.getpid(), AS="active")
        self.assertEq(systemctl.get_active_from(conf), "active")
        status_file = systemctl.get_status_file_from(conf)
        os.chmod(status_file, 0o000)
        conf.status = None # forget what we cached from the readable file
        self.assertEq(systemctl.get_active_from(conf), "unknown")
        self.assertEq(systemctl.get_substate_from(conf), "unknown")
        os.chmod(status_file, 0o644)
        self.rm_testdir()
    def test_0431(self) -> None:
        """ an absent status file is a real answer, not a failure """
        tmp = self.testdir()
        systemctl, conf = self._status_conf(tmp)
        self.assertEq(systemctl.get_active_from(conf), "inactive")
        self.assertEq(conf.state_unreadable, False)
        self.rm_testdir()
    def test_0432(self) -> None:
        """ a fifo at the status path must not block us - open() on one waits for a
            writer forever, which would hang is-active and, on PID 1, survive the
            SIGTERM of a docker stop """
        tmp = self.testdir()
        systemctl, conf = self._status_conf(tmp)
        status_file = systemctl.get_status_file_from(conf)
        os.makedirs(os.path.dirname(status_file), exist_ok=True)
        os.mkfifo(status_file)
        self.assertEq(systemctl.get_active_from(conf), "unknown")
        self.rm_testdir()
    def test_0433(self) -> None:
        """ is_readable_file tells "cannot read" apart from "is not there" """
        tmp = self.testdir()
        systemctl, _ = self._status_conf(tmp)
        missing = F"{tmp}/nosuch.txt"
        self.assertEq(systemctl.is_readable_file(missing), False)
        present = F"{tmp}/present.txt"
        text_file(present, "x\n")
        self.assertEq(systemctl.is_readable_file(present), True)
        os.chmod(present, 0o000)
        conf = app.SystemctlConf(app.UnitConfParser(), "zz9.service")
        self.assertEq(systemctl.is_readable_file(present, conf), False)
        self.assertEq(conf.state_unreadable, True)
        os.chmod(present, 0o644)
        self.rm_testdir()
    def test_0434(self) -> None:
        """ a PIDFile is written by the application and may well be a symlink of its
            own - unlike our status file, that one has to be followed """
        tmp = self.testdir()
        systemctl, _ = self._status_conf(tmp)
        real = F"{tmp}/real.pid"
        text_file(real, "4242\n")
        link = F"{tmp}/link.pid"
        os.symlink(os.path.abspath(real), link)
        self.assertEq(systemctl.is_readable_file(link, None, ours=False), True)
        self.assertEq(systemctl.read_pid_file(link), 4242)
        self.assertEq(systemctl.is_readable_file(link, None, ours=True), False)
        self.rm_testdir()
    def _pidfile_unit(self, tmp: str) -> Any: # type: ignore[explicit-any]
        sysd = F"{tmp}/etc/systemd/system"
        os.makedirs(sysd)
        os.makedirs(F"{tmp}/piddir")
        text_file(F"{sysd}/zzp.service", """
        [Service]
        Type = forking
        PIDFile = /piddir/zzp.pid
        ExecStart = /usr/bin/true""")
        systemctl = app.Systemctl()
        systemctl._root = tmp # pylint: disable=protected-access
        systemctl.unitfiles._root = tmp # pylint: disable=protected-access
        return systemctl, systemctl.unitfiles.get_conf("zzp.service")
    def test_0444(self) -> None:
        """ a PIDFile= we may not even stat does not by itself make the state
            unknown - that file belongs to the application and may well sit behind
            a directory we are not allowed to enter (exim4 keeps /run/exim4 at 0750).
            When we never wrote a state for the unit, it was never started here, and
            that is a complete answer: inactive, the same one root gets. """
        tmp = self.testdir()
        systemctl, conf = self._pidfile_unit(tmp)
        os.chmod(F"{tmp}/piddir", 0o000)
        try:
            self.assertEq(systemctl.get_active_from(conf), "inactive")
            conf.status = None
            self.assertEq(systemctl.get_substate_from(conf), "dead")
        finally:
            os.chmod(F"{tmp}/piddir", 0o755)
        self.rm_testdir()
    def test_0445(self) -> None:
        """ and when we did write a state for it, that state is the answer - a
            running service must not turn into "unknown" just because the pid file
            the application keeps sits in a directory we may not enter """
        tmp = self.testdir()
        systemctl, conf = self._pidfile_unit(tmp)
        systemctl.write_status_from(conf, MainPID=os.getpid()) # a PID that is alive
        conf.status = None
        os.chmod(F"{tmp}/piddir", 0o000)
        try:
            self.assertEq(systemctl.get_active_from(conf), "active")
            conf.status = None
            self.assertEq(systemctl.get_substate_from(conf), "running")
        finally:
            os.chmod(F"{tmp}/piddir", 0o755)
    def test_0440(self) -> None:
        """ the state of a system unit is read from /run, where the system keeps it,
            not from the private tree an unprivileged caller writes into """
        tmp = self.testdir()
        systemctl, conf = self._status_conf(tmp)
        system_dir = F"{tmp}/run"
        os.makedirs(system_dir, exist_ok=True)
        text_file(F"{system_dir}/zz1.service.status", "MainPID=4242\n")
        self.assertEq(systemctl.read_status_file_from(conf), F"{system_dir}/zz1.service.status")
        self.rm_testdir()
    def test_0441(self) -> None:
        """ when nobody privileged keeps state in /run, this script is the manager
            and its own tree is all there is """
        tmp = self.testdir()
        systemctl, conf = self._status_conf(tmp)
        os.makedirs(F"{tmp}/run", exist_ok=True) # exists but holds no state
        self.assertEq(systemctl.read_status_file_from(conf), systemctl.get_status_file_from(conf))
        self.rm_testdir()
    def test_0442(self) -> None:
        """ writing is never redirected - an unprivileged caller must not be sent at
            the system state, it writes into its own tree and fails there or not """
        tmp = self.testdir()
        systemctl, conf = self._status_conf(tmp)
        os.makedirs(F"{tmp}/run", exist_ok=True)
        text_file(F"{tmp}/run/zz1.service.status", "MainPID=4242\n")
        written = systemctl.get_status_file_from(conf)
        self.assertEq(written.endswith("zz1.service.status"), True)
        self.assertEq(systemctl.read_status_file_from(conf), F"{tmp}/run/zz1.service.status")
        self.rm_testdir()
    def test_0443(self) -> None:
        """ a unit that names its own StatusFile= means that path and nothing else """
        tmp = self.testdir()
        sysd = F"{tmp}/etc/systemd/system"
        os.makedirs(sysd)
        text_file(F"{sysd}/zz2.service", """
        [Service]
        StatusFile = /var/lib/zz2.state
        ExecStart = /usr/bin/true""")
        os.makedirs(F"{tmp}/run", exist_ok=True)
        text_file(F"{tmp}/run/zz2.state", "MainPID=4242\n")
        systemctl = app.Systemctl()
        systemctl._root = tmp # pylint: disable=protected-access
        systemctl.unitfiles._root = tmp # pylint: disable=protected-access
        conf = systemctl.unitfiles.get_conf("zz2.service")
        self.assertEq(systemctl.read_status_file_from(conf), F"{tmp}/var/lib/zz2.state")
        self.rm_testdir()
    def _nopidfile_unit(self, tmp: str) -> Any: # type: ignore[explicit-any]
        """ a unit with no PIDFile= at all - there is nobody else to ask, so our own
            state is the only source there is """
        sysd = F"{tmp}/etc/systemd/system"
        os.makedirs(sysd)
        text_file(F"{sysd}/zzq.service", """
        [Service]
        Type = simple
        ExecStart = /usr/bin/true""")
        systemctl = app.Systemctl()
        systemctl._root = tmp # pylint: disable=protected-access
        systemctl.unitfiles._root = tmp # pylint: disable=protected-access
        return systemctl, systemctl.unitfiles.get_conf("zzq.service")
    def test_0446(self) -> None:
        """ unknown is kept for the case it was meant for: there is no PIDFile to
            ask, and our OWN state is what we cannot read """
        tmp = self.testdir()
        systemctl, conf = self._nopidfile_unit(tmp)
        systemctl.write_status_from(conf, MainPID=os.getpid())
        conf.status = None
        status_file = systemctl.get_status_file_from(conf)
        os.chmod(status_file, 0o000)
        try:
            self.assertEq(systemctl.get_active_from(conf), "unknown")
        finally:
            os.chmod(status_file, 0o644)
        self.rm_testdir()
    def test_0448(self) -> None:
        """ ... but when the unit does declare a PIDFile= and that file is absent,
            the application has answered and we do not need our own state at all -
            not even when we cannot read it """
        tmp = self.testdir()
        systemctl, conf = self._pidfile_unit(tmp)
        systemctl.write_status_from(conf, MainPID=os.getpid())
        conf.status = None
        status_file = systemctl.get_status_file_from(conf)
        os.chmod(status_file, 0o000)
        try:
            self.assertEq(systemctl.get_active_from(conf), "inactive")
        finally:
            os.chmod(status_file, 0o644)
        self.rm_testdir()
    def test_0447(self) -> None:
        """ a PIDFile that is simply ABSENT is a different answer from one we may
            not read. Absent means the application says it is not running, and that
            is complete - our own state must not override it, or a service that
            ended by itself gets reported as failed. """
        tmp = self.testdir()
        systemctl, conf = self._pidfile_unit(tmp)
        dead = os.fork()
        if not dead:
            os._exit(0) # pylint: disable=protected-access
        os.waitpid(dead, 0)
        systemctl.write_status_from(conf, MainPID=dead)
        conf.status = None
        self.assertEq(systemctl.get_active_from(conf), "inactive")
        self.assertEq(systemctl.get_substate_from(conf), "dead")
        self.rm_testdir()
    def test_0490(self) -> None:
        """ a PIDFile= we may not stat is the normal case for an unprivileged
            caller - exim4 keeps /run/exim4 at 0750 - and we answer it correctly
            from our own state. Saying so at WARNING on every single query buries
            the warnings that do mean something. """
        tmp = self.testdir()
        systemctl, conf = self._pidfile_unit(tmp)
        os.chmod(F"{tmp}/piddir", 0o000)
        logged = []
        warning = app.logg.warning
        app.logg.warning = lambda fmt, *a: logged.append(fmt % a) # type: ignore[method-assign,assignment]
        try:
            pid_file = F"{tmp}/piddir/zzp.pid"
            self.assertFalse(systemctl.is_readable_file(pid_file, conf, ours=False))
        finally:
            app.logg.warning = warning # type: ignore[method-assign]
            os.chmod(F"{tmp}/piddir", 0o755)
        self.assertEqual(logged, [])
        self.assertTrue(conf.state_unreadable) # still recorded, just not shouted
        self.rm_testdir()
    def test_0491(self) -> None:
        """ ... but a file of our own that we may not stat is a real surprise and
            keeps its warning """
        tmp = self.testdir()
        systemctl, conf = self._pidfile_unit(tmp)
        os.chmod(F"{tmp}/piddir", 0o000)
        logged = []
        warning = app.logg.warning
        app.logg.warning = lambda fmt, *a: logged.append(fmt % a) # type: ignore[method-assign,assignment]
        try:
            self.assertFalse(systemctl.is_readable_file(F"{tmp}/piddir/ours.state", conf))
        finally:
            app.logg.warning = warning # type: ignore[method-assign]
            os.chmod(F"{tmp}/piddir", 0o755)
        self.assertEqual(len(logged), 1)
        self.assertTrue(logged[0].startswith("can not stat"))
        self.rm_testdir()
    def _killmode_unit(self, tmp, killmode, mainpid, pidlist, dies = None, timeout = 4):
        """ do_kill_unit_from is driven by pidlist_of() and pid_exists(), so a fake
            process table is enough to observe which pids it signals and which ones
            it waits for. 'dies' are the pids that react to the friendly signal, the
            others only to SIGKILL. Returns (systemctl, conf, alive, killed). """
        sysd = F"{tmp}/etc/systemd/system"
        os.makedirs(sysd)
        text_file(F"{sysd}/zzk.service", F"""
        [Service]
        ExecStart = /usr/bin/true
        KillMode = {killmode}
        TimeoutStopSec = {timeout}""")
        systemctl = app.Systemctl()
        systemctl._root = tmp # pylint: disable=protected-access
        systemctl.unitfiles._root = tmp # pylint: disable=protected-access
        conf = systemctl.unitfiles.get_conf("zzk.service")
        systemctl.write_status_from(conf, MainPID=mainpid)
        alive = set(pidlist)
        obedient = set([mainpid] if dies is None else dies)
        killed = []
        def kill_pid(pid, kill_signal = None):
            killed.append((pid, kill_signal))
            if pid in obedient or kill_signal == signal.SIGKILL:
                alive.discard(pid)
            return pid not in alive
        systemctl.pidlist_of = lambda pid: list(pidlist) # type: ignore[method-assign]
        systemctl._kill_pid = kill_pid # type: ignore[method-assign] # pylint: disable=protected-access
        return systemctl, conf, alive, killed
    def _fake_pids(self, alive):
        """ patches the module-wide process lookups against a fake process table """
        pid_exists, pid_zombie = app.pid_exists, app.pid_zombie
        app.pid_exists = lambda pid: pid in alive
        app.pid_zombie = lambda pid: False
        return pid_exists, pid_zombie
    def _real_pids(self, saved):
        app.pid_exists, app.pid_zombie = saved
    def test_0450(self) -> None:
        """ KillMode=control-group - all remaining processes of the unit are killed """
        self.assertEqual(app.killmode_pidlist("control-group", 11, [11, 22, 33]), [11, 22, 33])
        self.assertEqual(app.killmode_pidlist("control-group", 11, [11, 22, 33], sigkill=True), [11, 22, 33])
    def test_0451(self) -> None:
        """ KillMode=process - only the main process itself is killed, and the later
            SIGKILL does not widen that (systemd.kill(5)) """
        self.assertEqual(app.killmode_pidlist("process", 11, [11, 22, 33]), [11])
        self.assertEqual(app.killmode_pidlist("process", 11, [11, 22, 33], sigkill=True), [11])
    def test_0452(self) -> None:
        """ KillMode=mixed - SIGTERM goes to the main process while the subsequent
            SIGKILL is sent to all remaining processes (systemd.kill(5)) """
        self.assertEqual(app.killmode_pidlist("mixed", 11, [11, 22, 33]), [11])
        self.assertEqual(app.killmode_pidlist("mixed", 11, [11, 22, 33], sigkill=True), [11, 22, 33])
    def test_0453(self) -> None:
        """ KillMode=none - no process is killed, only the stop command is executed """
        self.assertEqual(app.killmode_pidlist("none", 11, [11, 22, 33]), [])
        self.assertEqual(app.killmode_pidlist("none", 11, [11, 22, 33], sigkill=True), [])
    def test_0454(self) -> None:
        """ KillMode=process must not wait for processes it never signalled. Debian
            ships ssh.service, cron.service and puppet.service that way so that the
            established sessions survive - waiting for them burns TimeoutStopSec on
            every shutdown and the container ends up being SIGKILLed from outside. """
        tmp = self.testdir()
        systemctl, conf, alive, killed = self._killmode_unit(tmp, "process", 11, [11, 22])
        saved = self._fake_pids(alive)
        try:
            started = time.monotonic()
            done = systemctl.do_kill_unit_from(conf)
            lapse = time.monotonic() - started
        finally:
            self._real_pids(saved)
        self.assertEqual(killed, [(11, signal.SIGTERM)])
        self.assertEqual(alive, set([22])) # the session process is left alone
        self.assertTrue(done)
        self.assertLess(lapse, 2) # not TimeoutStopSec=4
        self.rm_testdir()
    def test_0455(self) -> None:
        """ KillMode=none kills nothing at all - not even the main process """
        tmp = self.testdir()
        systemctl, conf, alive, killed = self._killmode_unit(tmp, "none", 11, [11, 22])
        saved = self._fake_pids(alive)
        try:
            started = time.monotonic()
            done = systemctl.do_kill_unit_from(conf)
            lapse = time.monotonic() - started
        finally:
            self._real_pids(saved)
        self.assertEqual(killed, [])
        self.assertEqual(alive, set([11, 22]))
        self.assertTrue(done)
        self.assertLess(lapse, 2)
        self.rm_testdir()
    def test_0456(self) -> None:
        """ KillMode=control-group stays as it was - every process of the unit gets
            the kill signal """
        tmp = self.testdir()
        systemctl, conf, alive, killed = self._killmode_unit(tmp, "control-group", 11, [11, 22], dies=[11, 22])
        saved = self._fake_pids(alive)
        try:
            started = time.monotonic()
            done = systemctl.do_kill_unit_from(conf)
            lapse = time.monotonic() - started
        finally:
            self._real_pids(saved)
        self.assertEqual(killed, [(11, signal.SIGTERM), (22, signal.SIGTERM)])
        self.assertEqual(alive, set())
        self.assertTrue(done)
        self.assertLess(lapse, 2)
        self.rm_testdir()
    def test_0458(self) -> None:
        """ KillMode=control-group does wait for the other processes as well, and it
            escalates to SIGKILL for the ones that did not react """
        tmp = self.testdir()
        systemctl, conf, alive, killed = self._killmode_unit(tmp, "control-group", 11, [11, 22], timeout=1)
        saved = self._fake_pids(alive)
        try:
            started = time.monotonic()
            done = systemctl.do_kill_unit_from(conf)
            lapse = time.monotonic() - started
        finally:
            self._real_pids(saved)
        self.assertEqual(killed, [(11, signal.SIGTERM), (22, signal.SIGTERM), (22, signal.SIGKILL)])
        self.assertTrue(done)
        self.assertGreaterEqual(lapse, 1) # it did wait for TimeoutStopSec
        self.rm_testdir()
    def test_0457(self) -> None:
        """ SendSIGHUP follows the KillMode set, not the whole process list - systemd
            sends it right after the kill signal, to the same processes """
        tmp = self.testdir()
        systemctl, conf, alive, killed = self._killmode_unit(tmp, "process", 11, [11, 22])
        conf.set("Service", "SendSIGHUP", "yes")
        saved = self._fake_pids(alive)
        try:
            systemctl.do_kill_unit_from(conf)
        finally:
            self._real_pids(saved)
        self.assertEqual(killed, [(11, signal.SIGTERM), (11, signal.SIGHUP)])
        self.rm_testdir()
    def test_0460(self) -> None:
        """ having no unit waiting for a restart is the healthy state of the init
            loop, not an error. restart_failed_units() runs on every tick, so the
            flag it raised here made the manager exit 1 after a clean shutdown. """
        tmp = self.testdir()
        sysd = F"{tmp}/etc/systemd/system"
        os.makedirs(sysd)
        text_file(F"{sysd}/zzr.service", """
        [Service]
        ExecStart = /usr/bin/true
        Restart = no""")
        systemctl = app.Systemctl()
        systemctl._root = tmp # pylint: disable=protected-access
        systemctl.unitfiles._root = tmp # pylint: disable=protected-access
        self.assertEqual(systemctl.error, app.NOT_A_PROBLEM)
        done = systemctl.restart_failed_units(["zzr.service"])
        self.assertEqual(done, [])
        self.assertEqual(systemctl.error, app.NOT_A_PROBLEM)
        self.rm_testdir()
    def test_0461(self) -> None:
        """ ... and it stays that way over the repeated ticks of the init loop """
        tmp = self.testdir()
        sysd = F"{tmp}/etc/systemd/system"
        os.makedirs(sysd)
        text_file(F"{sysd}/zzr.service", """
        [Service]
        ExecStart = /usr/bin/true
        Restart = no""")
        systemctl = app.Systemctl()
        systemctl._root = tmp # pylint: disable=protected-access
        systemctl.unitfiles._root = tmp # pylint: disable=protected-access
        for _ in range(3):
            systemctl.restart_failed_units(["zzr.service"])
        self.assertEqual(systemctl.error, app.NOT_A_PROBLEM)
        self.rm_testdir()
    def test_0310(self) -> None:
        tmp = self.testdir()
        svc1 = "test1.service"
        text_file(F"{tmp}/{svc1}", """
        [Service]
        ExecStart = /usr/bin/false""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        mode = "check"
        want = ["/usr/bin/false"]
        conf = unit.get_conf(svc1)
        env = unit.get_env(conf)
        for cmd in conf.getlist("Service", "ExecStart", []):
            exe, newcmd = unit.expand_cmd(cmd, env, conf)
            logg.info("[%s] %s", execmode(exe), app.shell_cmd(newcmd))
            self.assertEqual(want, newcmd)
            self.assertEqual(mode, execmode(exe))
        self.rm_testdir()
    def test_0311(self) -> None:
        tmp = self.testdir()
        svc1 = "test1.service"
        text_file(F"{tmp}/{svc1}", """
        [Service]
        ExecStart = -/usr/bin/false""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        mode = "nocheck"
        want = ["/usr/bin/false"]
        conf = unit.get_conf(svc1)
        env = unit.get_env(conf)
        for cmd in conf.getlist("Service", "ExecStart", []):
            exe, newcmd = unit.expand_cmd(cmd, env, conf)
            logg.info("[%s] %s", execmode(exe), app.shell_cmd(newcmd))
            self.assertEqual(want, newcmd)
            self.assertEqual(mode, execmode(exe))
        self.rm_testdir()
    def test_0312(self) -> None:
        tmp = self.testdir()
        svc1 = "test1.service"
        text_file(F"{tmp}/{svc1}", """
        [Service]
        ExecStart = -!/usr/bin/false""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        mode = "nocheck+nouser"
        want = ["/usr/bin/false"]
        conf = unit.get_conf(svc1)
        env = unit.get_env(conf)
        for cmd in conf.getlist("Service", "ExecStart", []):
            exe, newcmd = unit.expand_cmd(cmd, env, conf)
            logg.info("[%s] %s", execmode(exe), app.shell_cmd(newcmd))
            self.assertEqual(want, newcmd)
            self.assertEqual(mode, execmode(exe))
        self.rm_testdir()
    def test_0313(self) -> None:
        tmp = self.testdir()
        svc1 = "test1.service"
        text_file(F"{tmp}/{svc1}", """
        [Service]
        ExecStart = !-/usr/bin/false""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        mode = "nocheck+nouser"
        want = ["/usr/bin/false"]
        conf = unit.get_conf(svc1)
        env = unit.get_env(conf)
        for cmd in conf.getlist("Service", "ExecStart", []):
            exe, newcmd = unit.expand_cmd(cmd, env, conf)
            logg.info("[%s] %s", execmode(exe), app.shell_cmd(newcmd))
            self.assertEqual(want, newcmd)
            self.assertEqual(mode, execmode(exe))
        self.rm_testdir()
    def test_0314(self) -> None:
        tmp = self.testdir()
        svc1 = "test1.service"
        text_file(F"{tmp}/{svc1}", """
        [Service]
        ExecStart = !!-/usr/bin/false""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        mode = "nocheck+nouser"
        want = ["/usr/bin/false"]
        conf = unit.get_conf(svc1)
        env = unit.get_env(conf)
        for cmd in conf.getlist("Service", "ExecStart", []):
            exe, newcmd = unit.expand_cmd(cmd, env, conf)
            logg.info("[%s] %s", execmode(exe), app.shell_cmd(newcmd))
            self.assertEqual(want, newcmd)
            self.assertEqual(mode, execmode(exe))
        self.rm_testdir()
    def test_0315(self) -> None:
        tmp = self.testdir()
        svc1 = "test1.service"
        text_file(F"{tmp}/{svc1}", """
        [Service]
        ExecStart = -+/usr/bin/false""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        mode = "nocheck+nouser"
        want = ["/usr/bin/false"]
        conf = unit.get_conf(svc1)
        env = unit.get_env(conf)
        for cmd in conf.getlist("Service", "ExecStart", []):
            exe, newcmd = unit.expand_cmd(cmd, env, conf)
            logg.info("[%s] %s", execmode(exe), app.shell_cmd(newcmd))
            self.assertEqual(want, newcmd)
            self.assertEqual(mode, execmode(exe))
        self.rm_testdir()
    def test_0316(self) -> None:
        tmp = self.testdir()
        svc1 = "test1.service"
        text_file(F"{tmp}/{svc1}", """
        [Service]
        ExecStart = +-/usr/bin/false""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        mode = "nocheck+nouser"
        want = ["/usr/bin/false"]
        conf = unit.get_conf(svc1)
        env = unit.get_env(conf)
        for cmd in conf.getlist("Service", "ExecStart", []):
            exe, newcmd = unit.expand_cmd(cmd, env, conf)
            logg.info("[%s] %s", execmode(exe), app.shell_cmd(newcmd))
            self.assertEqual(want, newcmd)
            self.assertEqual(mode, execmode(exe))
        self.rm_testdir()
    def test_0317(self) -> None:
        tmp = self.testdir()
        svc1 = "test1.service"
        text_file(F"{tmp}/{svc1}", """
        [Service]
        ExecStart = +:/usr/bin/false""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        mode = "check+nouser+noexpand"
        want = ["/usr/bin/false"]
        conf = unit.get_conf(svc1)
        env = unit.get_env(conf)
        for cmd in conf.getlist("Service", "ExecStart", []):
            exe, newcmd = unit.expand_cmd(cmd, env, conf)
            logg.info("[%s] %s", execmode(exe), app.shell_cmd(newcmd))
            self.assertEqual(want, newcmd)
            self.assertEqual(mode, execmode(exe))
        self.rm_testdir()
    def test_0318(self) -> None:
        tmp = self.testdir()
        svc1 = "test1.service"
        text_file(F"{tmp}/{svc1}", """
        [Service]
        ExecStart = +@/usr/bin/true /usr/bin/false""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        mode = "check+nouser+argv0"
        want = ["/usr/bin/true"] # not false
        conf = unit.get_conf(svc1)
        env = unit.get_env(conf)
        for cmd in conf.getlist("Service", "ExecStart", []):
            exe, newcmd = unit.expand_cmd(cmd, env, conf)
            logg.info("[%s] %s", execmode(exe), app.shell_cmd(newcmd))
            self.assertEqual(want, newcmd)
            self.assertEqual(mode, execmode(exe))
        self.rm_testdir()
    def test_0319(self) -> None:
        tmp = self.testdir()
        svc1 = "test1.service"
        text_file(F"{tmp}/{svc1}", """
        [Service]
        ExecStart = |@/usr/bin/true /usr/bin/false""")
        unit = app.SystemctlUnitFiles()
        unit.add_unit_file(svc1, F"{tmp}/{svc1}")
        mode = "check+argv0" # pipe is ignored
        want = ["/usr/bin/true"] # not false
        conf = unit.get_conf(svc1)
        env = unit.get_env(conf)
        for cmd in conf.getlist("Service", "ExecStart", []):
            exe, newcmd = unit.expand_cmd(cmd, env, conf)
            logg.info("[%s] %s", execmode(exe), app.shell_cmd(newcmd))
            self.assertEqual(want, newcmd)
            self.assertEqual(mode, execmode(exe))
        self.rm_testdir()
    def test_0320(self) -> None:
        tmp = self.testdir()
        svc1 = F"{tmp}/etc/systemd/system/test1.service"
        svc2 = F"{tmp}/etc/systemd/system/test2.service"
        os.makedirs(os.path.dirname(svc1))
        text_file(svc1, """
        [Service]
        ExecStart = /usr/bin/false""")
        text_file(svc2, """
        [Service]
        ExecStartPre = /usr/bin/true
        .include test1.service""")
        systemctl = app.Systemctl(tmp)
        found = systemctl.unitfiles.scan_unit_files()
        logg.info("found %s", found)
        self.assertEq(found, ["test2.service", "test1.service"])
        conf = systemctl.unitfiles.get_conf("test2.service")
        have = conf.get("Service", "ExecStartPre", "")
        logg.info("have %s", have)
        self.assertEq(have, "/usr/bin/true")
        have = conf.get("Service", "ExecStart", "")
        logg.info("have %s", have)
        self.assertEq(have, "/usr/bin/false")
    def test_0321(self) -> None:
        tmp = self.testdir()
        svc1 = F"{tmp}/etc/systemd/system/test1.service"
        svc2 = F"{tmp}/etc/systemd/system/test1.service.d/extra.conf"
        os.makedirs(os.path.dirname(svc1))
        text_file(svc1, """
        [Service]
        ExecStart = /usr/bin/false""")
        text_file(svc2, """
        [Service]
        ExecStartPre = /usr/bin/true""")
        systemctl = app.Systemctl(tmp)
        found = systemctl.unitfiles.scan_unit_files()
        logg.info("found %s", found)
        self.assertEq(found, ["test1.service"])
        conf = systemctl.unitfiles.get_conf("test1.service")
        have = conf.get("Service", "ExecStartPre", "")
        logg.info("have %s", have)
        self.assertEq(have, "/usr/bin/true")
        have = conf.get("Service", "ExecStart", "")
        logg.info("have %s", have)
        self.assertEq(have, "/usr/bin/false")
    def test_0322(self) -> None:
        """ same as test_373 but using Unitfiles """
        tmp = self.testdir()
        log1 = "test1.log"
        log_file1 = F"{tmp}/{log1}"
        text_file(log_file1, """
        info
        here""")
        tail_cmd = F"{tmp}/tail.py"
        shell_file(tail_cmd, """
        #!/usr/bin/env python3
        from optparse import OptionParser
        cmdline = OptionParser("%prog")
        cmdline.add_option("-F", "--follow", action="store_true")
        cmdline.add_option("-n", "--lines", metavar="lines")
        opt, args = cmdline.parse_args()
        assert args
        print(open(args[0]).read())
        """)
        app.logg.info("======== lines")
        files = app.SystemctlUnitFiles(tmp)
        journal = app.SystemctlJournal(files)
        journal.exec_spawn = True
        journal.tail_cmds = [tail_cmd]
        x = journal.tail_log_file(log_file1, 1)
        self.assertEq(x, 0)
        app.logg.info("======== follow")
        files = app.SystemctlUnitFiles(tmp)
        journal = app.SystemctlJournal(files)
        journal.exec_spawn = True
        journal.tail_cmds = [tail_cmd]
        x = journal.tail_log_file(log_file1, 1, True)
        self.assertEq(x, 0)
        app.logg.info("======== cat")
        journal = app.SystemctlJournal(files)
        journal.exec_spawn = True
        journal.no_pager = True
        journal.less_cmds = [tail_cmd]
        x = journal.tail_log_file(log_file1)
        self.assertEq(x, 0)
        app.logg.info("======== less")
        journal = app.SystemctlJournal(files)
        journal.exec_spawn = True
        journal.less_cmds = journal.cat_cmds
        x = journal.tail_log_file(log_file1)
        self.assertEq(x, 0)
        app.logg.info("======== no less")
        journal = app.SystemctlJournal(files)
        journal.exec_spawn = True
        journal.less_cmds = []
        x = journal.tail_log_file(log_file1)
        self.assertEq(x, 1)
        app.logg.info("======== no cat")
        journal = app.SystemctlJournal(files)
        journal.exec_spawn = True
        journal.cat_cmds = []
        journal.no_pager = True
        x = journal.tail_log_file(log_file1)
        self.assertEq(x, 1)
        app.logg.info("======== no tail")
        journal = app.SystemctlJournal(files)
        journal.exec_spawn = True
        journal.tail_cmds = []
        x = journal.tail_log_file(log_file1, 1)
        self.assertEq(x, 1)
        app.logg.info("======== no follow")
        journal = app.SystemctlJournal(files)
        journal.exec_spawn = True
        journal.tail_cmds = []
        x = journal.tail_log_file(log_file1, 1, True)
        self.assertEq(x, 1)
        app.logg.info("======== DONE")
    def test_0323(self) -> None:
        """ adding to test_273 but using Systemctl """
        tmp = self.testdir()
        svc1 = F"{tmp}/etc/systemd/system/test1.service"
        os.makedirs(os.path.dirname(svc1))
        text_file(svc1, """
        [Service]
        ExecStart = |@/usr/bin/true /usr/bin/false""")
        systemctl = app.Systemctl(tmp)
        conf = systemctl.unitfiles.get_conf("test1.service")
        log_file1 = systemctl.journal.get_log_from(conf)
        text_file(log_file1, """
        info
        here""")
        tail_cmd = F"{tmp}/tail.py"
        shell_file(tail_cmd, """
        #!/usr/bin/env python3
        from optparse import OptionParser
        cmdline = OptionParser("%prog")
        cmdline.add_option("-F", "--follow", action="store_true")
        cmdline.add_option("-n", "--lines", metavar="lines")
        opt, args = cmdline.parse_args()
        assert args
        print(open(args[0]).read())
        """)
        systemctl.journal.tail_cmds = [tail_cmd]
        systemctl.journal.less_cmds = [tail_cmd]
        systemctl.journal.cat_cmds = [tail_cmd]
        systemctl.journal.exec_spawn = True
        app.logg.info("======== less")
        systemctl.log_units(["test1.service"])
        app.logg.info("======== lines")
        systemctl.log_units(["test1.service"], 100)
        app.logg.info("======== follow")
        systemctl.log_units(["test1.service"], 100, True)
        app.logg.info("======== cat")
        systemctl.journal.no_pager = True
        systemctl.log_units(["test1.service"])
        app.logg.info("======== module")
        systemctl.log_modules("test1")
        app.logg.info("======== DONE")

if __name__ == "__main__":
    # unittest.main()
    suite = unittest.TestSuite()
    if not cmdline_args:
        cmdline_args = ["test_*"]
    for arg in cmdline_args:
        for classname in sorted(globals()):
            if not classname.endswith("Test"):
                continue
            testclass = globals()[classname]
            for method in sorted(dir(testclass)):
                if arg.endswith("/"):
                    arg = arg[:-1]
                if "*" not in arg:
                    arg += "*"
                if len(arg) > 2 and arg[1] == "_":
                    arg = "test" + arg[1:]
                if fnmatch(method, arg):
                    suite.addTest(testclass(method))
    # select runner
    xmlresults = None
    if opt.xmlresults:
        if os.path.exists(opt.xmlresults):
            os.remove(opt.xmlresults)
        xmlresults = open(opt.xmlresults, "w")
        logg.info("xml results into %s", opt.xmlresults)
    if not logfile:
        if xmlresults:
            import xmlrunner # type: ignore[import-error,import-untyped,unused-ignore] # pylint: disable=import-error
            TestRunner = xmlrunner.XMLTestRunner
            testresult = TestRunner(xmlresults, verbosity=opt.verbose).run(suite)
        else:
            TestRunner = unittest.TextTestRunner
            testresult = TestRunner(verbosity=opt.verbose, failfast=opt.failfast).run(suite)
    else:
        TestRunner = unittest.TextTestRunner
        if xmlresults:
            import xmlrunner # type: ignore[import-error,import-untyped,unused-ignore] # pylint: disable=import-error
            TestRunner = xmlrunner.XMLTestRunner
        testresult = TestRunner(logfile.stream, verbosity=opt.verbose).run(suite) # type: ignore[import-error,unused-ignore]
    if not testresult.wasSuccessful():
        sys.exit(1)
