#!/usr/bin/env python
# Title:    Python 2.7 SSH key configuration
# Author:   Matthew Williams
# Date:     2/30/2017
# Latest Update:   4/18/2017
#
# Description: Python Code to pull public keys from PIV standard smartcards
# create an ssh key from the certificate and insert it into the file specified
#
#
import re
import fileinput
import os
import sys
import platform
import shutil
import subprocess
import logging
import time
import socket
from itertools import islice
#
# VARIABLE DEFINITION
#

dist_name = platform.linux_distribution()[0] # For Linux Distro's store the distribution name
dist_version = platform.linux_distribution()[1] # For Linux Distro's store the version number
host_name = socket.gethostname()
script_path = os.path.abspath(os.path.dirname(sys.argv[0])) # Location script is ran from.
current_time = time.strftime("%H:%M:%S")
current_date = time.strftime("%d-%m-%Y")
log_file_path = 'SSHscript_' + dist_name + dist_version + '_' + current_date + '_' + current_time + '.log'
debug_flag = False
cert_number = '1' # pkcs15 requires the location of the certificate on the PIV card. This points to that
output_crt =  'myPIV.crt'
output_pem =  'myPIV.pem'
pubkey_pem =  'pubkey.pem'
publickey_pub =  'publickey.pub'
pkcs15_output = 'nothing' # Check all of the certs available on the card and store output
pkcs15_create_crt = subprocess.check_output("pkcs15-tool --read-certificate 1 --out " + script_path + "/myPIV.crt", shell=True) # Export the cert from the card and store output
ssh_created_key = 'none'
authorized_ssh_keys = "/.ssh/authorized_keys"
authorized_ssh_keys2 = "/.ssh/authorized_keys2"
head,tail = os.path.split(script_path)
username = os.environ['SUDO_USER']
homedir = "/home/" + username
homedirfound = os.path.isdir(homedir + "/.ssh")
piv_variable = '.*Certificate for PIV Authentication.*'
ask_input = True
intro_text = """
##################################################################
# Title:    Python 2.7 SSH key configuration
# Author:   Matthew Williams
#
# Special Thanks to Derek Stucki for his help on SSH key and a method to
# extract the keys in the smartcard for use with SSH.
#
# Date:     3/30/2017
# Latest Update:   4/18/2017
#
# Description: Python Code to pull public keys from PIV standard smartcards
# create an ssh key from the certificate and insert it into the file specified
#
# This script is to be used on Linux OS's ONLY
# DO NOT RUN AS SUDO OR ROOT
#
"""
outro_text = """
# The script is has completed!
#
# No major errors were discovered during the configuration.
##################################################################
"""
configuration_options = """
This script will pull the public certificate from your smardcard and use it
to generate a public ssh key to be placed in your ~/.ssh/authorized_keys file.

Please choose from the following options:

1. Generate the key and place it in ~/.ssh/authorized_keys
2. Generate the key ONLY
3. Generate the key and place it in a different location

Default is Option 1

"""
#
# END OF VARIABLE DEFINITION
#

#
# LOGGING DEFINITION
#
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# create file handler and set level to debug
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

# create stream handler and set level to info then print that stream to console
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
formatterstream = logging.Formatter("%(levelname)s - %(message)s")
stream_handler.setFormatter(formatterstream)

# add Handlers to logger
logger.addHandler(stream_handler)
logger.addHandler(file_handler)
#
# END OF LOGGING DEFINITION
#

#
# FUNCTIONS DEFINITION
#

def check_os(): # Function to determine OS and whether or not to continue
    from sys import platform
    if platform == "linux" or platform == "linux2": # Linux...
        print (intro_text)
        print ("Your OS:"),
        print (dist_name),
        print (dist_version)
        logger.info ("Hostname: " + host_name)
        logger.debug("path: " + head)
        logger.debug("directory: " + tail)
        logger.debug("home directory located? \/")
        logger.debug(homedirfound)
        
        return()
            # End Linux...
    elif platform == "darwin": #OS X...
        print ("Your OS is MAC")
        print ("This script is for Linux Machines only...")
        exit_script(0)
            # End OS X...
    elif platform == "win32": # Windows...
        print ("Your OS is Windows")
        print ("This script is for Linux Machines only...")
        exit_script(0)
            # End Windows...
    else:
        print ("I cannot determine your Operating System type...")
        exit_script(0)
        
def pull_cert(): # walks through steps as designed by Derek Stuki to pull cert and use openssl to turn it into an SSH key
    global pkcs15_output
    global pkcs15_create_crt
    global ssh_created_key
    logger.debug (pkcs15_create_crt)
    subprocess.check_output("openssl x509 -in " + output_crt + " -outform PEM -inform PEM -out " + output_pem, shell=True)
    subprocess.check_output("openssl x509 -in " + output_pem + " -pubkey -noout > " + pubkey_pem, shell=True)
    ssh_created_key = subprocess.check_output("ssh-keygen -i -m PKCS8 -f " + pubkey_pem, shell=True)
    logger.debug(ssh_created_key)
    if debug_flag is True:
        pkcs15_output = subprocess.check_output("pkcs15-tool -c", shell=True)
        logger.debug(pkcs15_output)
        lines = pkcs15_output.split('\n')
        for line in lines:
            print(line)
            if re.match(piv_variable, line):
                print(line)
                logger.debug("Index for the start of PIV Auth cert: ")
                logger.debug(lines.index(line))

def place_cert_home(): # pastes the key to authorized_keys and authorized_keys2 in the users home directory.
    global ssh_created_key
    if homedirfound is True:
        if not os.path.exists(homedir + authorized_ssh_keys):
            f = open(homedir + authorized_ssh_keys, 'w+')
            f.write(ssh_created_key)
            f.close()
            return()
        with open(homedir + authorized_ssh_keys,"a+") as f:
            f.write(ssh_created_key)
            f.close()
        
        if os.path.exists(homedir + authorized_ssh_keys2):
            with open(homedir + authorized_ssh_keys2,"a+") as f2:
                f2.write(ssh_created_key)
                f2.close()
    else:
        print(homedir + authorized_keys)
        exit_script(0)

def place_cert_loc(input_location): #Will take the location from the ask_location function and add the key there.
    global ssh_created_key
    location = input_location
    if not os.path.exists(location):
        logger.error("That directory does not exist or is not a directory!")
        exit(0)
    else:
        f = open(location + "/SSHkey" + current_date + current_time, 'a+')
        f.write(ssh_created_key)
        f.close()
        logger.info("SSH key saved to: " + location + "/SSHkey" + current_date + current_time)
        return()
def ask_location(ask_input): # ask the user where they want the keys exported to. Accepts string as input (NO INTERPRETATION)
    if ask_input is True:
        loc_var = raw_input("What directory do you want the key exported to?")
    else:
        loc_var = script_path
    return(loc_var)
    
def configuration_check(): # ask the user how they want to use the script
    option_1 = set(['1','1.',''])
    option_2 = set(['2','2.'])
    option_3 = set(['3','3.'])
    debug = set(['debug','d'])
    global debug_flag
    global ask_input
    print(configuration_options)
    choice = raw_input().lower()
    if choice in option_1: # Generate the key and place it in ~/.ssh/authorized_keys
        debug_flag = False
        pull_cert()
        place_cert_home()
        cleanup(output_crt)# delete output_crt
        cleanup(output_pem)# delete output_pem
        cleanup(pubkey_pem)# delete pubkey_pem
        logger.info("Keys added")
        exit_script(0)
    elif choice in option_2: # Generate the key ONLY
        pull_cert()
        debug_flag = False
        ask_input = False
        place_cert_loc(ask_location(ask_input))
        cleanup(output_crt)# delete output_crt
        cleanup(output_pem)# delete output_pem
        cleanup(pubkey_pem)# delete pubkey_pem
        exit_script(0)
    elif choice in option_3: # Generate the key and place it in a different location
        debug_flag = False
        ask_input = True
        place_cert_loc(ask_location(ask_input))
        cleanup(output_crt)# delete output_crt
        cleanup(output_pem)# delete output_pem
        cleanup(pubkey_pem)# delete pubkey_pem
        exit_script(0)
    elif choice in debug: # Debugging Generate the key and not place it anywhere
        debug_flag = True
        if debug_flag is True:
            logger.info("***DEBUGGING ENABLED***")
            logger.info(username)
            pull_cert()
    else:
        print("Please respond with 'yes' or 'no'")
        configuration_check()# Just ask if the user wishes to continue

def exit_script(exit_code): # Function to exit script, will build exception handling in the future
    logger.debug("Exiting script.")
    sys.exit(exit_code)
    
def cleanup(filename): # remove files created during script
    logger.debug("Cleaning up: " + filename)
    try:
        os.remove(filename)
        logger.debug("Removing: " + filename)
    except OSError:
        logger.error(filename + " clean up failed!")
        pass

#
# END OF FUNCTIONS DEFINITION
#

#
# PROGRAM DEFINITION
#
check_os()
configuration_check()
exit_script(0)
#
# END OF PROGRAM DEFINITION
#