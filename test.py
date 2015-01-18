import unittest

from pyparams import ( _bool_check,
                       _str_list_check,
                       _Param,
                       ParamError,
                       PARAM_TYPE_BOOL,
                       PARAM_TYPE_INT,
                       PARAM_TYPE_STR_LIST,
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
    Tests for the Param class.

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


    # TODO: Need to add tests for full configuration.

if __name__ == "__main__":
    unittest.main()

