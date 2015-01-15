import pyparams
import sys

CONF = pyparams.Conf(
    default_conf_file_name      = "myproject-params.conf",
    default_conf_file_locations = [ "", "/etc/" ],
    default_env_prefix          = "MYPROJECT_",
    default_allow_unset_values  = False,
    doc_section_order           = [ "Specific parameters", "General" ],
    param_dict = {
        "foo" : {
            "default"        : "some-value",
            "allowed_values" : [ 'some-value', 'something-else', 'foobar' ],
            "conffile"       : "MY_PARAM",
            "cmd_line"       : ('f', 'some-param'),
            "doc_spec"       : { 'text'    : "Set the foo parameter, "
                                             "which is a really important one. "
                                             "The description string here is "
                                             "really long and will automatically "
                                             "be wrapped across multiple lines.",
                                 'section' : "General",
                                 'argname' : "the foo value" }
        },
        "baz" : {
            "default"        : None,
            "allowed_range"  : dict(min=1, max=200),
            "param_type"     : pyparams.PARAM_TYPE_INT,
            "doc_spec"       : { 'text'    : "The amount of baz gizmos to be added.",
                                 'section' : "Specific parameters",
                                 'argname' : "num" }
        },
        "ggg" : {
            "default"        : True,
            "conffile"       : None,
            "param_type"     : pyparams.PARAM_TYPE_BOOL,
            "cmd_line"       : ('g', None),
            "doc_spec"       : { 'text'    : "Flag to control the running of foobar.",
                                 'section' : "General" }
        },
    }
)

#
# Read parameter values from config file, environment variables and command
# line options.
#
CONF.acquire(sys.argv[1:])

#
# Dump the current configuration and any values. This is mostly for debugging
# purposes.
#
CONF.dump()

#
# Demonstrate getting and setting of parameters, including a setting attempt
# that violates some value restrictions.
#
print "-----------------------------"
print CONF.get("foo")
print CONF.get("baz")
try:
    CONF.set("baz", 456)
except pyparams.ParamError:
    print "Correctly caught exception for invalid value."
CONF.set("baz", 199)
print CONF.get("baz")
print "-----------------------------"

#
# Output the automatically generated documentation for the parameters. This is
# meant to be suitable for a man page or usage page.
#
CONF.make_doc()


