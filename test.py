import os
import shutil
import tempfile
import StringIO
import unittest

from pyparams import ( _bool_check,
                       _str_list_check,
                       _str_dict_check,
                       _Param,
                       ParamError,
                       PARAM_TYPE_BOOL,
                       PARAM_TYPE_INT,
                       PARAM_TYPE_STR_LIST,
                       PARAM_TYPE_STR_DICT,
                       Conf
                     )


class LowLevelFunctionTests(unittest.TestCase):
    """
    Tests, which directly use lower level functions of the module.

    """
    def test_bool_check(self):
        """
        Test the function that converts various types and values in their
        boolean equivalent.

        """
        for v in [ True, "y", "Y", "yes", "yEs", "true", "TRUE", "trUE", "1" ]:
            self.assertTrue(_bool_check(v))
        for v in [ False, "n", "n", "no", "nO", "false", "fALSe", "0" ]:
            self.assertFalse(_bool_check(v))
        for v in [ 1, 0, "ja", "nein", "j", "n", "t", "f" ]:
            self.assertRaises(ParamError, _bool_check, (v,))

    def test_str_list_check(self):
        """
        Test the function that converts lists of strings.

        """
        self.assertEqual([ 1,2,"3",True ], _str_list_check( [1,2,"3",True] ))
        self.assertEqual([ "1","2","3" ], _str_list_check( "1,2,3" ))
        self.assertEqual([ "1","2","3" ], _str_list_check( "1 ,  2 ,  3" ))
        self.assertEqual([ "","1","","3","" ], _str_list_check( ",1,,3," ))
        self.assertEqual([ "1:3" ], _str_list_check( "1:3" ))

    def test_str_dict_check(self):
        """
        Test the function that converts lists of strings.

        """
        self.assertEqual({ 'foo' : 123 }, _str_dict_check( { 'foo' : 123 }))
        self.assertEqual({ 'foo' : '123' }, _str_dict_check( "{ foo : 123 }"))
        self.assertEqual({ 'foo' : '123', 'bar' : 'ggg' },
                         _str_dict_check( "{ foo : 123 ; bar : ggg }"))
        self.assertEqual({ 'foo' : [ '123', 'ddd' ], 'bar' : 'ggg' },
                         _str_dict_check( "{ foo : 123 , ddd ; bar : ggg }"))

    def test_param_error_class(self):
        """
        Test the message formatting in the ParamError class.

        """
        try:
            raise ParamError("Foobar", "This is the message.")
        except ParamError as e:
            self.assertEqual(e.message,
                             "Parameter 'Foobar': This is the message.")

        # Starting the parameter name with a "-" allows us to change the
        # formatting behaviour of the class, dropping the 'parameter' prefix.
        # This makes this class usable in other contexts as well.
        try:
            raise ParamError("-Foobar", "This is the message.")
        except ParamError as e:
            self.assertEqual(e.message,
                             "Foobar: This is the message.")


class ParamClassTests(unittest.TestCase):
    """
    Tests for the _Param class.

    """
    def _make_param(self, **kwargs):
        """
        Helper function to make it easier to test the Param class __init__
        function.

        """
        if 'name' not in kwargs:
            kwargs['name'] = 'dummy'
        return _Param(**kwargs)

    def test_param_init_errors(self):
        """
        Test the initialization catches various error conditions.

        """
        self.assertRaisesRegexp(ParamError,
                                "Unknown parameter type 'FOO'",
                                self._make_param,
                                **{ "param_type" : "FOO" })

        self.assertRaisesRegexp(ParamError,
                                "Allowed values or range not allowed for",
                                self._make_param,
                                **{ "param_type" : PARAM_TYPE_BOOL,
                                    "allowed_range" : dict(min=1,max=2) })

        self.assertRaisesRegexp(ParamError,
                                "Allowed values or range not allowed for",
                                self._make_param,
                                **{ "param_type" : PARAM_TYPE_BOOL,
                                    "allowed_values" :  [ "1", "2" ] })

        self.assertRaisesRegexp(ParamError,
                                "Cannot convert 'foo' to type 'integer'.",
                                self._make_param,
                                **{ "param_type" : PARAM_TYPE_INT,
                                    "allowed_values" :  [ "1", 2, "foo" ] })

        self.assertRaisesRegexp(ParamError,
                                "Malformed dictionary for 'allowed_range'.",
                                self._make_param,
                                **{ "param_type" : PARAM_TYPE_INT,
                                    "allowed_range" :  dict(foo=1, max=3) })

        self.assertRaisesRegexp(ParamError,
                                "Cannot convert 'x' to type 'integer'.",
                                self._make_param,
                                **{ "param_type" : PARAM_TYPE_INT,
                                    "allowed_range" :  dict(min="x", max=3) })

        self.assertRaisesRegexp(ParamError,
                                "'123' is not in the allowed range.",
                                self._make_param,
                                **{ "param_type" : PARAM_TYPE_INT,
                                    "allowed_range" :  dict(min=1, max=3),
                                    "default" : 123 })

        self.assertRaisesRegexp(ParamError,
                                "Cannot convert 'foo' to type 'integer'.",
                                self._make_param,
                                **{ "param_type" : PARAM_TYPE_INT,
                                    "default" : "foo" })

        self.assertRaisesRegexp(ParamError,
                                "Invalid command line option specification.",
                                self._make_param,
                                **{ "cmd_line" : "foo" })

        self.assertRaisesRegexp(ParamError,
                                "Invalid command line option specification.",
                                self._make_param,
                                **{ "cmd_line" : ("1","2","3") })

        self.assertRaisesRegexp(ParamError,
                                "Invalid command line option specification.",
                                self._make_param,
                                **{ "cmd_line" : ("ab","foo") })

        self.assertRaisesRegexp(ParamError,
                                "'baz' is not one of the allowed values.",
                                self._make_param,
                                **{ "param_type" : PARAM_TYPE_STR_LIST,
                                    "default" : "foo,bar,baz",
                                    "allowed_values" : [ "foo", "bar" ]})

        self.assertRaisesRegexp(ParamError,
                                "'zzz' is not in the allowed range.",
                                self._make_param,
                                **{ "param_type" : PARAM_TYPE_STR_LIST,
                                    "default" : "foo,bar,baz,zzz",
                                    "allowed_range" : dict(min="a", max="x")})

    def test_param_validate_error(self):
        """
        Testing validation of various parameter values.

        """
        # Checking for allowed-range
        p = _Param(name='foo', param_type=PARAM_TYPE_INT,
                   allowed_range=dict(min=1, max=5))
        p.validate(1)
        p.validate("1")
        self.assertRaisesRegexp(ParamError,
                                "Cannot convert 'foo' to type 'integer'.",
                                p.validate, "foo")
        self.assertRaisesRegexp(ParamError,
                                "'6' is not in the allowed range.",
                                p.validate, 6)
        self.assertRaisesRegexp(ParamError,
                                "'0' is not in the allowed range.",
                                p.validate, 0)

        # Checking for allowed-values
        p = _Param(name='foo', param_type=PARAM_TYPE_INT,
                   allowed_values=[ 1, 3, 5 ])
        p.validate(1)
        p.validate("3")
        self.assertRaisesRegexp(ParamError,
                                "'0' is not one of the allowed values.",
                                p.validate, 0)

        # Checking for list validation with allowed values
        p = _Param(name='foo', param_type=PARAM_TYPE_STR_LIST,
                   allowed_values=[ "1", "2", "3" ])
        p.validate([ "1", "2" ])
        p.validate("1,2,3,1,2")
        self.assertRaisesRegexp(ParamError,
                                "'0' is not one of the allowed values.",
                                p.validate, "0,1")

        # Checking for list validation with allowed ranges
        p = _Param(name='foo', param_type=PARAM_TYPE_STR_LIST,
                   allowed_range=dict(min="a", max="f"))
        p.validate([ "a", "aa", "bb" ])
        p.validate("a,aa,bb,eeee,f")
        self.assertRaisesRegexp(ParamError,
                                "'A' is not in the allowed range.",
                                p.validate, "a,f,A")

    def test_param_getopt_str_output(self):
        """
        Testing that we create correct specs for getopt.

        """
        p = _Param(name='foo', param_type=PARAM_TYPE_INT,
                   allowed_range=dict(min=1, max=5))
        self.assertEqual(p.make_getopts_str(), ( None, None ))

        p = _Param(name='foo', param_type=PARAM_TYPE_INT,
                   allowed_range=dict(min=1, max=5),
                   cmd_line=(None, "foo"))
        self.assertEqual(p.make_getopts_str(), ( None, "foo=" ))

        p = _Param(name='foo', param_type=PARAM_TYPE_INT,
                   allowed_range=dict(min=1, max=5),
                   cmd_line=("f", None))
        self.assertEqual(p.make_getopts_str(), ( "f:", None ))

        p = _Param(name='foo', param_type=PARAM_TYPE_BOOL,
                   cmd_line=("f", "foo"))
        self.assertEqual(p.make_getopts_str(), ( "f", "foo" ))

    def test_param_doc_output(self):
        """
        Testing that we create correct doc output.

        """
        p = _Param(name='foo', param_type=PARAM_TYPE_INT)
        self.assertEqual(p.doc(), ( None, None ))

        p = _Param(name='foo', param_type=PARAM_TYPE_INT,
                   cmd_line=("f", "foo"),  # no doc if no cmd_line
                   doc_spec=dict())
        self.assertEqual(p.doc(), ( None, "-f <val>, --foo=<val>\n" ))

        p = _Param(name='foo', param_type=PARAM_TYPE_INT,
                   cmd_line=("f", "foo"),
                   doc_spec=dict(text="Some text"))
        self.assertEqual(p.doc(), ( None,
                                    "-f <val>, --foo=<val>\n"
                                    "    Some text\n"))

        p = _Param(name='foo', param_type=PARAM_TYPE_INT,
                   cmd_line=("f", "foo"),
                   doc_spec=dict(text="Some text", argname="arg"))
        self.assertEqual(p.doc(), ( None,
                                    "-f <arg>, --foo=<arg>\n"
                                    "    Some text\n"))

        p = _Param(name='foo', param_type=PARAM_TYPE_INT,
                   cmd_line=("f", "foo"),
                   doc_spec=dict(text="Some text", argname="arg"))
        self.assertEqual(p.doc(), ( None,
                                    "-f <arg>, --foo=<arg>\n"
                                    "    Some text\n"))

        p = _Param(name='foo', param_type=PARAM_TYPE_INT,
                   default=123,
                   cmd_line=("f", "foo"),
                   doc_spec=dict(text="Some text", argname="arg"))
        self.assertEqual(p.doc(), ( None,
                                    "-f <arg>, --foo=<arg>\n"
                                    "    Some text\n"
                                    "    Default value: 123\n"))

        p = _Param(name='foo', param_type=PARAM_TYPE_INT,
                   default=123,
                   conffile="FOOBAR",
                   cmd_line=("f", "foo"),
                   doc_spec=dict(text="Some text", argname="arg"))
        self.assertEqual(p.doc(), ( None,
                                    "-f <arg>, --foo=<arg>\n"
                                    "    Some text\n"
                                    "    Default value: 123\n"
                                    "    Conf file equivalent: FOOBAR\n"))

        p = _Param(name='foo', param_type=PARAM_TYPE_INT,
                   default=123,
                   conffile="FOOBAR",
                   cmd_line=("f", "foo"),
                   doc_spec=dict(text="Text\n* Foo\n* Bar", argname="arg"))
        self.assertEqual(p.doc(), ( None,
                                    "-f <arg>, --foo=<arg>\n"
                                    "    Text\n"
                                    "    * Foo\n"
                                    "    * Bar\n"
                                    "    Default value: 123\n"
                                    "    Conf file equivalent: FOOBAR\n"))


class ConfigClassTests(unittest.TestCase):
    """
    Tests for the Config class.

    """
    @classmethod
    def setUpClass(cls):
        """
        Create a full config with a number of parameters.

        Also create temporary directories to store config files in.

        """
        # Create a small temporary directory hierarchy
        cls.dir_one_name = tempfile.mkdtemp()
        cls.dir_two_name = tempfile.mkdtemp(dir=cls.dir_one_name)

        cls.sample_param_dict = {
        "foo" : {
            "default"        : "some-value",
            "allowed_values" : [ 'some-value', 'something-else', 'foobar',
                                 'xyz baz' ],
            "conffile"       : "MY_PARAM",
            "cmd_line"       : ('f', 'some-param'),
            "doc_spec"       : { 'text'    : "The description string here is "
                                             "long and will automatically be "
                                             "wrapped across multiple lines.",
                                 'section' : "General",
                                 'argname' : "the foo value" }
        },
        "ddd" : {
            "default"        : { 'baz' : 123 },
            "conffile"       : "MY_DICT",
            "param_type"     : PARAM_TYPE_STR_DICT,
            "cmd_line"       : ( 'Q', None ),
            "doc_spec"       : { 'text'    : "A dict value.",
                                 'section' : "General",
                                 'argname' : "the ddd value" }
        },
        "baz" : {
            "default"        : 123,
            "allowed_range"  : dict(min=1, max=200),
            "param_type"     : PARAM_TYPE_INT,
            "doc_spec"       : { 'text'    : "Amount of baz gizmos to add.",
                                 'section' : "Specific parameters",
                                 'argname' : "num" }
        },
        "ggg" : {
            "default"        : None,
            "param_type"     : PARAM_TYPE_BOOL,
            "cmd_line"       : ('g', None),
            "doc_spec"       : { 'text'    : "Flag control run of foobar.",
                                 'section' : "General" }
        },
        }

    @classmethod
    def tearDownClass(cls):
        """
        Removing the temporary directories.

        """
        shutil.rmtree(cls.dir_one_name)

    def _make_conf(self, *args, **kwargs):
        return Conf(*args, **kwargs)

    def test_config_init_errors(self):
        """
        Test correct error handling during configuration creation.

        """
        # Error if unknown keyword pass in via param spec
        self.assertRaisesRegexp(
            ParamError,
            "Parameter 'FOO': Invalid parameter config attribute.",
            self._make_conf,
            **{ "param_dict" : {
                    "foo" : {
                        "default"  : "some-value",
                        "FOO"      : 123,
                        "doc_spec" : {
                            'text'    : "Some desc",
                            'section' : "General",
                            'argname' : "the foo value" }}}})

        # Error if unknown param type presented
        self.assertRaisesRegexp(
            ParamError,
            "Parameter 'foo': Unknown parameter type 'FOO'.",
            self._make_conf,
            **{ "param_dict" : {
                    "foo" : {
                        "default"    : "some-value",
                        "param_type" : 'FOO',
                        "doc_spec"   : {
                            'text'    : "Some desc",
                            'section' : "General",
                            'argname' : "the foo value" }}}})

    def test_conf_access_functions(self):
        """
        Testing of a few smaller access functions for the Conf object.

        """
        conf = Conf(self.sample_param_dict)

        # Able to get a parameter
        self.assertEqual(conf.get('foo'), 'some-value')

        # Get proper exception when asking for undefine parameter
        self.assertRaisesRegexp(ParamError,
                                "Parameter 'bar': Unknown parameter.",
                                conf.get, 'bar')

        # Get all the parameter names
        k = list(conf.keys())
        k.sort()
        self.assertEqual([ 'baz', 'ddd', 'foo', 'ggg'], k)

        # Get all the items (name and values)
        items = conf.items()
        self.assertTrue(len(items), 3)
        should = {'ggg': None, 'foo': 'some-value', 'baz': 123}
        for k,v in should.items():
            self.assertTrue(k in items)
            self.assertEqual(items[k], v)

        # Getting by conffile name
        self.assertEqual(conf.get_by_conffile_name('GGG'), None)
        self.assertEqual(conf.get_by_conffile_name('MY_PARAM'), 'some-value')
        self.assertEqual(conf.get_by_conffile_name('BAZ'), 123)

        # Setting invalid values should cause exception
        self.assertRaisesRegexp(ParamError,
                                "Parameter 'baz': "
                                     "Cannot convert 'foo' to type 'integer'.",
                                conf.set,
                                'baz', "foo")
        self.assertRaisesRegexp(ParamError,
                                "Parameter 'baz': "
                                     "'444' is not in the allowed range.",
                                conf.set,
                                'baz', 444)

        # Setting valid value should be allowed
        conf.set('baz',40)
        self.assertEqual(conf.get('baz'), 40)

    def test_conf_doc_creation(self):
        """
        Test that the automatically generated doc for the configuration
        is correct.

        """
        conf = Conf(self.sample_param_dict)
        out = conf.make_doc()
        should =("General:\n"
                 "    -f <the foo value>, --some-param=<the foo value>\n"
                 "        The description string here is long and will "
                 "automatically be\n"
                 "        wrapped across multiple lines.\n"
                 "        Default value: some-value\n"
                 "        Conf file equivalent: MY_PARAM\n"
                 "    \n"
                 "    -g\n"
                 "        Flag control run of foobar.\n"
                 "        Conf file equivalent: GGG\n"
                 "    \n"
                 "    -Q <the ddd value>\n"
                 "        A dict value.\n"
                 "        Default value: {'baz': 123}\n"
                 "        Conf file equivalent: MY_DICT\n"
                 "    \n"
                 "Specific parameters:\n"
                 "    -b <num>, --baz=<num>\n"
                 "        Amount of baz gizmos to add.\n"
                 "        Default value: 123\n"
                 "        Conf file equivalent: BAZ")
        self.assertEqual(out, should)

    def test_conf_add_param(self):
        """
        Testing manual addition of parameter to existing config.

        """
        conf = Conf(self.sample_param_dict)

        # Not allowing duplicate names for parameters.
        self.assertRaisesRegexp(ParamError,
                                "Duplicate definition.",
                                conf.add, "foo")

        # Catching already existing command line options.
        self.assertRaisesRegexp(ParamError,
                                "Short option '-f' already in use.",
                                conf.add,
                                **{ "name" : "ttt",
                                    "cmd_line" : ( 'f', None ) })
        self.assertRaisesRegexp(ParamError,
                                "Long option '--some-param' already in use.",
                                conf.add,
                                **{ "name" : "ttt",
                                    "cmd_line" : ( None, 'some-param' ) })

        conf.add("zip-bar")
        p = conf.params["zip-bar"]

        # Assert that default getopts are correct.
        self.assertEqual(('z:', 'zip-bar='), p.make_getopts_str())

        # Assert correctness of aut-generated conffile name.
        self.assertEqual("ZIP_BAR", p.conffile)
        p.value = "foo"
        self.assertEqual(conf.get_by_conffile_name("ZIP_BAR"), "foo")

    def _make_file(self, buf):
        fname = self.dir_two_name+"/t1.conf"
        f = open(fname, "w")
        f.write(buf)
        f.close()
        return fname

    def test_conf_configfile(self):
        """
        Testing parsing of configfile.

        """
        # Create config file with unknown parameter.
        fname = self._make_file("""

        # This is a comment line.
        FOO xyz
        """)
        conf = Conf(self.sample_param_dict)
        with open(fname, "r") as f:
            self.assertRaisesRegexp(ParamError,
                                    "Line 4: Unknown parameter 'FOO'.",
                                    conf._parse_config_file, f)

        # Create config file with correct parameter but wrong value.
        fname = self._make_file("""
        MY_PARAM xyz
        """)
        conf = Conf(self.sample_param_dict)
        with open(fname, "r") as f:
            self.assertRaisesRegexp(ParamError,
                                    "Line 2: Parameter 'foo': "
                                    "'xyz' is not one of the allowed values.",
                                    conf._parse_config_file, f)

        # Create config file with correct parameters
        fname = self._make_file("""

         # empty lines and comments and stuff with odd indentation
        MY_PARAM     xyz baz

          MY_DICT     {
              bar : 123;    # some comment that's ignored
                          baz : foo,bar,   blah  , fff ;
                          }
              # some comment
         GGG   yes     # comment at end of line
        """)
        conf = Conf(self.sample_param_dict)
        with open(fname, "r") as f:
            conf._parse_config_file(f)

        self.assertEqual(conf.get('foo'), "xyz baz")
        self.assertTrue(conf.get('ggg'))
        d = conf.get('ddd')
        self.assertEqual(len(d), 2)
        self.assertTrue('bar' in d)
        self.assertTrue('baz' in d)
        self.assertEqual(d['bar'], "123")
        self.assertEqual(d['baz'], [ "foo", "bar", "blah", "fff" ])

    def test_conf_envvars(self):
        """
        Testing parsing of environment variables.

        """
        conf = Conf(self.sample_param_dict,
                    default_env_prefix="FOOBAR_")

        # Env variables with the defined prefix, but otherwise unknown name
        # will simply be silently ignored.
        os.environ['FOOBAR_SOMETHING_UNKNOWN'] = "foo"

        # Set illegal value in env variable
        os.environ['FOOBAR_MY_PARAM'] = "ggg"
        self.assertRaisesRegexp(ParamError,
                                "Environment variable FOOBAR_MY_PARAM: "
                                "Parameter 'foo': 'ggg' is not one of the "
                                "allowed values.",
                                conf._process_env_vars)

        # Set correct value in env variables
        os.environ['FOOBAR_MY_PARAM'] = "something-else"
        os.environ['FOOBAR_GGG'] = "y"
        conf._process_env_vars()
        self.assertEqual("something-else", conf.get('foo'))
        self.assertTrue(conf.get('ggg'))

    def test_conf_cmdline(self):
        """
        Testing parsing of command line arguments.

        """
        conf = Conf(self.sample_param_dict)

        # Testing with illegal parameter
        self.assertRaisesRegexp(ParamError,
                                "Command line option: option --xyz not "
                                "recognized.",
                                conf._process_cmd_line,
                                [ "--xyz=blah" ])

        # Testing with illegal value
        self.assertRaisesRegexp(ParamError,
                                "Parameter 'foo': 'blah' is not one of the "
                                "allowed values.",
                                conf._process_cmd_line,
                                [ "--some-param=blah", "-g", "--baz", "200" ])

        # Testing with correct value
        conf._process_cmd_line([ "--some-param=foobar", "-g", "--baz", "200",
                                 "-Q", "{ foo:123 ; bar:1, 2,3; a: X  Y Z }" ])
        self.assertEqual('foobar', conf.get('foo'))
        self.assertEqual(200, conf.get('baz'))
        self.assertTrue(conf.get('ggg'))
        d = conf.get('ddd')
        self.assertEqual(len(d), 3)
        self.assertEqual(d['foo'], "123")
        self.assertEqual(d['bar'], ["1", "2", "3"])
        self.assertEqual(d['a'], "X  Y Z")

    def test_conf_acquire(self):
        """
        Testing full run of acquire, using defaults, config files, environment
        variables and command line options.

        """
        # Create the config file, some values are missing
        self._make_file("""
        MY_PARAM foobar
        """)

        conf = Conf(self.sample_param_dict,
                    default_conf_file_locations=[self.dir_one_name,
                                                 self.dir_two_name],
                    default_env_prefix="FOOBAR_",
                    default_conf_file_name="t1.conf")
        self.assertRaisesRegexp(ParamError,
                                "Parameter 'ggg': Requires a value, "
                                "nothing has been set.",
                                conf.acquire, list())

        # Try again, this time set environment variable for missing value.
        os.environ['FOOBAR_GGG'] = "yes"

        conf.acquire([])
        self.assertEqual("foobar", conf.get('foo'))
        self.assertTrue(conf.get('ggg'))

        # Try again, this time set environment variables for missing value as
        # well as env overwrite for other param.
        os.environ['FOOBAR_GGG'] = "yes"
        os.environ['FOOBAR_MY_PARAM'] = "something-else"

        conf.acquire([])

        self.assertEqual("something-else", conf.get('foo'))
        self.assertTrue(conf.get('ggg'))

        # Try again, this time add a command line overwrite
        conf.acquire([ "-f", "some-value" ])
        self.assertEqual("some-value", conf.get('foo'))


if __name__ == "__main__":
    unittest.main()

