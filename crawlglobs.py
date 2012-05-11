""" Random global variables accessed through the crawler. 

Author: nehachachra@gmail.com
"""

# Note: These variables can only be set for processes before new processes are
#    spawned. Processes don't share memory, so editing them from any process
#    will only affect that process.
display = None
img_dir = None
dom_dir = None
visit_chain_dir = None
proxy_file = None
proxy_scheme = None
# List of tag dictionaries.
tags_l = None
# Directory for all temporary data
tmp_dir = None
# Logging queue for multiprocess logging
log_q = None
logger = None
log_level = None