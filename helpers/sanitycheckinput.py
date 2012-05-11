"""
Checks the input files for correct format before crawling them to avoid 
delayed error notifications.

See: 
python sanitycheckinput.py -h 
for documentation.


Author: nchachra@cs.ucsd.edu
"""

import argparse
import json
import logging
import os
import traceback


def args_to_input_file_list(arg):
    """Returns a list of input files. If the user passed a directory, the 
    list contains the .json files from the directory. If the user entered
    individual files using -i file1.json -i file2.json, return the list 
    unchanged.
    """
    # Check if the input file is a directory.
    if os.path.isdir(arg[0]):
        logging.info("Processing all .json files in input directory")
        json_file_list = [arg[0] + "/" + 
                f for f in os.listdir(arg[0]) 
                if f[-5:] == ".json" ]
    else:
        json_file_list = arg
    return json_file_list
  
def check_req_obj(visit_req, req_id):
    """Checks an individual visit object.
    """
    # Check URL key
    if not visit_req.has_key("url"):
        logging.error("A URL must be supplied for visit req_id %s" % req_id)
    # Check setup
    if not visit_req.has_key("setup"):
        logging.info("No setup for visit req_id %s" % req_id)
    else:
        check_setup_dict(visit_req["setup"], req_id)
    # Check features
    if not visit_req.has_key("features"):
        logging.error("No features request for ID %s" % req_id)
    else:
        if (isinstance(visit_req["features"], unicode) and
            visit_req["features"] != "all"):
                logging.error("The features can either be a string \"all\" "+
                       "or a dictionary listing all the features.")
        else:
            check_features(visit_req["features"], req_id)
    # Check actions
    if not visit_req.has_key("actions"):
        logging.info("No actions will be taken for req_id %s" % req_id)
    elif not isinstance(visit_req["actions"], dict):
        logging.error("Actions has to be a dictionary for ID %s" % req_id)
    else:
        check_actions_dict(visit_req["actions"], req_id)
        
def check_setup_dict(setup_dict, req_id):
    """Checks the setup dictionary in request object.
    """
    # Check ff_prefs
    if not setup_dict.has_key("ffprefs"):
        logging.info("No firefox prefs will be set for ID %s " % req_id)
    else:
        ff_prefs_list = setup_dict["ffprefs"]
        if not isinstance(ff_prefs_list, list):
            logging.error("ffprefs should be a list for ID %s " % req_id)
        elif len(ff_prefs_list) == 0:
            logging.info("No prefs supplied for ID %s" % req_id)
        for pref in ff_prefs_list:
            if not isinstance(pref, list):
                logging.error("Pref %s for ID %s must be a list" %
                      (str(pref), req_id))
            elif not len(pref) == 3:
                logging.error("Pref %s " % str(pref) + " for ID %s " % req_id +
                       "must be a list of 3 strings: " +
                        "[pref_name, pref_value, pref_type]")
                for pref_mem in pref:
                    if not isinstance(pref_mem, str):
                        logging.error("Pref mem %s " % str(pref_mem) +
                                "in ID %s " % req_id + " should be string.")
                # Check the last pref to be one of the predefined values
                if not (isinstance(pref[2], unicode) and 
                        pref[2].lower() == 'int' or 
                        pref[2].lower() == "integer" or 
                        pref[2].lower() == "str" or 
                        pref[2].lower() == "string" or
                        pref[2].lower() == "bool" or 
                        pref[2].lower() == "boolean"):
                    logging.error("Invalid value for pref_type for \n" +
                           "id %s" % req_id + " Pref_type can be 'int', \n" +
                           "'integer', 'str', 'string', 'bool' or 'boolean'")
                if (isinstance(pref[2], unicode) and 
                    isinstance(pref[1], unicode) and
                    pref[2].lower() == "bool" or 
                    pref[2].lower() == "boolean" and 
                    pref[1].lower() != "true" and pref[1].lower() != "false"):
                        logging.error("For boolean preference types, the " +
                               "only valid arguments are \"true\" and " +
                               "\"false\"")
    # Check headers
    if not setup_dict.has_key("headers"):
        logging.info("No headers will be sent for ID %s " % req_id)
    else:
        headers_dict = setup_dict["headers"]
        if not isinstance(headers_dict, dict):
            logging.error("headers should be a dict for ID %s" % req_id)
        else:
            if len(headers_dict.items()) == 0:
                logging.info("No headers will be set for req_id %s" % req_id)
            for (header, value) in headers_dict.iteritems():
                if not isinstance(header, unicode):
                    logging.error("Header %s " % str(header) + 
                            " should be string for req_id %s" % req_id )
                if not isinstance(value, unicode):
                    logging.error("Header value %s " % str(value) + 
                           " should be string for req_id %s" % req_id )
        # Check proxy
        if not setup_dict.has_key("proxy"):
            logging.info("No proxy will be used for ID %s" % req_id)
        else:
            proxy_list = setup_dict["proxy"]
            if not isinstance(proxy_list, list):
                logging.error("proxy should be a list of \n" +
                        "[hostname_str, port_str, proxy_type_str] " +
                        " for req_id %s" % req_id)
            elif not len(proxy_list) == 3:
                logging.error("proxy should be a list of \n" +
                        "[hostname_str, port_str, proxy_type_str] " +
                        " for req_id %s" % req_id)
            else:
                for mem in proxy_list:
                    if not isinstance(mem, unicode):
                        logging.error("proxy member %s " % mem +
                                " should be string for req_id %s " % req_id)


def check_features(features, req_id):
    """Checks the features dictionary within visit request.
    """
    if (not isinstance(features, str) and not isinstance(features, dict) 
        and not isinstance(features, unicode)):
        logging.error("Features has to be either a string 'all' or a \n" +
               "dictionary for id %s" % req_id)
    if ((isinstance(features, str) or isinstance(features, unicode)) 
        and features.lower() != 'all'):
        logging.error("features for any input should be either the \n" +
                   "'all', or a dictionary of features for id %s" % req_id)
    elif isinstance(features, dict):
        if (features.has_key("screenshot") and 
            features["screenshot"][-4:] == '.png'):
            if not features.has_key("visitchain"):
                logging.error("Screenshot file will be saved as <md5>.png, \n"+
                   "but visitchain file is not specified so mapping will \n "+
                   "be lost for id %s" % req_id)
            else:
                logging.warning("Screenshot file will be saved as <md5>.png "+
                                "for id %s" % req_id)
        else:
            logging.info("No screenshot will be saved for id %s" % req_id)
        if (features.has_key("dom") and 
            features["dom"][-5:] == '.html'):
            if not features.has_key("visitchain"):
                logging.error("Dom file will be saved as <md5>.html, \n" +
                   "but visitchain file is not specified so mapping will \n "+
                   "be lost for id %s" % req_id)
            else:
                logging.warning("Dom file will be saved as <md5>.html for " +
                       " id %s" % req_id) 
        else:
            logging.info("No Dom will be saved for id %s " % req_id)
        if features.has_key("visitchain"):
            if (features["visitchain"][-4:] == '.json'):
                logging.warning("Visitchain file will be saved as <id>.json" +
                   " for id %s" % req_id)
        else:
            logging.info("No visit chain will be saved for id %s" % req_id)
            
                        
def check_actions_dict(actions, req_id):
    """Checks just the actions in request for correctness.
    """
    if actions.has_key("eval"):
        if not isinstance(actions["eval"], list):
            logging.error(("Action eval must be a list of JS snippets for " +
                           "id %s") % req_id)
        else:
            for snippet in actions["eval"]:
                if not isinstance(snippet, unicode):
                    logging.error(("JavaScript snippets in eval should be " +
                                   "strings for req_id %s") % req_id)

if __name__== '__main__':
    description = ('This script sanity checks input files for crawler.')
    parser = argparse.ArgumentParser(
                        description=description, 
                        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-i', '--input-file', action='append',
            help='Input file/directory containing URLs. Either specify \n'+
                 'any number of input files or a single input directory \n'+
                 'containing the input files. For example: \n' +
                 '    python run.py -i input1.json -i input2.json \n' +
                 'or \n' +
                 '    python run.py -i /path/to/input/directory \n',
            required=True)
    parser.add_argument('-v', '--verbosity', 
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            help='Anything at the log level and above will be logged. \n' +
            'CRITICAL > INFO. Default: %(default)s', default='WARNING')
    args = parser.parse_args()
    
    # Set up logging
    level = getattr(logging, args.verbosity.upper(), None)
    logging.basicConfig(format='%(levelname)s:%(message)s', level=level)
    
    file_list = args_to_input_file_list(args.input_file)
    
    logging.info("Processing files: %s" % file_list)
    for f in file_list:
        logging.info("File: %s" % f)
        try:
            fh = open(f, "rb")
        except:
            print "Exception in opening input file ", f
            logging.error(("Exception in opening input file: %s. \n" +
                           "Exception: %s") % (f, traceback.print_exc()))
            fh.close()
            exit(1)
        try:
            obj = json.load(fh)
        except:
            logging.error("Cannot load JSON for file: %s. Exception: %s" 
                          % (f, traceback.print_exc()))
            fh.close()
            exit(1)
        fh.close()
        
        if not isinstance(obj, dict):
            logging.error("All the visit requests need to be encapsulated \n"+
                   "in a dictionary object.")
            exit(1)
            
        for (req_id, visit_req) in obj.iteritems():            
            if not isinstance(req_id, unicode):
                logging.error("Id %s should be a string" % req_id)
                req_id = str(req_id)
            check_req_obj(visit_req, req_id)