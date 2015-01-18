# pyparams
A parameter parsing library for Python: One simple to use module to:

- Define your program's parameters.
- Define each parameter's type, default values and some basic validity
  checking.
- Define each parameter's command line option, config file and environment
  variable equivalent.
- Sit back, relax: Let pyparams do the parsing of environment variables,
  config files and command line parameters for you.
  
## Overview
This module uses a single parameter definition to define and initialize
configuration parameters for a program. Without having to write any additional
code, it gives you access to parameters for your program, which are taken from
config files, environment variables or command line options.

The parameter values are taken (in that order) from:

    1. defined default values
    2. a configuration file
    3. environment variables
    4. command line options

## Defining your configuration
To allow pyparams to read and parse your program's parameters for you, you need
to define a configuration specification.

A full config definition may look like this. Comments are inserted to explain
various features:

```
CONF = Conf(
    # Specify the default name of your project's config file.
    default_conf_file_name     = "myproject-params.conf",

    # Specify any locations (paths) where we should look for the config file
    # in the specified order. By default it looks in the current directory,
    # the user's home directory and the /etc/ directory. In the example below
    # we are just looking in the current directory and /etc.
    default_conf_file_locations = [ "", "/etc/" ],

    # Specify a prefix, which is used to identify any environment variables,
    # which are used to set parameters for your project. The full name of
    # the environment variable is the defined prefix plus the 'conffile'
    # portion of the parameter specification (see below). By default, there
    # is no prefix defined.
    default_env_prefix         = "MYPROJECT_",

    # Specify whether we allow values to remain unset. Note that a defition
    # of None for the default value just means that no default was provided.
    default_allow_unset_values = True,

    # Specify the actual parameters. For each parameter we define a name (the
    # key in the dictionary) as well as a specification dictionary. The spec
    # dictionary can contain the following values (some are optional):
    #
    # - default:        The default value for the parameter, or None (no
    #                   default defined).
    # - allowed_values: A list of pemissible values for this parameter.
    # - allowed_range:  A dictionary containing a min and max value for the
    #                   parameter.
    # - conffile:       The name of the parameter in the configuration file.
    #                   This is also used to construct the name as environment
    #                   variable, by pre-pending the env-prefix to this name.
    #                   If not defined, pyparams will automatically create
    #                   the conffile name for you by capitalizing the parameter
    #                   name (and replacing any '-' with '_'). If you don't
    #                   want a conffile (and environment variable) equivalent,
    #                   set this to None.
    # - param_type:     The allowed type of the parameter, either
    #                   PARAM_TYPE_STR (the default), PARAM_TYPE_INT or
    #                   PARAM_TYPE_BOOL.
    # - cmd_line:       A tuple containing the short-option letter and the
    #                   lon-option name. Either one can be left None, or the
    #                   entire cmd_line value can be omitted. In the latter
    #                   case, pyparams automatically constructs the cmd_line
    #                   tuple for you, using the first letter (short) and the
    #                   full name (long) of the parameter name. If you don't
    #                   want to have any command line equivalent for the
    #                   parameter, set this to None.
    param_dict = {
        "foo" : {
            "default"        : "some-value",
            "allowed_values" : [ 'some-value', 'something-else', 'foobar' ],
            "conffile"       : "MY_PARAM",
            "cmd_line"       : ('f', 'some-param')
        },
        "baz" : {
            "default"        : 123,
            "allowed_range"  : dict(min=1, max=200),
            "param_type"     : param.PARAM_TYPE_INT,
        },
        "ggg" : {
            "default"        : None,
            "param_type"     : param.PARAM_TYPE_BOOL,
            "cmd_line"       : ('g', None)
        },
        "lll" : {
            "default"        : "Peter,Tom,Sally,Alice,Bob",
            "param_type"     : pyparams.PARAM_TYPE_STR_LIST,
        }
    }
)

# At this point, only the default values (if any) are known. Call the acquire()
# function to look for environment variables and process command line options.
# The acqjuire() function can accept additional parameter to overwrite the
# defaults that were specified when creating the Conf object.
# - config_filename
# - env_prefix
# - allow_unset_values
# Note that acquire checks whether any parameters remain unset after looking
# through the config file, the environment variables and the command line
# parameters. If allow_unset_values is not set (either here or in the default),
# then an exception will be raised.
CONF.acquire(sys.argv)

# Now you can get specific parameter values:
print CONF.get("baz")

# You can set parameters (their type, permissible values and ranges are
# checked):
CONF.set("baz", 199)

# You can get the names of all defined parameters (whether values have been
# set for them or not):
print CONF.keys()

# You can get a dictionary with name/value for each parameter:
print CONF.items()

```

A note about boolean parameters:

- If a parameter is defined as 'bool' then it does not take any values on
  the command line.
- In the config file or in environment variables you can use 'y', 'yes', '1',
  'true' to define a true value and 'n', 'no', '0', 'false' to define a false
  value.

A note about config files:

- Config files can contain empty lines.
- All characters following a '#' are considered comments and are ignored.
- A valid line in the config file contains the 'conffile' name of a parameter,
  followed by at least one space, followed by the value. Like so:

    MY_PARAM   foobar

A note about ignored parameters:

- You can add an 'ignore' flag (set it to True) to an individual parameter's
  definition.
- An ignored parameter can appear in the config file, environment variables
  or the command line, but will not be assigned or checked for validity.
- This is useful if you dynamically need to enable parameters, but don't
  wish to change your environment variables, scripts or config file for
  every case.

A note about lists:

- Lists are specified as a single string, with each element in the list
  separated by a comma.
- If allowed_values or allowed_range is defined then each element of the list
  needs to pass this validation test.


# Sample program

```
import pyparams

CONF = pyparams.Conf(
    default_conf_file_name      = "myproject-params.conf",
    default_conf_file_locations = [ "", "/etc/" ],
    default_env_prefix          = "MYPROJECT_",
    default_allow_unset_values  = False,
    param_dict = {
        "foo" : {
            "default"        : "some-value",
            "allowed_values" : [ 'some-value', 'something-else', 'foobar' ],
            "conffile"       : "MY_PARAM",
            "cmd_line"       : ('f', 'some-param')
        },
        "baz" : {
            "default"        : None,
            "allowed_range"  : dict(min=1, max=200),
            "param_type"     : pyparams.PARAM_TYPE_INT,
        },
        "ggg" : {
            "default"        : True,
            "param_type"     : pyparams.PARAM_TYPE_BOOL,
            "conffile"       : None
            "cmd_line"       : ('g', None)
        },
    }
)

CONF.acquire(sys.argv[1:])

print CONF.get("foo")
print CONF.get("baz")

```
This program can be run like this, for example:
```
python sample.py -f foobar --baz 123
```
When running the program it will automatically check for any config files as
well as any applicable environment variables.

Try this:
```
export MYPROJECT_BAZ=199
python sample.py -f foobar
```
Likewise, if you had a config file called 'myproject-params.conf' in your local
directory (or in /etc) and it contained a line:
```
BAZ 188
```
Then you could run the program without having to specify baz on the command
line or via environment variable.


# Tests

To run the set of unit tests, simply execute:
```
python test.py
```

# Still TODO

- Support other config file formats.
- Allow hierarchical config file interpretation, where values are read (and
  overwritten) from highest level (for example /etc) down to lowest level
  (for example local directory).
- Allow per-parameter definition of environment variable equivalent (or no
  equivalent at all).
- Add a dict type.


