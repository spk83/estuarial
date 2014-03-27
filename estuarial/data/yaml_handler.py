"""
Validates yaml format used by Estuarial for composite and singleton 
SQL query specifications.

Author: Ben Zaitlen and Ely Spears
"""
import re
import yaml
import keyword

class YamlHandler(object):
    """
    Provides methods for validating that the data loaded from a yaml file is
    suitable for use in the systems -- that it has the required and optional 
    keywords.
    """
    _SQL_SENTINAL = "SQL"
    _PYTHON_NAMING_REGEXP = "[_A-Za-z][_a-zA-Z0-9]*"

    _OPTIONAL_QUERY_ITEMS = {"conditionals":(dict,)}
    _REQUIRE_QUERY_ITEMS = {"doc":(str, unicode), 
                            "query":(str, unicode)}

    _CONDITIONAL_KEY_TYPES = (str, unicode)
    _CONDITIONAL_VALUE_TYPES = (str, unicode, None)


    def __init__(self):
        """
        Construct the callable checker functions for any named arguments that
        require additional checking beyond type validation.
        """
        # Space to declare callables that should be executed on the sub-dict
        # or parameter value for the specified keyword. These are implemented
        # as instance methods and thus are configured on instantiation.
        self._REQUIRED_ARG_CHECKERS = {}
        self._OPTIONAL_ARG_CHECKERS = {"conditionals":self.valid_conditionals}

    def valid_variable(self, variable):
        """
        Validates that a string to be used as a variable name conforms to
        standard Python naming conventions that won't disrupt common getattr
        access, that variable name does not conflict with Python keywords or
        built-in names.

        Params
        ------
        variable: A string intended to be used in naming a Python object.

        Returns
        -------
        valid: A Boolean describing whether the passed string is valid or not.
        """
        is_valid_string = re.match(self._PYTHON_NAMING_REGEXP, variable) 
        is_not_reserved_keyword = (not keyword.iskeyword(variable))
        is_not_builtin = (variable not in dir(__builtin__))
        valid = all((is_valid_string, is_not_reserved_keyword, is_not_builtin))
        
        # If the variable name is not valid, raise an exception.
        if not valid:
            message = ("Attempted to declare conditional variable named {}.\n"
                       "This name is either an invalid variable name or else "
                       "shadows a reserved keyword or builtin name.")

            raise NameError(message.format(variable))

        # Returns True when method succeeds.
        return valid

    def valid_conditionals(self, conditional_dict):
        """
        Validates sub-dictionary of conditional variable names and their doc-
        strings from loaded yaml data. Checks that all loaded values are of
        correct type and checks that all variable names will conform to Python
        standard for getattr attribute access ("dot" syntax).

        Params
        ------
        conditional_dict: A dictionary (from loaded yaml) of the conditional 
        names (keys) and doc-strings (values).

        Returns
        -------
        names_are_valid: A Boolean describing whether all of the conditonal
        names can serve as valid Python variable names.
        """
        # Get the intended variable names for the conditionals
        conditional_keys = conditional_dict.keys()

        # Ensure conditional names and their doc values are of allowable types.
        for conditional in conditional_keys:

            # Raise an exception if conditional name is not a string type.
            if not isinstance(conditional, self._CONDITIONAL_KEY_TYPES):

                message = "Received conditional {} that is not of type in {}"

                raise TypeError(message.format(conditional, 
                                               self._CONDITIONAL_KEY_TYPES))

            # Raise an exception if conditional name is not accompanied by a
            # string-type (or None) doc string value.
            if not isinstance(conditional_dict[conditional], 
                              self._CONDITIONAL_VALUE_TYPES):

                message = "Received invalid docstring type for conditional {}"

                raise TypeError(message.format(conditional))

        # After ensuring all types are ok, check if variable names adhere to
        # standards required for Python's natural getattr "dot" syntax to work.
        names_are_valid = all(map(self.valid_variable, conditional_keys))

        # Returns True when method succeeds.
        return names_are_valid
            
    def valid_sql_singleton(self, loaded_data_from_yaml):

        # Ensure that top-level signifies this is a SQL parameter file.
        top_level_keys = loaded_data_from_yaml.keys()
        has_one_top_level_key = (len(top_level_keys) == 1)
        top_level_key_is_sql = (top_level_keys[0] == self._SQL_SENTINAL)

        if not (has_one_top_level_key and top_level_key_is_sql):

            message = ("Single top-level key {} not found in yaml. Check\n"
                       "indentation levels to ensure only a single top-level\n"
                       "key exists and matches.")

            raise ValueError(message.format(self._SQL_SENTINAL))

        # Ensure there is only one function defined.
        function_level_data = loaded_data_from_yaml[self._SQL_SENTINAL]
        function_level_keys = function_level_daya.keys()
        has_one_function_key = (len(function_level_keys) == 1)

        if not has_one_function_key:
            message = ("Found {} yaml function declarations when only 1 is "
                       "permitted.")

            raise ValueError(message.format(len(function_level_keys)))

        # Get query-level data and keys and ensure no duplicates.
        query_level_data = function_level_data[function_level_keys[0]]
        query_level_keys = query_level_data.keys()

        if not (list(set(query_level_keys)) == query_level_keys):
            message = "No duplicate fields permitted, but found {}."

            raise ValueError(message.format(query_level_keys))


        # Check required items
        for require_key, require_type in self._REQUIRE_QUERY_ITEMS.iteritems():

            # Check that the required key is actually used.
            if not require_key in query_level_keys:
                message = "Required field {} not found in yaml data."
                raise LookupError(message.format(require_key))

            # Check that the data type for this key is permissible.
            if not isinstance(query_level_data[require_key], require_type):
                message = ("Data for required field {} is not correct type.\n"
                           "Found type {} but require type in {}")

                raise TypeError(message.format(
                        require_key, 
                        type(query_level_data[require_key]),
                        require_type))

            # If extra checkers are present for this key, run them and
            # raise an exception if they do not succeed.
            if require_key in self._REQUIRED_ARG_CHECKERS:
                checker = self._REQUIRED_ARG_CHECKERS[checker]
                is_valid = checker(query_level_data[require_key])
                if not is_valid:
                    message = ("Section {} from yaml failed validity "
                               "checking.")
                    
                    raise ValueError(message.format(require_key))

        # Check all keys for the optional items
        for query_key in query_level_keys:
            
            # If it's a required item, it was already checked, so skip it.
            if query_key in self._REQUIRED_QUERY_KEYS.keys():
                continue

            # If it's an optional item, process it.
            elif query_key in self._OPTIONAL_QUERY_ITEMS.keys():

                # Raise exception if the optional argument's data is
                # of the wrong type.
                permissible_types = self._OPTIONAL_QUERY_ITEMS[query_key]
                if not isinstance(query_level_data[query_key], 
                                  permissible_types):

                    message = ("For yaml data field {}, incorrect type {} was "
                               "found. Type expected to be in {}.")

                    raise TypeError(message.format(
                            query_key,
                            type(query_level_data[query_key]),
                            permissible_types))


                # If extra checkers exist for this key, call them and raise
                # exception if they do not succeed.
                if query_key in self._OPTIONAL_ARG_CHECKERS:
                    checker = self._OPTIONAL_ARG_CHECKERS[checker]
                    is_valid = checker(query_level_data[query_key])
                    if not is_valid:
                        message = ("Section {} from yaml failed validity "
                                   "checking.")
                        
                        raise ValueError(message.format(query_key))

            # Otherwise the key is invalid. Raise an exception.
            else:
                invalid_parm = "Unrecognized optional yaml parameter: {}."
                raise ValueError(invalid_parm.format(query_key))

        # If the method succeeds, return True
        return True

    def valid_sql_composite(self, loaded_data_from_yaml):
        """
        """
        #1. Ensure top-level name is valid Python name.
        #2. Ensure there are 1 or more second-level keys.
        #3. Ensure second level names are valid Python names.
        #4. Perform same validation as in single-yaml, but on each
        #   function's sub-yaml. May need to refactor the single-yaml
        #   function for this.
        return True
