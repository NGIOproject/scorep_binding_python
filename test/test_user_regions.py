import scorep.user
import os


def foo():
    scorep.user.region_begin("test_region")
    print("hello world")
    scorep.user.region_end("test_region")


foo()
