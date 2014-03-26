import yaml
import os
from sqlalchemy.sql import and_
from os.path import join as pjoin
from estuarial.util.config.config import expanduser
from estuarial.data.keyword_handler import KeywordHandler
from estuarial.array.arraymanagementclient import ArrayManagementClient

class QueryHandler(object):
    """
    """
    # Base path where queries are expected to reside.
    # Currently inferred by AMC via configs. This is
    # what provides the __getitem__ ability of aclient.
    BASEDIR = os.path.abspath(ArrayManagementClient().basedir)

    # Sub-folder of base dir for all autogenerated materials.
    AUTOGENDIR = pjoin(BASEDIR, "AUTO_GEN")

    # Sub-folder of base dir where assumed all custom yamls go.
    FILEDIR = pjoin(BASEDIR, "CUSTOM_SQL")

    # Root directory as far as query URLs are concerned.
    DATAROOT = "SQL_DATA"

    # Suffix to use for auto-gen folders coming from files, to
    # avoid having the folders end in '.yaml.'
    SUFFIX = ".autogen"

    def _parse_yaml(self, yaml_url):
        """
        Opens a compsite yaml of queries and returns a 3-tuple of the base name
        for the type that's to be created, the dictionary of data for that type
        and the list of names for the functions that will be created from the
        data.

        Params
        ------
        yaml_url: String naming a full path to a composite yaml file.

        Returns
        -------
        As a 3-tuple:
        type_name: Top-level data key from the yaml, used as the name of the
        created type.

        type_data: A dict containing the function keys and subsequent query
        data from the yaml.

        func_names: A list of the function name keys from the composite yaml.
        """
        with open(yaml_url, 'r') as stream: # Yaml should be validated here.
            obj = yaml.load(stream, Loader=yaml.CLoader)
        type_name = obj.keys()[0]
        type_data = obj[type_name]
        func_names = type_data.keys()
        return type_name, type_data, func_names

    def _publish_queries(self, class_url):
        """
        Creates a CUSTOM_SQL directory where the autogenerated queries will go.
        Publishes one yaml file per function key found in a composit yaml named
        by class_url.

        This is needed to conform to the ArrayManagement requirement that array
        clients must connect to query URLs that are relative to its known data
        path (from SQL_DATA) and the query files must have a single query. This
        function does the mapping from a composite url to the set of 
        single-query urls.

        Expects class_url to specify valid yaml, and for the url to be relative
        to BASEDIR.

        Params
        ------
        class_url: String naming a relative path to a composite yaml. Path must
        be relative to QueryHandler.BASEDIR

        Returns
        -------
        As a 5-tuple:
        query_files: List of the written single-query yamls.

        classdir: Path naming the created auto-gen directory where the queries
        have ben written.

        The following are returned by this function via an internal call to 
        _parse_yaml. See _parse_yaml for output information.

        type_name
        type_data
        func_names

        """
        full_url = pjoin(self.FILEDIR, class_url)
        type_name, type_data, func_names = self._parse_yaml(full_url)

        try:
            classdir = pjoin(self.AUTOGENDIR, class_url) + self.SUFFIX
            os.mkdir(classdir)
        except:
            # Should handle some errors and re-raise.
            pass

        query_files = {}
        for f_name in func_names:
            function_yaml = {"SQL":{f_name:type_data[f_name]}}
            output_file = pjoin(classdir, f_name) + ".yaml"
            with open(output_file, 'w') as output:
                yaml.dump(function_yaml, output)
            query_files[f_name] = output_file

        return query_files, classdir, type_name, type_data, func_names

    def _publish_docstring(self, function_description):
        """
        Expects the dictionary of function data from the Yaml to be passed
        in as function_description.

        Develops the function's docstring and keyword arg docs from the
        description and returns it as a string. Also returns a list of the
        discovered keyword arguments.

        Params
        ------
        function_description: A dictionary of the data form a composite yaml
        that describes a query function.

        Returns
        -------
        known_args: A list of the keyword args as strings.
        
        function_doc: The docstring of the function.
        """
        # Get annotated keyword args and docs.
        known_args_docs = function_description.get('conditionals', {})
        known_args = known_args_docs.keys()

        # Process arg-specific docs onto function's docstring.
        function_doc = function_description['doc'] + "\n\nParams\n------\n"
        if known_args == {}:
            function_doc += "None.\n"
        else:
            for k_arg in known_args:
                function_doc += k_arg + ": " + known_args_docs[k_arg] + "\n"
        return known_args, function_doc

    def function_factory(self, 
                         query_url, 
                         function_name, 
                         function_desc, 
                         known_args):
        """
        """
        url = query_url.split(self.DATAROOT)[1]
        def function(self, **kwargs):                    
            aclient = ArrayManagementClient()
            arr = aclient.aclient[url]

            # Create a Keyword Handler.
            kw_handler = KeywordHandler(arr)
            op_names = kw_handler.supported_ops()
            sql_names = kw_handler.supported_sql()

            # For each arg in known_args, loop over each
            # supported sql word and make a function that
            # gets invoked on the kw val, <base_arg>_<sql_word>
            kw_arg_responses = {}
            for base_arg in known_args:
                base_arg = base_arg.lower()
                for sql_name in sql_names:
                    compound_arg = base_arg + "_" + sql_name
                    kw_arg_responses[compound_arg] = (
                        kw_handler.sql_bind(base_arg, sql_name))

                for op_name in op_names:
                    if op_name == "":
                        compound_arg = base_arg
                    else:
                        compound_arg = base_arg + "_" + op_name
                    kw_arg_responses[compound_arg] = (
                        kw_handler.op_bind(base_arg, op_name))

            # To be used for more verbose documentation?
            all_possible_args = kw_arg_responses.keys()

            # Form the array backend object's connection.
            # This should be wrapped in a connection handling class.

            # Form the conditions needed to communicate the
            # logical request of the function's invoker.
            none = lambda *args, **kwargs: None
            conditions = []
            for attr, val in kwargs.iteritems():
                attr = attr.lower()
                response_function = kw_arg_responses.get(attr, none)
                if isinstance(val, (tuple, list, set)):
                    conditions.append(response_function(*val))
                elif isinstance(val, dict):
                    conditions.append(response_function(**val))
                else:
                    conditions.append(response_function(val))
                    
            # Handle case of no arguments.
            select_arg = and_(*conditions) if conditions else None
                    
            return arr.select(select_arg)
        return function

    def create_type_from_yaml(self, class_url):
        """
        Expects class_url to point to a properly formatted .yaml file
        for ingesting a set of related queries as functions exposed
        on a new class.
        """
        type_dict = {}
        #try:
        #    self.validate_yaml(class_url)
        #except:
        #    pass

        query_files, classdir, type_name, type_data, func_names = (
            self._publish_queries(class_url))

        for function_name in func_names:
            query_url = query_files[function_name]
            function_desc = type_data[function_name]
            query = function_desc["query"]
            known_args, function_doc = self._publish_docstring(function_desc)

            # Create the function wrapper for this query.
            f = self.function_factory(query_url, 
                                      function_name, 
                                      function_desc, 
                                      known_args)

            # Give the function attribute the name and docstring intended by
            # the user.
            f.__name__, f.__doc__ = function_name, function_doc

            # Place the function and metadata into the type dict.
            type_dict[function_name] = f
            type_dict["__" + function_name + "_file"] = query_url
            type_dict["__" + function_name + "_query"] = query
            type_dict["__" + function_name + "_kwargs"] = known_args

        return type(type_name, (object,), type_dict)        
        
if __name__ == "__main__":
    import os

    test_query_url = "test_yaml.yaml"
    UniverseBuilder = QueryHandler().create_type_from_yaml(test_query_url)
    ub = UniverseBuilder()

    # Inferred 'gicsec' query API:
    #ub.gicsec()             # <--- Callable. No args at the moment just for testing.
    print ub.__gicsec_kwargs # <--- Function signature for this query.
    print ub.__gicsec_query  # <--- Query saved as a string from file.

    # Inferred 'spx' query API:
    #ub.spx_universe() 
    print ub.__spx_universe_kwargs 
    print ub.__spx_universe_query 

    # Example of actually perfomring a query (assumes TR VPN):
    ex_date = '2013-12-31'
    df = ub.spx_universe(DATE_=ex_date, ITICKER='SPX_IDX')

    print "Result for SPX IDX query for {}".format(ex_date)
    print df.head()
