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
    default_env_prefix         = "MYPROJECT_",

    # Specify whether we allow values to remain unset. Note that a defition
    # of None for the default value just means that no default was provided.
    default_allow_unset_values = True,

    # Specify the order of sections for the automatically generated man-page
    # like output. When specifying a doc-spec for a parameter, you can specify
    # a section in which the parameters should be grouped. If no order is
    # specified, those sections are output in alphabetical order.
    doc_section_order = [ "Generic", "Example section" ],

    # Specify the actual parameters. For each parameter we define a name (the
    # key in the dictionary) as well as a specification dictionary. The spec
    # dictionary can contain the values shown in the Params() docstring.
    param_dict = {
        "foo" : {
            "default"        : "some-value",
            "allowed_values" : [ 'some-value', 'something-else', 'foobar' ],
            "conffile"       : "MY_PARAM",
            "cmd_line"       : ('f', 'some-param')
            "doc_spec"       : { 'text'    : "The description string here is "
                                             "long and will automatically be"
                                             "wrapped across multiple lines.",
                                 'section' : "General",
                                 'argname' : "the foo value" }
        },
        "baz" : {
            "default"        : 123,
            "allowed_range"  : dict(min=1, max=200),
            "param_type"     : param.PARAM_TYPE_INT,
            "doc_spec"       : { 'text'    : "Amount of baz gizmos to add.",
                                 'section' : "Specific parameters",
                                 'argname' : "num" }
        },
        "ggg" : {
            "default"        : None,
            "param_type"     : param.PARAM_TYPE_BOOL,
            "cmd_line"       : ('g', None)
            "doc_spec"       : { 'text'    : "Flag control run of foobar.",
                                 'section' : "General" }
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

"""

version = (0, 1, 0)
__version__ = '.'.join(map(str, version))

import os
import sys
import getopt
import textwrap

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


class ParamIgnored(ParamError):
    pass


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
                 conffile=None, cmd_line=None, ignore=False,
                 doc_spec=None):
        """
        Configuration for a given parameter.

        - name:             The name of the parameter, which can be used for
                            get()/set().
        - default:          The default value for this parameter. If this is
                            set to None, then no default value is set.
        - allowed_values:   A list of permissible values. When a value is set,
                            it is checked that it is contained in this list.
                            Leave as None if no such list should be checked
                            against.
        - allowed_range:    A dict with a 'min' and 'max' value. The assigned
                            value needs to be within this range. Leave as None
                            if no such range should be checked against.
        - param_type:       Indicate the type of the parameter. This module
                            defines the possible types in PARAM_TYPE_STR,
                            PARAM_TYPE_INT and PARAM_TYPE_BOOL. It will be
                            string by default.
        - conffile:         The name that this parameter should have in the
                            configuration file. If omitted, this name is
                            constructed automatically by capitalizing the
                            parameter name and replacing all '-' with '_'. If
                            set to None, then no config file equivalent for the
                            parameter is defined. The same name is used as the
                            environment variable equivalent, except that the
                            'default_env_prefix' (a Conf parameter) is
                            pre-pended to the name.
        - cmd_line:         The definition of the command line equivalent for
                            this parameter. It consists of a tuple, containing
                            the short (one-letter) and long command line
                            parameter name. If omitted, it will be
                            auto-generated by using the first character of the
                            parameter name as the short form and the name
                            itself as the long form. If set to None, then no
                            command line equivalent is defined. You can also
                            just set the short or the long form to None, if you
                            only wish to define one of the command line
                            equivalen forms.
        - ignore:           If set, the parameter is not validated and any
                            assignment (set) or access (get) results in an
                            exception, while any occurence of the parameter in
                            the config file, environment or command line is
                            ignored.
        - doc_spec:         A documentation specification for this parameter,
                            so that man-page suitable output can be generated
                            automatically. This value is a dictionary with the
                            three keys 'text', 'section' and 'argname'.

        """
        self.name        = name
        self.conffile    = conffile
        self.ignore      = ignore
        self.doc_spec    = doc_spec

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
        if self.ignore:
            # No checking of parameter values if this one is marked to
            # be ignored.
            return value
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

    def doc(self):
        """
        Return a string suitable for inclusion in a man page.

        This returns a tuple consisting of the section name and the parameter
        specific string.

        """
        # If no doc-spec was define, create a quick default spec
        dspec = self.doc_spec
        if not dspec:
            dspec = { "text" : "", "section" : None, "argname" : "" }

        # We don't have a parameter name in the case of boolean flags
        if self.param_type == PARAM_TYPE_BOOL:
            argname = ""
        else:
            argname = dspec.get('argname')
            if not argname:
                argname = "val"

        # Assemble the cmd-line option description
        s = list()
        if self.cmd_line:
            short_opt, long_opt = self.cmd_line
            if short_opt:
                s.append("-%s" % short_opt)
                if argname:
                    s.append(" <%s>" % argname)
                if long_opt:
                    s.append(", ")
            if long_opt:
                s.append("--%s" % long_opt)
                if argname:
                    s.append("=<%s>" % argname)
            if s:
                text = dspec.get('text')
                if text:
                    # We want the ability to format our text a little, so we
                    # allow the user to define blocks with \n in the text.
                    for t in text.split("\n"):
                        initial_indent = "    "
                        subsequent_indent = "    "
                        # Do some extra indent for text blocks that start with
                        # a '*', so that we can have nicely formatted bulleted
                        # lists.
                        if t.startswith("*"):
                            initial_indent += ""
                            subsequent_indent += "  "
                        s.append("\n%s" % '\n'.join(textwrap.wrap(t,
                                                initial_indent=initial_indent,
                                                replace_whitespace=False,
                                                subsequent_indent=subsequent_indent)))
                    s.append("\n")
                else:
                    s.append("\n")
                if self.default:
                    s.append("    Default value: %s\n" % self.default)
                if self.conffile:
                    s.append("    Conf file equivalent: %s\n" % self.conffile)

            return (dspec.get('section'), ''.join(s))
        else:
            # No doc provided if there are no command line parameters.
            # We might change that in the future, once we decide how to print
            # parameters that only exist in the config file or the environment
            # variables.
            return None, None


class Conf(object):
    """
    A configuration object.

    The object itself is configured with a number of parameter definitions.
    These can either be passed in via a dictionary, or they can be individually
    added later on.

    """
    def __init__(self, param_dict=dict(), default_conf_file_name=None,
                 default_conf_file_locations=[ "", "~/", "/etc/" ],
                 default_env_prefix=None, default_allow_unset_values=False,
                 doc_section_order=None):
        """
        Initialize the configuration object.

        - param_dict:                  A dictionary containing the parameter
                                       definitions. The format of this
                                       dictionary is show in this file's
                                       docstring and various sample programs
        - default_conf_file_name:      The name of the configuration file that
                                       we will look for. This is just the
                                       filename, not a full path. This value
                                       can can be overwritten in the acquire()
                                       call.
        - default_conf_file_locations: List of directories, which will be
                                       search (first to last) to look for the
                                       config file. Once it is found it is
                                       processed, no further directories are
                                       searched after that. This value can be
                                       overwritten in the acquire() call.
        - default_env_prefix:          A project or program specific prefix you
                                       can define, which is attached to the
                                       'conffile' name of each parameter in
                                       order to derive the environment variable
                                       name equivalent. By default, no prefix
                                       is set.
        - default_allow_unset_values:  If set to True, the configuration will
                                       NOT check whether after an acquire()
                                       there remain any unset values.
                                       Otherwise, the configuration object will
                                       perform such a test and will throw an
                                       exception if any of the parameters
                                       remaines without a value after defaults,
                                       config files, environment variables and
                                       command line options are evaluated. By
                                       default, the test is peformed.
        - doc_section_order:           Define the order in which the various
                                       sections of your parameter docs are
                                       printed when calling make_docs().
                                       Provide the list of section names in the
                                       order in which you want them printed. If
                                       omitted, sections are printed in
                                       alphabetical order.

        """
        self.params                      = dict()
        self.params_by_conffile_name     = dict()
        self.default_allow_unset_values  = default_allow_unset_values
        self.default_conf_file_name      = default_conf_file_name
        self.default_conf_file_locations = default_conf_file_locations
        self.default_env_prefix          = default_env_prefix or ""
        self.doc_section_order           = doc_section_order

        self._all_short_opts_so_far      = list()
        self._all_long_opts_so_far       = list()

        for param_name, param_conf in param_dict.items():
            for k in param_conf.keys():
                if k not in [ 'default', 'allowed_values', 'allowed_range',
                              'param_type', 'conffile', 'cmd_line', 'ignore',
                              'doc_spec']:
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
                raise ParamError("-Line %d" % (i+1), "Malformed line.")
            param_name, value = elems

            try:
                param = self.params_by_conffile_name[param_name]
                self.set(param.name, value)
            except ParamIgnored:
                pass
            except ParamError as e:
                raise ParamError("-Line %d" % (i+1), e.message)
            except KeyError as e:
                raise ParamError("-Line %d" % (i+1),
                                 "Unknown parameter '%s'." % param_name)

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
                        self.config_file = fname
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
                self.config_file = fname
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
                try:
                    self.set(param.name, value)
                except ParamIgnored:
                    pass
                except ParamError as e:
                    raise ParamError("-Environment variable %s" % full_var_name,
                                      e.message)

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
            if not param.ignore:
                if param.param_type == PARAM_TYPE_BOOL:
                    self.set(param.name, True)
                else:
                    self.set(param.name, a)

    def add(self, name, default=None, allowed_values=None, allowed_range=None,
            param_type=PARAM_TYPE_STR, conffile=__NOT_DEFINED__,
            cmd_line=__NOT_DEFINED__, ignore=False, doc_spec=None):
        """
        Add a parameter with fill configuration.

        """
        if 'name' in self.params:
            raise ParamError(name, "Duplicate definition.")
        else:
            short_opt = long_opt = None
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
                                      cmd_line, ignore, doc_spec)
            if conffile:
                self.params_by_conffile_name[conffile] = self.params[name]

    def get(self, name):
        """
        Retrieve just the value of a named parameter.

        """
        if name not in self.params:
            raise ParamError(name, "Unknown parameter.")
        param = self.params[name]
        if param.ignore:
            raise ParamIgnored(name, "Parameter configured to be ignored.")
        return param.value

    def keys(self):
        """
        Return the name of all parameters.

        Only list names of not-ignored parameters.

        """
        return [ pname for pname,param in self.params.items()
                            if not param.ignore ]

    def items(self):
        """
        Return a dictionary with name/value for all parameters.

        Only parameters not configured to be ignored are shown.

        """
        return dict(
                   [ (name, self.params[name].value)
                            for name in self.keys()
                                    if not self.params[name].ignore ]
               )

    def get_by_conffile_name(self, conffile_name):
        """
        Retrieve just the value of a parameter, named by its conffile name.

        """
        if conffile_name not in self.params_by_conffile_name:
            raise ParamError(conffile_name, "Unknown parameter.")
        param = self.params_by_conffile_name[conffile_name]
        if param.ignore:
            raise ParamIgnored(conffile_name,
                              "Parameter configured to be ignored.")
        return param.value

    def set(self, name, value):
        """
        Set the value of a named parameter.

        """
        if name not in self.params:
            raise ParamError(name, "Unknown parameter.")
        param = self.params[name]
        if param.ignore:
            raise ParamIgnored(name, "Parameter configured to be ignored.")
        param.value = param.validate(value)

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

        As a side effect, the actually read config file name/path is attached
        to the config object in the 'config_file' attribute.

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
                try:
                    value = self.get(pname)
                    if value is None:
                        raise ParamError(pname,
                                        "Requires a value, nothing has been set.")
                except ParamIgnored:
                    pass

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
            if param.ignore:
                print "    - IS IGNORED!"
            else:
                print "    - current value:    %s" % str(param.value)


    def make_doc(self, indent=0):
        """
        Create output suitable for man page.

        This produces a string suitable for the 'OPTIONS' portion of a man
        page, or 'usage' page.

        """
        istr     = indent*" "
        sections = dict()
        out      = list()

        # Assemble the parameter lists for each section.
        for pname, param in self.params.items():
            sec, txt = param.doc()
            if txt:
                sections.setdefault(sec, list()).append(txt)

        # Alphabetically sort the list of parameters in each section.
        # Ignore case.
        for param_list in sections.values():
            param_list.sort(key=lambda k: k.lower())

        # Sort the section order, or use the explicitly specified one.
        # Ignore case.
        if self.doc_section_order:
            snames = self.doc_section_order
        else:
            snames = sections.keys()
            snames.sort(key=lambda k: k.lower())

        # Output for each section. Each parameter output line is indented.
        for sname in snames:
            param_txts = sections[sname]
            if sname:
                out.append("%s%s:" % (istr, sname))
            for t in param_txts:
                for l in t.split("\n"):
                    out.append("%s    %s" % (istr,l))
        return '\n'.join(out).rstrip()


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


