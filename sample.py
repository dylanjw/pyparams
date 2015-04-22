import pyparams
import sys

CONF = pyparams.Conf(
    conf_file_parameter         = "conffile",
    default_conf_file_locations = [ "", "/etc/" ],
    default_env_prefix          = "MYPROJECT_",
    default_allow_unset_values  = False,
    doc_section_order           = [ "Specific parameters", "General" ],
    param_dict = {
        "conffile" : {
            "default"        : "myproject.conf",
            "cmd_line"       : ( None, 'conffile' ),
            "conffile"       : None,
            "doc_spec"       : { 'text'    : "Name of config file",
                                 'section' : "General",
                                 'argname' : "conffile" }
        },
        "foo" : {
            "default"        : "some-value",
            "allowed_values" : [ 'some-value', 'something-else', 'foobar' ],
            "conffile"       : "MY_PARAM",
            "cmd_line"       : ('f', 'some-param'),
            "doc_spec"       : { 'text'    : "Set the foo parameter, "
                                             "which is a really important "
                                             "one. The description string "
                                             "here is really long and will "
                                             "automatically be wrapped across "
                                             "multiple lines.",
                                 'section' : "General",
                                 'argname' : "the foo value" }
        },
        "baz" : {
            "default"        : None,
            "allowed_range"  : dict(min=1, max=200),
            "param_type"     : pyparams.PARAM_TYPE_INT,
            "doc_spec"       : { 'text'    : "The amount of baz gizmos to be "
                                             "added.",
                                 'section' : "Specific parameters",
                                 'argname' : "num" }
        },
        "ggg" : {
            "default"        : True,
            "conffile"       : None,
            "param_type"     : pyparams.PARAM_TYPE_BOOL,
            "cmd_line"       : ('g', None),
            "doc_spec"       : { 'text'    : "Flag to control the running "
                                             "of foobar.",
                                 'section' : "General" }
        },
        "lll" : {
            "default"        : "Peter,Tom,Sally,Alice,Bob",
            "param_type"     : pyparams.PARAM_TYPE_STR_LIST,
        },
        "ddd" : {
            "default"        : { "aaa" : 123 },
            "allowed_keys"   : [ "aaa", "bbb", "ccc" ],
            "mandatory_keys" : [ "aaa" ],
            "default_key"    : "aaa",
            "param_type"     : pyparams.PARAM_TYPE_STR_DICT,
            "conffile"       : None,
            "doc_spec"       : { 'text'    : "A dictionary.",
                                 'section' : "General" }
        }
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
print "@@@ Printing foo and baz."
print CONF.get("foo")
print CONF.get("baz")
try:
    print "@@@ Trying to set baz to invalid value."
    CONF.set("baz", 456)
except pyparams.ParamError:
    print "@@@ Correctly caught exception for invalid value."
print "@@@ Setting baz."
CONF.set("baz", 199)
print "@@@ Baz: ", CONF.get("baz")
print "@@@ Setting lll (a list)."
try:
    CONF.set("lll", 123)
except pyparams.ParamError:
    print "@@@ Correctly caught exception for invalid value."
CONF.set("lll", "xyz")
print "@@@ Setting baz."
print "@@@ Printing lll."
print CONF.get("lll")
if CONF.get("lll") != [ "xyz" ]:
    print "@@@ ERROR! Should be list with single element!"
CONF.set("lll", [ "a", "b" ])
print CONF.get("lll")
if CONF.get("lll") != [ "a", "b" ]:
    print "@@@ ERROR! Should be list with two elements 'a' and 'b'!"
CONF.set("lll", "x,y" )
print CONF.get("lll")
if CONF.get("lll") != [ "x", "y" ]:
    print "@@@ ERROR! Should be list with two elements 'x' and 'y'!"
CONF.set("lll", ",x,y," )
print CONF.get("lll")
if CONF.get("lll") != [ "", "x", "y", "" ]:
    print "@@@ ERROR! Should be list with four elements '', 'x', 'y', ''!"
print
print CONF.get("ddd")
print "-----------------------------"

#
# Output the automatically generated documentation for the parameters. This is
# meant to be suitable for a man page or usage page.
#
print CONF.make_doc()


