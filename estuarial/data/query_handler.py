import yaml
import os
from sqlalchemy.sql import and_
from os.path import join as pjoin
from estuarial.util.config.config import expanduser
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

    def parse_yaml(self, yaml_url):
        """
        """
        with open(yaml_url, 'r') as stream: # Yaml should be validated here.
            obj = yaml.load(stream, Loader=yaml.CLoader)
        type_name = obj.keys()[0]
        type_data = obj[type_name]
        func_names = type_data.keys()
        return type_name, type_data, func_names

    def publish_queries(self, class_url):
        """
        Expects class_url to specify valid yaml, and for the url
        to be relative to BASEDIR.
        """
        full_url = pjoin(self.FILEDIR, class_url)
        type_name, type_data, func_names = self.parse_yaml(full_url)

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

    def function_factory(self, 
                         query_url, 
                         function_name, 
                         function_desc, 
                         known_args):
        """
        """
        url = query_url.split(self.DATAROOT)[1]
        def function(self, **kwargs):                    
            # Argument handling. Should use subset here
            # so that partial keyword args are used.
            #assert set(kwargs.keys()) == set(known_args)

            # Form the array backend object's connection.
            # This should be wrapped in a connection handling class.
            aclient = ArrayManagementClient()
            arr = aclient.aclient[url]

            # Form the conditions needed to communicate the
            # logical request of the function's invoker. Should
            # this be a full replication of the faculties of
            # sql alchemy?
            #conditions = [
            #    getattr(arr, attr) == val # 
            #    for attr, val in kwargs.iteritems()
            #]
            return arr
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
            self.publish_queries(class_url))

        for function_name in func_names:
            query_url = query_files[function_name]
            function_desc = type_data[function_name]
            query = function_desc["query"]
            known_args = function_desc.get('conditionals', [])  
            
            # Create the function wrapper for this query.
            f = self.function_factory(query_url, 
                                      function_name, 
                                      function_desc, 
                                      known_args)

            f.__name__, f.__doc__ = function_name, function_desc['doc']

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
    ub.gicsec()              # <--- Callable. No args at the moment just for testing.
    print ub.__gicsec_kwargs # <--- Function signature for this query.
    print ub.__gicsec_query  # <--- Query saved as a string from file.

    # Inferred 'spx' query API:
    ub.spx_universe() 
    print ub.__spx_universe_kwargs 
    print ub.__spx_universe_query 
