"""
Process command line arguments, config file and environment variables.

This module uses a single parameter definition to define and initialize
configuration parameters for a program.

The parameter values are taken (in that order) from:

    1. defined default values
    2. a configuration file
    3. environment variables
    4. command line options

A full config definition may look like this. Comments are inserted to explain
various features:

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
    default_env_prefix         = "MYPROJECT_"

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
    }
)

# At this point, only the default values (if any) are known. Call the acquire()
# function to look for environment variables and process command line options.
# The acquire() function can accept additional parameter to overwrite the
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

A note about boolean parameters:

- If a parameter is defined as 'bool' then it does not take any values on
  the command line.
- In the config file or in environment variables you can use 'y', 'yes', '1',
  'true' to define a true value and 'n', 'no', '0', 'false' to define a false
  value.

"""

version = (0, 1, 0)
__version__ = '.'.join(map(str, version))

import os
import sys
import getopt

#
# Define all the configuration variables, which can be specified on the command
# line or via the command file. Also set any defaults, if applicable.
#

PARAM_TYPE_STR         = "string"
PARAM_TYPE_INT         = "integer"
PARAM_TYPE_BOOL        = "bool"
_PARAM_TYPES_ALLOWED   = [ PARAM_TYPE_STR, PARAM_TYPE_INT, PARAM_TYPE_BOOL ]

__NOT_DEFINED__        = "__NOT_DEFINED__"

def _bool_check(val):
    """
    Return True or False depending on the boolean equivalent of the value.

    This allows us to accept True and False, but also strings, such as
    "true", "false", "yes", "no", etc.

    Any other values will cause an exception.

    """
    if type(val) is bool:
        return val
    if type(val) is str:
        val = val.lower()
        if val in [ "y", "yes", "true", "1" ]:
            return True
        if val in [ "n", "no", "false", "0" ]:
            return False
    raise ParamError(str(val), "Cannot be translated to boolean value.")


class ParamError(Exception):
    """
    Custom exception for the config module.

    """
    def __init__(self, name, msg):
        if name.startswith("-"):
            msg = "%s: %s" % (name[1:], msg)
        else:
            msg = "Parameter '%s': %s" % (name, msg)
        super(ParamError, self).__init__(msg)


class Param(object):
    """
    Information for a single parameter.

    """
    PARAM_TYPE_CHECK_FUNCS = {
        PARAM_TYPE_STR  : str,
        PARAM_TYPE_INT  : int,
        PARAM_TYPE_BOOL : _bool_check
    }

    def __init__(self, name, default=None, allowed_values=None,
                 allowed_range=None, param_type=PARAM_TYPE_STR,
                 conffile=None, cmd_line=None):
        """
        Configuration for a given parameter.

        """
        self.name     = name
        self.conffile = conffile

        if param_type not in _PARAM_TYPES_ALLOWED:
            raise ParamError(name, "Unknown parameter type '%s'." % param_type)
        self.param_type = param_type

        # Special checking
        if param_type == PARAM_TYPE_BOOL:
            if allowed_values or allowed_range:
                raise ParamError(name,
                         "Allowed values or range not allowed for boolean.")

        # Type check all values in 'allowed-values' list
        if allowed_values:
            self.allowed_values = [ self.param_type_check(a) for a in
                                                            allowed_values ]
        else:
            self.allowed_values = None

        # Sanity check the min-max values in allowed-range.
        if allowed_range:
            if len(allowed_range.keys()) != 2  or \
                    'min' not in allowed_range  or  'max' not in allowed_range:
                raise ParamError(name,
                                   "Malformed dictionary for 'allowed_range'.")
            if self.param_type_check(allowed_range['min']) and \
                                 self.param_type_check(allowed_range['max']):
                self.allowed_range = allowed_range
            else:
                raise ParamError(name,
                             "Values in allowed-range not of permitted type.")
        else:
            self.allowed_range = None

        # Type check the default value
        if default is not None:
            self.default  = self.param_type_check(default)
            self.value    = self.validate(self.default)
        else:
            self.default = self.value = None

        if cmd_line:
            if len(cmd_line) != 2  or  (cmd_line[0] and len(cmd_line[0]) != 1):
                raise ParamError(name,
                                 "Invalid command line option specification.")

        self.cmd_line = cmd_line

    def param_type_check(self, value):
        """
        Convert the value to the specified type, raise exception if not
        possible.

        """
        if value is not None:
            try:
                return self.PARAM_TYPE_CHECK_FUNCS[self.param_type](value)
            except:
                raise ParamError(self.name,
                                 "Cannot convert '%s' to type '%s'." % \
                                                    (value, self.param_type))
        return None

    def validate(self, value):
        """
        Check if this is a permissable value for the parameter.

        If allowed-values are defined, they take precedence over allowed-range.

        """
        value = self.param_type_check(value)
        if self.allowed_values:
            if not value in self.allowed_values:
                raise ParamError(self.name,
                                 "'%s' is not one of the allowed values."
                                                                    % value)
        if self.allowed_range:
            if not ( self.allowed_range['min'] \
                            <= value <= self.allowed_range['max'] ):
                raise ParamError(self.name,
                                 "'%s' is not in the allowed range." % value)

        return value

    def make_getopts_str(self):
        """
        Return short and long option string for this parameter.

        The strings are formatted to be suitable for getopts. A tuple with both
        strings is returned.

        For example, if the parameter takes a value and has a short option of
        "v" and a long option of "value", then this function returns:

            ( "v:", "value=" )

        If it does not take a parameter (boolean) then this returns:

            ( "v", "value" )

        """
        if not self.cmd_line:
            return None, None
        if self.param_type != PARAM_TYPE_BOOL:
            opt_indicators = ( ":", "=" )
        else:
            opt_indicators = ( "", "" )
        return (self.cmd_line[0]+opt_indicators[0]
                                        if self.cmd_line[0] else None,
                self.cmd_line[1]+opt_indicators[1]
                                        if self.cmd_line[1] else None)


class Conf(object):
    """
    A configuration object.

    The object itself is configured with a number of parameter definitions.
    These can either be passed in via a dictionary, or they can be individually
    added later on.

    """
    def __init__(self, param_dict=dict(), default_conf_file_name=None,
                 default_conf_file_locations=[ "", "~/", "/etc/" ],
                 default_env_prefix=None, default_allow_unset_values=False):
        """
        Initialize the configuration object.

        """
        self.params                      = dict()
        self.params_by_conffile_name     = dict()
        self.default_allow_unset_values  = default_allow_unset_values
        self.default_conf_file_name      = default_conf_file_name
        self.default_conf_file_locations = default_conf_file_locations

        self.default_env_prefix          = default_env_prefix or ""

        self._all_short_opts_so_far      = list()
        self._all_long_opts_so_far       = list()

        for param_name, param_conf in param_dict.items():
            for k in param_conf.keys():
                if k not in [ 'default', 'allowed_values', 'allowed_range',
                              'param_type', 'conffile', 'cmd_line' ]:
                    raise ParamError(k, "Invalid parameter config attribute.")

            self.add(name=param_name, **param_conf)

    def _parse_config_file(self, f):
        """
        Read through the config file and set con values.

        """
        for i, line in enumerate(f.readlines()):
            line = line.strip()
            # Strip off any comments...
            elems = line.split("#", 1)
            line = elems[0]
            # ... and skip if there's nothing left
            if not line:
                continue

            elems = line.split()
            if len(elems) != 2:
                raise ParamError("-Line %d" % i, "Malformed line.")
            param_name, value = elems

            param = self.params_by_conffile_name[param_name]
            try:
                self.set(param.name, value)
            except ParamError as e:
                raise ParamError("-Line %d" % i, e.message)

    def _process_config_file(self, fname):
        """
        Open config file and process its content.

        """
        if not fname:
            # Search for config file at default locations
            for fname in [ prefix+self.default_conf_file_name for prefix
                                        in self.default_conf_file_locations ]:
                try:
                    with open(fname, "r") as f:
                        self._parse_config_file(f)
                except IOError as e:
                    if "No such file" in e.strerror:
                        # Quietly ignore failures to find the file. Not having
                        # a config file is allowed.
                        pass
                    else:
                        raise ParamError(fname,
                                         "Error processing config file.")
        else:
            with open(fname, "r") as f:
                self._parse_config_file(f)

    def _process_env_vars(self, env_prefix=None):
        """
        Look for environment variables for config values.

        The name of the environment variables is the same as the conffile name
        of the parameter, except that we allow a specific prefix to be placed
        in front of the environment variable name.

        For example, if the conffile name is MY_VAR and we define an env_prefix
        of "FOO_", then the environment variable we are looking for is
        FOO_MY_VAR.

        """
        env_prefix = env_prefix or self.default_env_prefix
        if not env_prefix:
            env_prefix = ""
        for var_name, param in self.params_by_conffile_name.items():
            full_var_name = env_prefix+var_name
            value = os.environ.get(full_var_name)
            if value is not None:
                self.set(param.name, value)

    def _process_cmd_line(self, args):
        """
        Process any command line arguments.

        Those take precedence over config file and environment variables.

        """
        # Create short option string
        short_opts_list = list()
        long_opts_list  = list()
        param_opt_lookup = dict()

        for pname, param in self.params.items():
            short_str, long_str = param.make_getopts_str()
            if short_str:
                short_opts_list.append(short_str)
                param_opt_lookup["-%s" %
                        (short_str if not short_str.endswith(':') else
                                                short_str[:-1])] = param
            if long_str:
                long_opts_list.append(long_str)
                param_opt_lookup["--%s" %
                        (long_str if not long_str.endswith('=') else
                                                long_str[:-1])] = param

        short_opts_str = ''.join(short_opts_list)

        try:
            opts, args = getopt.getopt(args, short_opts_str, long_opts_list)
        except getopt.GetoptError as e:
            raise ParamError("-Command line option", str(e))

        for o, a in opts:
            param = param_opt_lookup.get(o)
            if not param:
                raise ParamError(o, "Unknown parameter.")
            if param.param_type == PARAM_TYPE_BOOL:
                self.set(param.name, True)
            else:
                self.set(param.name, a)

    def add(self, name, default=None, allowed_values=None, allowed_range=None,
            param_type=PARAM_TYPE_STR, conffile=__NOT_DEFINED__,
            cmd_line=__NOT_DEFINED__):
        """
        Add a parameter with fill configuration.

        """
        if 'name' in self.params:
            raise ParamError(name, "Duplicate definition.")
        else:
            if cmd_line == __NOT_DEFINED__:
                # Automatically create the command line short and long option
                # if the user left it undefined. We use the first letter of
                # the name for short and the full name for long. If the name
                # consists of only one letter, we won't define a long option.
                short_opt = name[0]
                if len(name) > 1:
                    long_opt = name
                else:
                    long_opt = None
                cmd_line = (short_opt, long_opt)
            elif cmd_line:
                short_opt, long_opt = cmd_line

            if conffile == __NOT_DEFINED__:
                # Automatically create the conffile name of the parameter, if
                # the user left it undefined. We use the name in all caps.
                conffile = name.upper().replace("-", "_")

            if conffile:
                if conffile in self.params_by_conffile_name:
                    raise ParamError(conffile, "Duplicate definition.")

            if short_opt:
                if short_opt in self._all_short_opts_so_far:
                    raise ParamError(name,
                                     "Short option '-%s' already in use." %
                                                                     short_opt)
                else:
                    self._all_short_opts_so_far.append(short_opt)

            if long_opt:
                if long_opt in self._all_long_opts_so_far:
                    raise ParamError(name,
                                     "Long option '--%s' already in use." %
                                                                     long_opt)
                else:
                    self._all_long_opts_so_far.append(long_opt)

            self.params[name] = Param(name, default, allowed_values,
                                      allowed_range, param_type, conffile,
                                      cmd_line)
            if conffile:
                self.params_by_conffile_name[conffile] = self.params[name]

    def get(self, name):
        """
        Retrieve just the value of a named parameter.

        """
        if name not in self.params:
            raise ParamError(name, "Unknown parameter.")
        return self.params[name].value

    def keys(self):
        """
        Return the name of all parameters.

        """
        return self.params.keys()

    def items(self):
        """
        Return a dictionary with name/value for all parameters.

        """
        return dict(
                   [ (name, self.params[name].value) for name in self.keys() ]
               )

    def get_by_conffile_name(self, conffile_name):
        """
        Retrieve just the value of a parameter, named by its conffile name.

        """
        if conffile_name not in self.params_by_conffile_name:
            raise ParamError(conffile_name, "Unknown parameter.")
        return self.params_by_conffile_name[conffile_name].value

    def set(self, name, value):
        """
        Set the value of a named parameter.

        """
        if name not in self.params:
            raise ParamError(name, "Unknown parameter.")
        self.params[name].value = self.params[name].validate(value)

    def acquire(self, args, config_filename=None, env_prefix=None,
                allow_unset_values=None):
        """
        Retrieve values for the defined parameters from multiple sources.

        Values are collecting using a defined order (from lowest precedence to
        highest):

        1. default values (part of the parameter definition)
        2. configuration file
        3. environment variables
        4. command line arguments

        If a config-file name is specified then this overrides the default
        config file name of the config object.

        """
        self._process_config_file(config_filename)
        self._process_env_vars(env_prefix)
        self._process_cmd_line(args)

        if allow_unset_values is None:
            allow_unset_values = self.default_allow_unset_values

        if not allow_unset_values:
            # Check if any of our parameters are set to None. This is NOT
            # allowed, all of the parameters need to get a value from
            # somewhere: Default, config file, environment or command line.
            for pname in self.params.keys():
                if self.get(pname) is None:
                    raise ParamError(pname,
                                    "Requires a value, nothing has been set.")

    def dump(self):
        """
        Output the current configuration.

        This is mostly for debugging purposes right now, but something like
        this should be extended to auto-generate help pages as well.

        """
        for pname, param in self.params.items():
            print "* %s" % pname
            print "    - default:          %s" % param.default
            print "    - conffile:         %s" % param.conffile
            print "    - type:             %s" % param.param_type
            print "    - allowed_values:   %s" % param.allowed_values
            print "    - allowed_range:    %s" % param.allowed_range
            print "    - cmd_line:         %s" % str(param.cmd_line)
            print "    - current value:    %s" % str(param.value)


if __name__ == "__main__":
#
# --------------------------------------------------------------
#

# A sample configuration:

    CONF = Conf(
        default_conf_file_name = "yixus-deploy.conf",
        default_env_prefix     = "DEPLOY_",
        default_allow_unset_values     = True,
        param_dict = {
            "action" : {
                "default"        : "full",
                "allowed_values" : [ 'full', 'test', 'partial' ],
            },
            "region" : {
               "default"         : "east",
               "allowed_values"  : [ "west", "east", "north", "south" ],
               "conffile"        : "REGION_SPEC",
            },
            "quantity"  : {
                "default"        : 123,
                "allowed_range"  : dict(min=1, max=200),
                "param_type"     : PARAM_TYPE_INT,
            },
            "enable" : {
                "default"        : None,
                "conffile"       : "START_IT",
                "param_type"     : PARAM_TYPE_BOOL,
                "cmd_line"       : ('s', 'startit')
            }
        },
    )


#
# Main section, running through the steps
#
    def usage():
        print "This is some usage info"

    try:
        CONF.acquire(sys.argv[1:], config_filename="bbb.txt")
    except ParamError as e:
        print e
        usage()
        exit(1)

    print "@@@ action:   ", CONF.get("action")
    print "@@@ region:   ", CONF.get("region")
    print "@@@ quantity: ", CONF.get("quantity")
    print "@@@ enable:   ", CONF.get("enable")

    print "@@@ keys: ",  CONF.keys()
    print "@@@ items: ", CONF.items()


