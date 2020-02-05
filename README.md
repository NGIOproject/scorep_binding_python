# Score-P Python
This repository provides a module that allows tracing of python scripts using [Score-P](http://www.vi-hps.org/projects/score-p/).

This software was extended as part of the EC H2020 funded project NEXTGenIO (Project ID: 671951) http://www.nextgenio.eu.

# Requirements
* CMAKE
* Score-P
* Python Developer Libraries aka python-dev
* Optional: MPI

# Installation
**You must ensure that the "bin" folder of the scorep installation is in the $PATH**

Create build folder:
```
> mkdir BUILD && cd BUILD
```
Run CMAKE like:
```
> cmake .. -DCMAKE_INSTALL_PREFIX=/path/to/install
```
The compiler can be changed using CMAKE variables, e.g. the Intel Compiler
```bash
> cmake .. -DCMAKE_CXX_COMPILER=icpc -DCMAKE_C_COMPILER=icc -DCMAKE_INSTALL_PREFIX=/path/to/install
```
Build and install:
```
> make && make install
```
Finally, the `PYTHONPATH` and `LD_LIBRARY_PATH` must be set, like:
```bash
> scorep_python_dir=/path/to/install
> python_version=$(python -c 'import platform as p; print("{}.{}".format(p.sys.version_info.major,p.sys.version_info.minor))')
> export PYTHONPATH=$scorep_python_dir/lib/python$python_version/site-packages
> export LD_LIBRARY_PATH=$PYTHONPATH/scorep:$LD_LIBRARY_PATH
```

# Usage
Before using these bindings, please ensure that you have installed Score-P with shared libraries.(`configure --enable-shared`)
This tracing tool requires that you preload Score-P libraries before running the tool.
Since Score-P 4.0, Score-P provides a command for generating and printing preload libraries.
For older Score-P installations use [scorep_preload](https://github.com/harryherold/scorep_preload).
Following examples show how to preload Score-P libraries using the built-in tool `scorep-preload-init`.

## Preloading Score-P libraries
Create the preload libraries in your application folder:
```bash
> cd path/to/app
> ld_preload=$(scorep-preload-init --user --io=runtime:posix --value-only $PWD/app)
scorep-preload-init: warning: option not suitable for uninstrumented applications: '--user'
```
`scorep-preload-init` takes the same program arguments as the `scorep` instrumenter. `--value-only` is an option of `scorep-preload-init` and just prints the libraries which should be preloaded. In this example, we instrumented POSIX I/O operations. `--user` was used to enable user instrumentation because the Score-P Python bindings make use of them. If let out `--user` in this example, we will only record POSIX operation. Please ignore the warning from `scorep-preload-init`.

Some runtimes like `mpirun` using internally progress threads which may crash the measurement if they are not mentioned in the instrumentation.
In these cases just add the pthread wrapping for such an mpi4py example:
```bash
> ld_preload=$(scorep-preload-init --user              \
                                    --io=runtime:posix \
                                    --thread=pthread   \
                                    --mpp=mpi --value-only $PWD/app)
```
## Running the application
A serial Python application can be run like:
```bash
> LD_PRELOAD=$ld_preload python -m scorep foo.py
```
*Please use our recommended workflow for tracing (described at the end of the document).*

For running MPI applications, please use the export mechanism of the runtime (openmpi):
```bash
> mpirun -np 4 -x LD_PRELOAD=$ld_preload python -m scorep parallel_foo.py
```
Or SLURM
```bash
> srun -n 4 --export=ALL,LD_PRELOAD=$ld_preload python -m scorep parallel_foo.py
```

The example folder contains a little script (`python_tracing.sh`) which I wrote for my own python development. This script sets env. variable, generates the preload libraries and runs a given application. Just set `scorep_python_dir` in the script and run:
```bash
./python_tracing.sh python -u -m scorep flupp.py
```
The usual Score-P environment variables will be respected. Please have a look at:
* [www.vi-hps.org](http://www.vi-hps.org/projects/score-p/)
* [Score-P Documentation](https://silc.zih.tu-dresden.de/scorep-current/pdf/scorep.pdf)

# User instrumentation

In some cases, the user might want to define a region, log some parameters, or just disable tracing for a certain area. To do so the module implements a few functions:

```
scorep.user.region_begin(name)
scorep.user.region_end(name)
```

These functions allow the definition of user regions. `name` defines the name of a region. Each `user.region_begin` shall have a corresponding call to `user.region_end`.


```
scorep.user.enable_recording()
scorep.user.disable_recording()
```

These functions allow enabling and disabling of the tracing.

```
scorep.user.parameter_int(name, val)
scorep.user.parameter_uint(name, val)
scorep.user.parameter_string(name, string)
```

These functions allow passing user parameters to Score-P. These parameters can be int, uint and string. `name` defines the name of the parameter, while `val` or `string` defines the value that is passed to Score-P.

# Trouble
**Python Multiprocessing**

 Score-P does currently not support any non MPI or non SHMEM communication. So the different processes will not know from each other. You might want to take a look to https://mpi4py.readthedocs.io/en/stable/mpi4py.futures.html .

# Recommended Workflow
Our workflow contains these basic steps:

**1.) Create a Profile to determine the memory consumption of the trace:**
```bash
> export SCOREP_EXPERIMENT_DIRECTORY=$PWD/trace
> LD_PRELOAD=$ld_preload python -m scorep foo.py
```
The profile of the run is placed in `SCOREP_EXPERIMENT_DIRECTORY` like
```bash
> ls $SCOREP_EXPERIMENT_DIRECTORY
MANIFEST.md  profile.cubex  scorep.cfg
```
The memory consumption can be computed using the tool `scorep-score` (its included in the basic Score-P installation):
```bash
> scorep-score $SCOREP_EXPERIMENT_DIRECTORY/profile.cubex
Estimated aggregate size of event trace:                   573kB
Estimated requirements for largest trace buffer (max_buf): 573kB
Estimated memory requirements (SCOREP_TOTAL_MEMORY):       4097kB
(hint: When tracing set SCOREP_TOTAL_MEMORY=4097kB to avoid intermediate flushes
 or reduce requirements using USR regions filters.)

flt     type max_buf[B] visits time[s] time[%] time/visit[us]  region
         ALL    585,893 20,135    0.73   100.0          36.14  ALL
         USR    433,524 16,674    0.59    80.9          35.32  USR
          IO     98,872  1,404    0.01     1.2           6.05  IO
         COM     53,456  2,056    0.08    10.4          36.95  COM
      SCOREP         41      1    0.05     7.5       54365.23  SCOREP
```
`scorep-score` reports a total memory consumption of 4097kB per process.

**2.) Trace the application:**

Now the memory consumption can be set for the tracing:

```bash
> LD_PRELOAD=$ld_preload SCOREP_TOTAL_MEMORY=4097kB SCOREP_ENABLE_TRACING=true python -m scorep foo.py
```
After the run there should be an OTF2 trace in the folder:
```bash
> ls $SCOREP_EXPERIMENT_DIRECTORY
MANIFEST.md  profile.cubex  scorep.cfg  traces  traces.def  traces.otf2
```
If the memory consumption is too high please provide a filter. For that take a look at the Score-P manual.
