"""
Conversion script for sample_input.txt.

For help, run:
python createstalloneinput.py -h 

In order to check if the input file created is correct, use
sanitycheckinput.py in Stallone/helpers. Use -h for options with that script.

dataset.txt format:
URL1
URL2
URL3
...

Desired format:
{
 "1": {
            "url" : "http://www.google.com",
            "features": "all"
        }
}

Author: nchachra@cs.ucsd.edu
"""

import argparse
import simplejson as json
import os

def args_to_input_file_list(arg):
    """Returns a list of input files. If the user passed a directory, the 
    list contains the files from the directory. If the user entered
    individual files using -i file1 -i file2, return the list 
    unchanged.
    """
    # Check if the input file is a directory.
    if os.path.isdir(arg[0]):
        print "Provided directory."
        file_list = [arg[0] + "/" + 
                f for f in os.listdir(arg[0])]
    else:
        file_list = arg
    return file_list


if __name__== '__main__':
    description = ("This script is an example of generating a simple input \n"+
                   "file for the crawler.\n")
    parser = argparse.ArgumentParser(
                        description=description, 
                        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-i', '--input-file', action='append',
            help='Input file/directory containing URLs. Either specify \n'+
                 'any number of input files or a single input directory \n'+
                 'containing the input files. For example: \n' +
                 '    python createstalloneinput.py -i input1file \n' +
                 '                                        -i input2file \n' +
                 'or \n' +
                 '    python createstalloneinput.py \n' +
                 '                         -i /path/to/input/directory \n',
            required=True)
    args = parser.parse_args()
    
    file_list = args_to_input_file_list(args.input_file)
      
    for f in file_list:
        fd = open(f)
        i = 0
        # Create a large dictionary with some form of ids. In this case, I'm 
        #     picking sequential numbers, but this could really be any 
        #    alphanumeric (actually UNICODE, gasp!) id.
        req_dict = {}
        for line in fd:
            url = line.strip()
            req_dict[str(i)] = {"url": url, "features": "all"}
            i += 1
        fd.close()
        
        fd = open("sample_output.json", 'w')
        json.dump(req_dict, fd)
        fd.close()