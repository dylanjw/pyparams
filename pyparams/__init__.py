"""
Process command line arguments, config file and environment variables.

(c) 2015 by Juergen Brendel

Repository URL: https://github.com/jbrendel/pyparams


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
    # Specify the parameter name that we should look for first in order to get
    # a specified configuration filename from the command line. This is the
    # name that may have been specified for the configuration file parameter in
    # the parameter definition dictionary. The caller knows what parameter is
    # used for this, since they defined it.
    conf_file_parameter         = "configfile",

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
            "cmd_line"       : ('f', 'some-param'),
            "doc_spec"       : { 'text'    : "The description string here is "
                                             "long and will automatically be"
                                             "wrapped across multiple lines.",
                                 'section' : "General",
                                 'argname' : "the foo value" }
        "ddd" : {
            "default"        : { 'baz' : 123 },
            "allowed_keys"   : [ 'foo', 'baz' ],
            "conffile"       : "MY_DICT",
            "param_type"     : PARAM_TYPE_STR_DICT,
            "cmd_line"       : None,
            "doc_spec"       : { 'text'    : "A dict value.",
                                 'section' : "General",
                                 'argname' : "the ddd value" }
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
            "cmd_line"       : ('g', None),
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
PARAM_TYPE_STR_LIST    = "str-list"
PARAM_TYPE_STR_DICT    = "str-dict"
_PARAM_TYPES_ALLOWED   = [ PARAM_TYPE_STR, PARAM_TYPE_INT, PARAM_TYPE_BOOL,
                           PARAM_TYPE_STR_LIST, PARAM_TYPE_STR_DICT ]

__NOT_DEFINED__        = "__NOT_DEFINED__"


def _int_check(val, param_obj=None):
    """
    Return a converted integer.

    """
    return int(val)


def _str_check(val, param_obj=None):
    """
    Return a string object.

    """
    return str(val)


def _bool_check(val, param_obj=None):
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


def _str_list_check(val, param_obj=None):
    """
    Return a list, if the value string is properly formatted and can
    be translated to a list.

    Acceptable format:

        * "foo,bar,baz"      -> [ "foo", "bar", "baz" ]
        * "foo, bar  , baz"  -> [ "foo", "bar", "baz" ]

    If the value is already a list, just return that.

    Raises exception if problems.

    """
    if type(val) is list:
        return val
    try:
        return [ str(e).strip() for e in val.split(",") ]
    except:
        raise ParamError(str(val), "Malformed list format.")

def _str_dict_check(val, param_obj=None):
    """
    Return a dict, if the value string is properly formatted and can be
    translated to a dict.

    Acceptable format:

        * "{foo:bar;baz:123}"          -> dict(foo="bar", baz=123)
        * "{ foo:bar,fuzz ; baz:xyz }" -> dict(foo=["bar","fuzz"],
                                               baz="xyz")

    If the value is already a dict, just return that.

    Understands a 'default_key': If the value does not conform to the usual
    dictionary style then this will check if a default_key was defined. If so,
    it creates a dictionary with a single key (the default key) and the whole
    value as the value of the key. This allows the easy specification of
    dictionaries where most of the time just a specific, single value is
    required.

    Raises exception if problems.

    """
    if type(val) is dict:
        return val
    val = val.strip()
    if val[0] != "{" or val[-1] != "}":
        # If no default_key is defined, we can't proceed...
        if param_obj and param_obj.default_key is None:
            raise ParamError(str(val), "Malformed dict format: "
                                       "Need to be enclosed in { }.")
        is_dict = False
    else:
        is_dict = True

    try:
        if is_dict:
            elems = [ e.strip() for e in val[1:-1].split(";") ]
        else:
            # Not dict-formatted, but a default key was defined, so we can take
            # the whole value as the single value...
            elems = [ val ]
        d = {}
        for e in elems:
            e = e.strip()
            if e:
                if is_dict:
                    name, val = e.split(":")
                    name = name.strip()
                else:
                    # ... and specify the default key as the only dict key
                    if param_obj and param_obj.default_key:
                        name = param_obj.default_key
                        val = e
                val = val.strip()
                if "," in val:
                    try:
                        d[name] = _str_list_check(val)
                    except ParamError as e:
                        raise e
                else:
                    d[name] = val
        return d
    except:
        raise ParamError(str(val), "Malformed dict format.")


class ParamError(Exception):
    """
    Custom exception for the config module.

    If the 'name' starts with a '-' then we change the formatting of the
    message slightly.

    """
    def __init__(self, name, msg):
        if name.startswith("-"):
            msg = "%s: %s" % (name[1:], msg)
        else:
            msg = "Parameter '%s': %s" % (name, msg)
        super(ParamError, self).__init__(msg)


class ParamIgnored(ParamError):
    pass


class _Param(object):
    """
    Information for a single parameter.

    The user of this module should not access this class directly. Instead, it
    should be created and modified through the Conf object.

    """
    PARAM_TYPE_CHECK_FUNCS = {
        PARAM_TYPE_STR      : _str_check,
        PARAM_TYPE_INT      : _int_check,
        PARAM_TYPE_BOOL     : _bool_check,
        PARAM_TYPE_STR_LIST : _str_list_check,
        PARAM_TYPE_STR_DICT : _str_dict_check
    }

    def __init__(self, name, default=None, allowed_values=None,
                 allowed_range=None, allowed_keys=None, mandatory_keys=None,
                 default_key=None,
                 param_type=PARAM_TYPE_STR,
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
                            if no such range should be checked against. You may
                            also define either 'min' or 'max' as None, to
                            indicate that there is no upper or lower bound.
        - allowed_keys:     For DICT types, this lists the allowable key
                            values.
        - mandatory_keys:   For DICT types, this lists the keys that absolutely
                            have to be present.
        - default_key:      For DICT types, this sets the default key. If a
                            non-dict is specified as value, then this value is
                            placed into a dictionary with this default key as
                            value. This allows easy specification of
                            dictionaries where most of the time just a single
                            value is required.
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
                            parameter name. If omitted, it will be auto-
                            generated by using the first character of the
                            parameter name as the short form and the name
                            itself as the long form. If set to None, then no
                            command line equivalent is defined. You can also
                            just set the short or the long form to None, if you
                            only wish to define one of the command line
                            equivalent forms.
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

        if (allowed_keys or mandatory_keys or default_key) and \
                param_type != PARAM_TYPE_STR_DICT:
            raise ParamError(name,
                         "Allowed keys are only allowed for dictionaries.")
        if param_type == PARAM_TYPE_STR_DICT:
            if allowed_keys  and  type(allowed_keys) != list:
                raise ParamError(name, "Allowed keys need to be a list.")
            if mandatory_keys  and  type(mandatory_keys) != list:
                raise ParamError(name, "Mandatory keys need to be a list.")
            # Sanity check allowed and mandatory keys for dictionaries
            if mandatory_keys and allowed_keys:
                for k in mandatory_keys:
                    if k not in allowed_keys:
                        raise ParamError(name,
                                         "Mandatory key '%s' not an allowed "
                                         "key." % k)
            if (default_key and allowed_keys) and \
                    (default_key not in allowed_keys):
                raise ParamError(name,
                                 "Default key '%s' not an allowed key." %
                                 default_key)
            if default_key and mandatory_keys and \
                    (len(mandatory_keys) > 1 or \
                     default_key not in mandatory_keys):
                raise ParamError(name,
                                 "The default key must be in mandatory keys "
                                 "and no additional mandatory keys are "
                                 "allowed")

        self.allowed_keys   = allowed_keys
        self.mandatory_keys = mandatory_keys
        self.default_key    = default_key

        # Type check all values in 'allowed-values' list
        if allowed_values:
            if param_type == PARAM_TYPE_STR_LIST:
                # Special casing the string list, since the type-conversion
                # function we use is very aggressive and would just return a
                # list even for a simple string like "foo". We don't want this
                # here, we just want to check that each specified value can be
                # converted to a string.
                self.allowed_values = [ str(a) for a in allowed_values ]
            else:
                self.allowed_values = [ self.param_type_check(a)
                                        for a in allowed_values ]
        else:
            self.allowed_values = None

        # Sanity check the min-max values in allowed-range.
        if allowed_range:
            if len(allowed_range.keys()) != 2  or \
                    'min' not in allowed_range  or  'max' not in allowed_range:
                raise ParamError(name,
                                 "Malformed dictionary for 'allowed_range'.")
            # The min or max in an allowed range can be None, indicating no
            # upper or lower bound.
            if allowed_range['min'] is not None:
                self.param_type_check(allowed_range['min'])
            if allowed_range['max'] is not None:
                self.param_type_check(allowed_range['max'])
            self.allowed_range = allowed_range
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
                return self.PARAM_TYPE_CHECK_FUNCS[self.param_type](
                    value, self)
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

        # If we have allowed range or value set then this test needs to be
        # applied to all elements of a list parameter. If our parameter is not
        # a list, we quickly put it in a single-element list, so we can just
        # use the same code for all types of parameters.
        if self.param_type is PARAM_TYPE_STR_LIST:
            value_list = value
        else:
            value_list = [ value ]

        for v in value_list:
            if self.allowed_values:
                if not v in self.allowed_values:
                    raise ParamError(self.name,
                                     "'%s' is not one of the allowed values."
                                                                    % v)
            if self.allowed_range:
                min_val = self.allowed_range['min']
                max_val = self.allowed_range['max']
                if (min_val is not None and v < min_val) or \
                        (max_val is not None and v > max_val):
                    raise ParamError(self.name,
                                     "'%s' is not in the allowed range."
                                                                     % v)
        if self.param_type is PARAM_TYPE_STR_DICT:
            if self.allowed_keys:
                for k in value.keys():
                    if k not in self.allowed_keys:
                        raise ParamError(self.name,
                                 "'%s' is not an allowable key value." % k)
            if self.mandatory_keys:
                for k in self.mandatory_keys:
                    if k not in value.keys():
                        raise ParamError(self.name,
                                 "Mandatory key '%s' not present." % k)

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
        s = []
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
                        s.append("\n%s" % '\n'.join(
                                    textwrap.wrap(
                                        t, width=65,
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
    def __init__(self, param_dict=None, conf_file_parameter=None,
                 default_conf_file_locations=[ "", "~/", "/etc/" ],
                 default_env_prefix=None, default_allow_unset_values=False,
                 default_allow_unknown_params=False, doc_section_order=None):
        """
        Initialize the configuration object.

        - param_dict:                  A dictionary containing the parameter
                                       definitions. The format of this
                                       dictionary is shown in this file's
                                       docstring and various sample programs
        - conf_file_parameter:         Name of the parameter with which a user
                                       can specify a configuration file.
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
        - default_allow_unknown_params: If set to True, unknown parameters in
                                       config files will be ignored, no
                                       'Unknown parameter' exception will be
                                       raised. By default, unknown parameters
                                       are not accepted.
        - doc_section_order:           Define the order in which the various
                                       sections of your parameter docs are
                                       printed when calling make_docs().
                                       Provide the list of section names in the
                                       order in which you want them printed. If
                                       omitted, sections are printed in
                                       alphabetical order.

        """
        self.params                       = {}
        self.params_by_conffile_name      = {}
        self.default_allow_unset_values   = default_allow_unset_values
        self.default_allow_unknown_params = default_allow_unknown_params
        self.conf_file_parameter          = conf_file_parameter
        self.default_conf_file_locations  = \
            [ (l if (l == "" or l.endswith("/")) else l+"/") \
                        for l in default_conf_file_locations ]
        self.default_env_prefix           = default_env_prefix or ""
        self.doc_section_order            = doc_section_order

        self._all_short_opts_so_far       = []
        self._all_long_opts_so_far        = []

        if param_dict is not None:
            for param_name, param_conf in param_dict.items():
                for k in param_conf.keys():
                    if k not in [ 'default', 'allowed_values', 'allowed_range',
                                  'allowed_keys', 'mandatory_keys',
                                  'default_key', 'param_type', 'conffile',
                                  'cmd_line', 'ignore', 'doc_spec']:
                        raise ParamError(
                            k, "Invalid parameter config attribute.")
                self.add(name=param_name, **param_conf)

    def _parse_config_file(self, f, allow_unknown_params=None):
        """
        Read through the config file and set con values.

        In config files dictionaries can stretch over multiple lines, breaking
        either behind '{' or behind ';' or behind ',' within a list value.

        """
        if allow_unknown_params is None:
            allow_unknown_params = self.default_allow_unknown_params

        value = ""
        in_continuation = False
        continuation_chars = [ '{', ',', ';' ]

        for i, line in enumerate(f.readlines()):
            line = line.strip()
            # Strip off any comments...
            elems = line.split("#", 1)
            line = elems[0].strip()
            # ... and skip if there's nothing left
            if not line:
                continue

            line = line.replace("\t", " ")

            if not in_continuation:
                # Brand new parameter, so we keep the parameter name
                elems = line.split(" ", 1)
                if len(elems) != 2:
                    raise ParamError("-Line %d" % (i+1),
                                     "Malformed line. Should have two tokens")
                param_name, value = elems
                param_name = param_name.strip()
                value = value.strip()
                if value[-1] in continuation_chars:
                    # If there is more to come for this parameter, we will skip
                    # the parameter evaluation.
                    in_continuation = True
                    continue

            else:
                value += line
                if line[-1] not in continuation_chars:
                    in_continuation = False
                else:
                    # If there is more to come for this parameter, we will skip
                    # the parameter evaluation.
                    continue

            # Evaluate parameter
            try:
                param = self.params_by_conffile_name[param_name]
                self.set(param.name, value)
            except ParamIgnored:
                pass
            except ParamError as e:
                raise ParamError("-Line %d" % (i+1), e.message)
            except KeyError as e:
                if not allow_unknown_params:
                    raise ParamError("-Line %d" % (i+1),
                                     "Unknown parameter '%s'." % param_name)
                else:
                    pass

    def _process_config_file(self, fname, allow_unknown_params):
        """
        Open config file and process its content.

        """
        if not fname:
            # It's possible that no config file is specified at all.
            return
        if fname[0] not in [ "/", "." ]:
            # Search for config file at default locations, since the user
            # didn't specify an absolute path name.
            for fn in [ prefix+fname for prefix
                           in self.default_conf_file_locations ]:
                try:
                    with open(fn, "r") as f:
                        self.config_file = fn
                        self._parse_config_file(f, allow_unknown_params)
                except IOError as e:
                    if "No such file" in e.strerror:
                        # Quietly ignore failures to find the file. Not having
                        # a config file is allowed.
                        pass
                    else:
                        # Some other error?
                        raise ParamError(fname,
                                         "Error processing config file.")
        else:
            # Looks the user specified an absolute path name
            with open(fname, "r") as f:
                self.config_file = fname
                self._parse_config_file(f, allow_unknown_params)

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
                    raise ParamError("-Environment variable %s" % \
                                                               full_var_name,
                                      e.message)

    def _process_cmd_line(self, args, filter_list=None):
        """
        Process any command line arguments.

        Those take precedence over config file and environment variables.

        With filter_list a list of options can be specified, to which the
        function should limit itself. This allows for the selective processing
        of just certain parameters. For example, an initial parameter run,
        which only looks for parameters, such as the config-file location.

        """
        # Create short option string
        short_opts_list  = []
        long_opts_list   = []
        param_opt_lookup = {}

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
            raise ParamError("-Command line option", str(e) + ".")

        for o, a in opts:
            param = param_opt_lookup.get(o)
            if not param:
                raise ParamError(o, "Unknown parameter.")
            if not param.ignore  and \
                    ((not filter_list) or param.name in filter_list):
                if param.param_type == PARAM_TYPE_BOOL:
                    self.set(param.name, True)
                else:
                    self.set(param.name, a)

    def add(self, name, default=None,
            allowed_values=None, allowed_range=None, allowed_keys=None,
            mandatory_keys=None, default_key=None,
            param_type=PARAM_TYPE_STR, conffile=__NOT_DEFINED__,
            cmd_line=__NOT_DEFINED__, ignore=False, doc_spec=None):
        """
        Add a parameter with fill configuration.

        """
        if name in self.params:
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

            self.params[name] = _Param(name, default, allowed_values,
                                       allowed_range, allowed_keys,
                                       mandatory_keys, default_key,
                                       param_type, conffile,
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
                allow_unset_values=None, allow_unknown_params=None):
        """
        Retrieve values for the defined parameters from multiple sources.

        Values are collecting using a defined order (from lowest precedence to
        highest):

        1. default values (part of the parameter definition)
        2. configuration file
        3. environment variables
        4. command line arguments

        If a config_filename is specified that is not an absolute path then we
        will look for it in various default locations. Once found, the full
        path of the actually read config file is attached in the 'config_file'
        attribute.

        """
        # Get the config file name: Process the command line parameters, but
        # just look for the presence of the config-file-name parameter, by
        # specifying the parameter-name (not the parameter value).
        if self.conf_file_parameter:
            self._process_cmd_line(args,
                                   filter_list=[ self.conf_file_parameter ])
            config_filename = self.get(self.conf_file_parameter)
        else:
            config_filename = None

        self._process_config_file(config_filename, allow_unknown_params)
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
        sections = {}
        out      = []

        # Assemble the parameter lists for each section.
        for pname, param in self.params.items():
            sec, txt = param.doc()
            if txt:
                sections.setdefault(sec, []).append(txt)

        # Alphabetically sort the list of parameters in each section.
        # Ignore case. Each parameter's documentation is a single test blob by
        # now, but we can tell those parameters that don't have short options
        # apart simply because that string blob starts with '--'. We would like
        # those parameters to be listed last. Furthermore, we would like the
        # same letter, but differently capitalized, to show the capital letter
        # last (even though naturally, a capital letter is 'less' than a lower
        # case letter).
        #
        # Therefore our 'key' function we pass to sort() does a number of
        # things: It adds a 'high' character (we use '_') to the start of any
        # '--' option. It also adds a '_' behind the first letter if the key is
        # an upper case string. That way, a capitalized option will be pushed
        # below a lower-case option that starts with the same letter.
        def my_key(k):
            if k.startswith("--"):
                k = "_"+k
                first_letter = 2
            else:
                first_letter = 1
            if k[first_letter].isupper():
                k = "%s_%s" % (k[:first_letter+1], k[first_letter+1:])
            return k.lower()

        for param_list in sections.values():
            param_list.sort(key=my_key)

        # Sort the section order, or use the explicitly specified one.
        # Ignore case.
        if self.doc_section_order:
            snames = self.doc_section_order
        else:
            snames = sections.keys()
            if snames and snames[0] is not None:
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
        conf_file_parameter    = None,
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


