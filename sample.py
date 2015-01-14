import pyparams
import sys

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
            "conffile"       : None,
            "param_type"     : pyparams.PARAM_TYPE_BOOL,
            "cmd_line"       : ('g', None)
        },
    }
)

CONF.acquire(sys.argv[1:])

CONF.dump()

print CONF.get("foo")
print CONF.get("baz")


